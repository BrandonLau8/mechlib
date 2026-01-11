import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from src.api.routers.auth import get_current_user
from src.api.schemas import ImageDiscoveryResponse, ProcessResponse, ProcessRequest, SearchResponse, SearchRequest, \
    ImageResult, UpdateMetadataResponse, UpdateMetadataRequest, DeleteImageResponse, DeleteImageRequest
from src.mechlib.img_fetcher import ImageFetcher
from src.mechlib.img_processor import ImageProcessor
from src.mechlib.metadata_fetcher import Metadata
from src.mechlib.s3_store import S3_StoreManager
from src.mechlib.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Configure upload directory
UPLOAD_DIR = Path("/tmp/mechlib_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================================
# Helper Functions
# ============================================================================

def get_document_by_s3_uri(s3_uri: str):
    """
    Find a document in the vector database by S3 URI using direct SQL query.

    This is more efficient than vector similarity search for exact lookups,
    and scales to any database size (not limited by k parameter).

    Args:
        s3_uri: S3 URI of the image (e.g., 's3://bucket/path/image.png')

    Returns:
        Document object with metadata including 'langchain_id'

    Raises:
        HTTPException: 404 if document not found
    """
    import psycopg
    from config import config
    from langchain_core.documents import Document

    logger.debug(f"Querying database for s3_uri: {s3_uri}")

    try:
        with psycopg.connect(
            host=config.psql_host,
            port=config.psql_port,
            dbname=config.psql_database,
            user=config.psql_user,
            password=config.psql_password
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT langchain_id, langchain_metadata
                    FROM mechlib_images
                    WHERE langchain_metadata->>'s3_uri' = %s
                    LIMIT 1;
                    """,
                    (s3_uri,)
                )
                result = cur.fetchone()

        if not result:
            logger.error(f"Document not found with s3_uri: {s3_uri}")
            raise HTTPException(
                status_code=404,
                detail=f"Image not found with s3_uri: {s3_uri}"
            )

        # Reconstruct Document from SQL result
        langchain_id, langchain_metadata = result

        tag_string =''
        for key, value in langchain_metadata.items():
            tag_string += f'{key}:{value}, '
        page_content = f"{langchain_metadata['description']} Tags: [{tag_string}]"

        doc = Document(page_content=page_content, metadata=langchain_metadata)

        logger.debug(f"Found document: {langchain_metadata.get('filename', 'unknown')}")
        return str(langchain_id), doc

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database query failed for s3_uri {s3_uri}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query database: {str(e)}"
        )


# ============================================================================
# API Endpoints
# ============================================================================

"""
  Browser Upload → Memory (UploadFile) → Disk (/tmp) → ExifTool → S3
                        ↑                    ↑
                    Need to save      Can't process in memory
"""
@router.post("/upload", response_model=ImageDiscoveryResponse)
async def upload_images(files: list[UploadFile] = File(...), directory: Optional[str] = None, user:dict=Depends(get_current_user)):
    """
    Button 1: Upload Images from Browser

    Accepts file uploads from the client browser, saves them temporarily,
    and returns the saved file paths for processing.

    Args:
        files: List of uploaded image files
        directory: Optional directory name for organizing uploads in S3

    Returns:
        ImageDiscoveryResponse with saved file paths
    """
    # files[0].file = <in-memory buffer of image data>
    # files[0].filename = "switch.png"
    try:
        saved_paths = []

        # Validate and save uploaded files
        for f in files:
            # Check file extension (file doesn't exist on disk yet, so just check extension)
            file_ext = Path(f.filename).suffix.lower()
            if file_ext not in ImageFetcher.SUPPORTED_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {f.filename}. Supported: {ImageFetcher.SUPPORTED_FORMATS}"
                )

            # Save to upload directory
            file_path = UPLOAD_DIR / f.filename


            # Use shutil for efficient file copying
            with open(file_path, "wb") as destination_file:
                shutil.copyfileobj(f.file, destination_file) # File Memory → Disk file located in /tmp
            logger.debug(f"Saved upload {f.filename} -> {file_path}")

            saved_paths.append(str(file_path.absolute()))
        logger.info(f'Uploaded {len(saved_paths)} files for user {user['email']}')

        return ImageDiscoveryResponse(
            file_paths=saved_paths,
            count=len(saved_paths),
            directory=directory
        )

    except HTTPException: #For expected 400 error
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload files: {str(e)}"
        )


@router.post("/process", response_model=ProcessResponse)
def process_images(request: ProcessRequest, user:dict=Depends(get_current_user)):
    """
    Button 2: Process Images

    Processes images by:
    1. Adding metadata to image files using ExifTool
    2. Uploading images to S3

    Args:
        request: ProcessRequest containing full paths and metadata

    Returns:
        ProcessResponse with processing results and S3 URIs
    """
    try:
        # Validate all paths exist
        for path_str in request.paths:
            if not Path(path_str).exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {path_str}"
                )

        # Override person field with authenticated user email (audit trail)
        request.person = user['email']

        # Create Metadata objects for each path
        # Note: We store the full path in filename for processing,
        # but S3 will use just the basename
        metadata_list = []
        for path_str in request.paths:
            full_path = Path(path_str).absolute()

            # Create metadata with full path so ExifTool can find the file
            metadata = Metadata(filename=str(full_path))
            metadata.description = request.description
            metadata.brand = request.brand
            metadata.materials = request.materials
            metadata.process = request.process
            metadata.mechanism = request.mechanism
            metadata.project = request.project
            metadata.person = request.person

            metadata_list.append(metadata)
        logger.debug(f"Created {len(metadata_list)} metadata objects")

        # Convert path strings to Path objects for path_list (Not used in API)
        path_list = [Path(p) for p in request.paths]

        # Process images: embed metadata using ExifTool
        logger.debug(f"Processing files: {[m.filename for m in metadata_list]}")
        processor = ImageProcessor(metadata_list, path_list)
        processed_files = processor.metadata_to_imgs()
        logger.info(f"ExifTool processed {len(processed_files)}/{len(metadata_list)} files")

        if not processed_files:
            raise HTTPException(
                status_code=500,
                detail="Failed to add metadata to images"
            )

        # Upload to S3
        logger.debug(f"About to upload {len(processed_files)} files to S3")
        s3_manager = S3_StoreManager()
        logger.debug(f"S3 manager created, bucket: {s3_manager.aws_bucket_name}")
        s3_manager.add_files(processed_files, request.directory)
        logger.info(f"Uploaded {len(s3_manager.img_data)} files to S3")

        # Get S3 URIs from img_data
        # img_data: {filename: s3_uri}
        filename_with_s3uri = s3_manager.img_data

        if not filename_with_s3uri:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload images to S3"
            )

        # Put s3 URIs into their respective metadatas
        # Map full paths to S3 URIs (metadata.filename contains full paths)
        filename_with_s3uri_obj = {}
        for processed_file in processed_files:
            filename = processed_file.name
            if filename in filename_with_s3uri:
                filename_with_s3uri_obj[str(processed_file.absolute())] = filename_with_s3uri[filename]
                logger.debug(f"Mapping full path: {str(processed_file.absolute())} to s3_uri: {filename_with_s3uri[filename]}")
        logger.info(f"Mapped {len(filename_with_s3uri_obj)} full paths to s3_uri")

        # Add S3_uri into metadata
        processor.s3_uris_to_metadata(filename_with_s3uri_obj)


        # Create documents using processor method
        documents = processor.make_documents()
        logger.info(f"Making documents successful: {documents}")

        # Add documents to vector store
        vector_store = VectorStoreManager()
        vector_store.add_documents(documents)
        logger.info(f"Added {len(documents)} documents to vector database for user {user['email']}")

        # Clean up temporary files after successful processing
        for processed_file in processed_files:
            try:
                processed_file.unlink()  # Delete the temporary file
                logger.info(f"Temporary file: {processed_file} cleaned up after successful processing")
            except Exception as e:
                # Log but don't fail the request if cleanup fails
                logger.warning(f"Failed to delete temp file {processed_file}: {e}")

        # Return response with basename-keyed URIs for simplicity
        s3_uris = filename_with_s3uri

        return ProcessResponse(
            message="Images processed and uploaded successfully",
            files_processed=len(processed_files),
            s3_uris=s3_uris
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process images: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
def search_images(request: SearchRequest, user:dict=Depends(get_current_user)):
    """
    Search for images in the vector database using hybrid search (keyword + semantic).

    Args:
        request: SearchRequest with query, k, score_threshold, use_hybrid, and keyword_weight

    Returns:
        SearchResponse with search results and presigned URLs
    """
    try:
        # Cap k at reasonable maximum for performance
        k = min(request.k, 50)

        # Initialize vector store
        vector_manager = VectorStoreManager()

        # Perform search (hybrid or semantic only)
        if request.use_hybrid:
            logger.debug("Using hybrid search")
            results_with_scores = vector_manager.hybrid_search(
                query=request.query,
                k=k,
                keyword_weight=request.keyword_weight
            )
        else:
            logger.debug("Using semantic-only search")
            results_with_scores = vector_manager.vector_store.similarity_search_with_score(
                query=request.query,
                k=k
            )

        # Filter by distance threshold
        # pgvector returns cosine distance where: 0=identical, 1=orthogonal, 2=opposite
        # Lower distance = more similar, so we keep results where distance <= threshold
        filtered_results = []
        for doc, score in results_with_scores:
            if score <= request.score_threshold:
                filtered_results.append((doc, score))
        logger.info(
            f"User {user['email']} searched '{request.query}': {len(filtered_results)}/{len(results_with_scores)} results passed threshold {request.score_threshold}")

        # Generate presigned URLs for filtered results
        s3_manager = S3_StoreManager()
        image_results = []

        for doc, score in filtered_results:
            # Generate presigned URL
            presigned_url = s3_manager.generate_presigned_url(
                s3_uri=doc.metadata.get('s3_uri'),
            )

            # Create ImageResult
            image_result = ImageResult(
                url=presigned_url,
                s3_uri=doc.metadata.get('s3_uri', ''),
                filename=doc.metadata.get('filename', 'Unknown'),
                description=doc.metadata.get('description'),
                brand=doc.metadata.get('brand'),
                materials=doc.metadata.get('materials'),
                process=doc.metadata.get('process'),
                mechanism=doc.metadata.get('mechanism'),
                project=doc.metadata.get('project'),
                person=doc.metadata.get('person'),
                timestamp=doc.metadata.get('timestamp'),
                score=score
            )
            image_results.append(image_result)

        # Prepare response message if no results
        message = None
        if len(filtered_results) == 0:
            if len(results_with_scores) > 0:
                min_score = min(s for _, s in results_with_scores)
                message = f"No images found with distance <= {request.score_threshold}. Closest match has distance {min_score:.3f}. Try increasing the threshold to {min_score + 0.1:.2f} or higher."
            else:
                message = "No images found matching your query."

        return SearchResponse(
            query=request.query,
            results=image_results,
            total_count=len(results_with_scores),
            filtered_count=len(filtered_results),
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for query '{request.query}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search images: {str(e)}"
        )


@router.put("/update-metadata", response_model=UpdateMetadataResponse)
def update_metadata(request: UpdateMetadataRequest):
    """
    Update metadata for an image in the vector database and S3.

    This will:
    1. Find image in the database by S3 URI (direct SQL query)
    2. Download the image from S3
    3. Update the EXIF/XMP metadata using ExifTool
    4. Re-upload to S3
    5. Delete and re-add document to the vector database

    Args:
        request: UpdateMetadataRequest with s3_uri and fields to update

    Returns:
        UpdateMetadataResponse with update confirmation
    """
    try:
        import tempfile
        import psycopg
        from config import config

        vector_manager = VectorStoreManager()
        s3_manager = S3_StoreManager()

        # Find document by s3_uri using efficient SQL query
        langchain_id, doc = get_document_by_s3_uri(request.s3_uri)

        filename = doc.metadata.get('filename', 'image')


        """
          Extracts just the key:
          s3_uri:  "s3://mechlib-images/switch.png"
                        ↓ remove "s3://mechlib-images/"
          s3_key:  "switch.png"
        """
        s3_key = request.s3_uri.replace(f"s3://{s3_manager.aws_bucket_name}/", "")

        # Use temp file to download and reload S3 Object
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)  # tmp_file.name = "/tmp/tmp8x3k2j1p.png" (random name)

            # Download from S3
            s3_manager.s3_client.download_file(
                s3_manager.aws_bucket_name, # Where to download FROM (S3 bucket)
                s3_key, # What to download (S3 object path)
                str(temp_path) # Where to save to (local file path, filename does not matter)
            )
            logger.debug(f"Downloaded image from S3: {s3_key}")


            # Create Metadata object with updated fields
            # IMPORTANT: filename must be the full path to the temp file for ExifTool to find it
            metadata_obj = Metadata(filename=str(temp_path.absolute()))
            metadata_obj.description = request.description if request.description is not None else doc.metadata.get('description', '')
            metadata_obj.brand = request.brand if request.brand is not None else doc.metadata.get('brand', '')
            metadata_obj.materials = request.materials if request.materials is not None else doc.metadata.get('materials', [])
            metadata_obj.process = request.process if request.process is not None else doc.metadata.get('process', [])
            metadata_obj.mechanism = request.mechanism if request.mechanism is not None else doc.metadata.get('mechanism', '')
            metadata_obj.project = request.project if request.project is not None else doc.metadata.get('project', '')
            metadata_obj.person = request.person if request.person is not None else doc.metadata.get('person', '')


            # Update metadata in the file using ExifTool
            processor = ImageProcessor([metadata_obj], [temp_path])
            updated_files = processor.metadata_to_imgs()

            if not updated_files:
                temp_path.unlink()  # Clean up
                logger.error(f"ExifTool failed to update metadata for {filename}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update image metadata with ExifTool"
                )
            logger.debug(f"Updated metadata with ExifTool for {filename}")

            # Re-upload to S3 (overwrites existing)
            s3_manager.s3_client.upload_file(
                str(temp_path), # FROM: "/tmp/tmpABC123.png" (local modified file)
                s3_manager.aws_bucket_name, # TO BUCKET: "mechlib-images"
                s3_key, # AS NAME: "switch.png" (original filename!)
                ExtraArgs={
                    'ContentType': f'image/{temp_path.suffix.lstrip(".")}',
                    'ContentDisposition': 'inline'
                }
            )
            logger.debug(f"Re-uploaded image to S3: {s3_key}")

            # Clean up temp file
            temp_path.unlink()

        # Update document metadata fields
        updated_fields = {}
        if request.description is not None:
            doc.metadata['description'] = request.description
            updated_fields['description'] = request.description
        if request.brand is not None:
            doc.metadata['brand'] = request.brand
            updated_fields['brand'] = request.brand
        if request.materials is not None:
            doc.metadata['materials'] = request.materials
            updated_fields['materials'] = request.materials
        if request.process is not None:
            doc.metadata['process'] = request.process
            updated_fields['process'] = request.process
        if request.mechanism is not None:
            doc.metadata['mechanism'] = request.mechanism
            updated_fields['mechanism'] = request.mechanism
        if request.project is not None:
            doc.metadata['project'] = request.project
            updated_fields['project'] = request.project
        if request.person is not None:
            doc.metadata['person'] = request.person
            updated_fields['person'] = request.person

        # Update page_content to match new metadata
        tags = [
            f"filename:{doc.metadata.get('filename', '')}",
            f"brand:{doc.metadata.get('brand', '')}",
            f"materials:{','.join(doc.metadata.get('materials', []))}",
            f"process:{','.join(doc.metadata.get('process', []))}",
            f"mechanism:{doc.metadata.get('mechanism', '')}",
            f"project:{doc.metadata.get('project', '')}",
            f"person:{doc.metadata.get('person', '')}"
        ]
        doc.page_content = f"{doc.metadata.get('description', '')} Tags: [{', '.join(tags)}]"

        # Delete old document from vector DB
        if langchain_id:
            vector_manager.vector_store.delete([langchain_id])
            logger.debug(f"Deleted old vector DB entry for {filename}")
        else:
            # Direct SQL delete using s3_uri in metadata
            with psycopg.connect(
                host=config.psql_host,
                port=config.psql_port,
                dbname=config.psql_database,
                user=config.psql_user,
                password=config.psql_password
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM mechlib_images WHERE langchain_metadata->>'s3_uri' = %s",
                        (request.s3_uri,)
                    )
                conn.commit()

        # Add updated document to vector DB
        vector_manager.add_documents([doc])
        logger.info(f"Metadata updated successfully for {filename} (s3_uri: {request.s3_uri})")

        return UpdateMetadataResponse(
            message="Metadata updated successfully in S3 and vector database",
            s3_uri=request.s3_uri,
            updated_fields=updated_fields
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metadata update failed for {request.s3_uri}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update metadata: {str(e)}"
        )


@router.delete("/delete-image", response_model=DeleteImageResponse)
def delete_image(request: DeleteImageRequest):
    """
    Delete an image from S3 and vector database.

    Args:
        request: DeleteImageRequest with s3_uri and filename

    Returns:
        DeleteImageResponse with deletion status
    """
    try:
        logger.info(f"Deleting image: {request.filename} (s3_uri: {request.s3_uri})")
        deleted_from_s3 = False
        deleted_from_vector_db = False

        # Delete from S3
        try:
            s3_manager = S3_StoreManager()
            # Extract key from s3_uri (format: s3://bucket/key)
            s3_key = request.s3_uri.replace(f"s3://{s3_manager.aws_bucket_name}/", "")

            s3_manager.s3_client.delete_object(
                Bucket=s3_manager.aws_bucket_name,
                Key=s3_key
            )
            deleted_from_s3 = True
            logger.debug(f"Deleted {request.s3_uri} from S3")
        except Exception as e:
            logger.warning(f"Failed to delete from S3: {e}")

        # Delete from vector database
        try:
            import psycopg
            from config import config

            # Direct SQL delete using s3_uri in metadata JSONB column
            with psycopg.connect(
                host=config.psql_host,
                port=config.psql_port,
                dbname=config.psql_database,
                user=config.psql_user,
                password=config.psql_password
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM mechlib_images WHERE langchain_metadata->>'s3_uri' = %s",
                        (request.s3_uri,)
                    )
                    deleted_count = cur.rowcount
                conn.commit()

            if deleted_count > 0:
                deleted_from_vector_db = True
                logger.debug(f"Deleted {request.s3_uri} from vector DB")
            else:
                logger.warning(f"No document found with s3_uri: {request.s3_uri}")

        except Exception as e:
            logger.warning(f"Failed to delete from vector DB: {e}")

        if not deleted_from_s3 and not deleted_from_vector_db:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete image from both S3 and vector database"
            )

        logger.info(
            f"Image '{request.filename}' deleted successfully (S3: {deleted_from_s3}, VectorDB: {deleted_from_vector_db})")
        return DeleteImageResponse(
            message=f"Image '{request.filename}' deleted successfully",
            s3_uri=request.s3_uri,
            deleted_from_s3=deleted_from_s3,
            deleted_from_vector_db=deleted_from_vector_db
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete image {request.s3_uri}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete image: {str(e)}"
        )
