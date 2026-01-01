from pathlib import Path
from typing import Optional
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.documents import Document
from pydantic import BaseModel

from src.mechlib.img_fetcher import ImageFetcher
from src.mechlib.img_processor import ImageProcessor
from src.mechlib.s3_store import S3_StoreManager
from src.mechlib.metadata_fetcher import Metadata
from src.mechlib.vector_store import VectorStoreManager

app = FastAPI(title="MechLib Image Processor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    # allow_origins=[
    #     "http://localhost:5173",  # Vite dev server
    #     "http://127.0.0.1:5173",  # Alternative localhost
    # ],
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Configure upload directory
UPLOAD_DIR = Path("/tmp/mechlib_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ============================================================================
# Request/Response Models
# ============================================================================

class ImageDiscoveryResponse(BaseModel):
    """Response for image discovery endpoint"""
    file_paths: list[str]
    count: int
    directory: Optional[str] = None


class ProcessRequest(BaseModel):
    """Request for processing images with metadata and S3 upload"""
    paths: list[str]  # List of image file paths to process
    description: str
    brand: str
    materials: list[str]
    process: list[str]
    mechanism: str
    project: str
    person: str
    directory: Optional[str] = None  # Optional directory context for S3 upload


class ProcessResponse(BaseModel):
    """Response for processing endpoint"""
    message: str
    files_processed: int
    s3_uris: dict[str, str]  # Mapping of filename to S3 URI


class SearchRequest(BaseModel):
    """Request for searching images"""
    query: str
    k: int = 3
    score_threshold: float = 0.5
    use_hybrid: bool = True
    keyword_weight: float = 0.5


class ImageResult(BaseModel):
    """Image search result"""
    url: str
    s3_uri: str
    filename: str
    description: Optional[str] = None
    brand: Optional[str] = None
    materials: Optional[list[str]] = None
    process: Optional[list[str]] = None
    mechanism: Optional[str] = None
    project: Optional[str] = None
    person: Optional[str] = None
    timestamp: Optional[str] = None
    score: float


class SearchResponse(BaseModel):
    """Response for search endpoint"""
    query: str
    results: list[ImageResult]
    total_count: int
    filtered_count: int
    message: Optional[str] = None


class UpdateMetadataRequest(BaseModel):
    """Request for updating image metadata"""
    s3_uri: str
    description: Optional[str] = None
    brand: Optional[str] = None
    materials: Optional[list[str]] = None
    process: Optional[list[str]] = None
    mechanism: Optional[str] = None
    project: Optional[str] = None
    person: Optional[str] = None


class UpdateMetadataResponse(BaseModel):
    """Response for update metadata endpoint"""
    message: str
    s3_uri: str
    updated_fields: dict


class DeleteImageRequest(BaseModel):
    """Request for deleting an image"""
    s3_uri: str
    filename: str


class DeleteImageResponse(BaseModel):
    """Response for delete image endpoint"""
    message: str
    s3_uri: str
    deleted_from_s3: bool
    deleted_from_vector_db: bool


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"message": "MechLib Image Processor API", "status": "running"}

"""

  Browser Upload → Memory (UploadFile) → Disk (/tmp) → ExifTool → S3
                        ↑                    ↑
                    Need to save      Can't process in memory


"""
@app.post("/upload", response_model=ImageDiscoveryResponse)
async def upload_images(files: list[UploadFile] = File(...), directory: Optional[str] = None):
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

            saved_paths.append(str(file_path.absolute()))

        return ImageDiscoveryResponse(
            file_paths=saved_paths,
            count=len(saved_paths),
            directory=directory
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload files: {str(e)}"
        )


@app.post("/process", response_model=ProcessResponse)
def process_images(request: ProcessRequest):
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

        # Convert path strings to Path objects for path_list
        path_list = [Path(p) for p in request.paths]

        # Process images: embed metadata using ExifTool
        processor = ImageProcessor(metadata_list, path_list)
        processed_files = processor.metadata_to_imgs()

        if not processed_files:
            raise HTTPException(
                status_code=500,
                detail="Failed to add metadata to images"
            )

        # Upload to S3
        print(f"DEBUG: About to upload {len(processed_files)} files to S3")
        s3_manager = S3_StoreManager()
        print(f"DEBUG: S3 manager created, bucket: {s3_manager.aws_bucket_name}")
        s3_manager.add_files(processed_files, request.directory)
        print(f"DEBUG: Upload complete, img_data: {s3_manager.img_data}")

        # Get S3 URIs from img_data
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

        # Add S3 URIs back to metadata objects using processor method
        processor.s3_uris_to_metadata(filename_with_s3uri_obj)

        # Create documents using processor method
        documents = processor.make_documents()

        # Add documents to vector store
        vector_store = VectorStoreManager()
        vector_store.add_documents(documents)

        # Clean up temporary files after successful processing
        for processed_file in processed_files:
            try:
                processed_file.unlink()  # Delete the temporary file
            except Exception as e:
                # Log but don't fail the request if cleanup fails
                print(f"Warning: Failed to delete temp file {processed_file}: {e}")

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


@app.post("/search", response_model=SearchResponse)
def search_images(request: SearchRequest):
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
            results_with_scores = vector_manager.hybrid_search(
                query=request.query,
                k=k,
                keyword_weight=request.keyword_weight
            )
        else:
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

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search images: {str(e)}"
        )


@app.put("/update-metadata", response_model=UpdateMetadataResponse)
def update_metadata(request: UpdateMetadataRequest):
    """
    Update metadata for an image in the vector database and S3.

    This will:
    1. Download the image from S3
    2. Update the EXIF/XMP metadata using ExifTool
    3. Re-upload to S3
    4. Update the vector database

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

        # Search for all documents and filter manually
        # Use a broad search to get documents, then filter by s3_uri
        all_results = vector_manager.vector_store.similarity_search(
            query=request.description or "image",  # Use description or generic query
            k=1000,  # Get a large batch to ensure we find the document
        )

        # Find the document with matching s3_uri
        doc = None
        for result in all_results:
            if result.metadata.get('s3_uri') == request.s3_uri:
                doc = result
                break

        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Image not found with s3_uri: {request.s3_uri}"
            )

        # Store the langchain_id if available (for deletion)
        langchain_id = doc.metadata.get('langchain_id')
        filename = doc.metadata.get('filename', 'image')

        # Download image from S3 to temp file
        s3_key = request.s3_uri.replace(f"s3://{s3_manager.aws_bucket_name}/", "")

        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)

            # Download from S3
            s3_manager.s3_client.download_file(
                s3_manager.aws_bucket_name,
                s3_key,
                str(temp_path)
            )

            # Create Metadata object with updated fields
            # IMPORTANT: filename must be the full path to the temp file for ExifTool to find it
            from src.mechlib.metadata_fetcher import Metadata

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
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update image metadata with ExifTool"
                )

            # Re-upload to S3 (overwrites existing)
            s3_manager.s3_client.upload_file(
                str(temp_path),
                s3_manager.aws_bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': f'image/{temp_path.suffix.lstrip(".")}',
                    'ContentDisposition': 'inline'
                }
            )

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

        return UpdateMetadataResponse(
            message="Metadata updated successfully in S3 and vector database",
            s3_uri=request.s3_uri,
            updated_fields=updated_fields
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update metadata: {str(e)}"
        )


@app.delete("/delete-image", response_model=DeleteImageResponse)
def delete_image(request: DeleteImageRequest):
    """
    Delete an image from S3 and vector database.

    Args:
        request: DeleteImageRequest with s3_uri and filename

    Returns:
        DeleteImageResponse with deletion status
    """
    try:
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
        except Exception as e:
            print(f"Warning: Failed to delete from S3: {e}")

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
            else:
                print(f"Warning: No document found with s3_uri: {request.s3_uri}")

        except Exception as e:
            print(f"Warning: Failed to delete from vector DB: {e}")

        if not deleted_from_s3 and not deleted_from_vector_db:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete image from both S3 and vector database"
            )

        return DeleteImageResponse(
            message=f"Image '{request.filename}' deleted successfully",
            s3_uri=request.s3_uri,
            deleted_from_s3=deleted_from_s3,
            deleted_from_vector_db=deleted_from_vector_db
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete image: {str(e)}"
        )
