from pathlib import Path
from typing import Optional
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File
from langchain_core.documents import Document
from pydantic import BaseModel

from backend.src.mechlib.img_fetcher import ImageFetcher
from backend.src.mechlib.img_processor import ImageProcessor
from backend.src.mechlib.s3_store import S3_StoreManager
from backend.src.mechlib.metadata_fetcher import Metadata
from backend.src.mechlib.vector_store import VectorStoreManager

app = FastAPI(title="MechLib Image Processor API")

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
    mechanism: str
    project: str
    person: str
    directory: Optional[str] = None  # Optional directory context for S3 upload


class ProcessResponse(BaseModel):
    """Response for processing endpoint"""
    message: str
    files_processed: int
    s3_uris: dict[str, str]  # Mapping of filename to S3 URI


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
            metadata.mechanism = request.mechanism
            metadata.project = request.project
            metadata.person = request.person

            metadata_list.append(metadata)

        # Process images: embed metadata using ExifTool
        processor = ImageProcessor(metadata_list)
        processed_files = processor.metadata_to_imgs()

        if not processed_files:
            raise HTTPException(
                status_code=500,
                detail="Failed to add metadata to images"
            )

        # Upload to S3
        s3_manager = S3_StoreManager()
        s3_manager.add_files(processed_files, request.directory)

        # Get S3 URIs from the manager (keys are basenames)
        s3_uris_by_basename = s3_manager.img_data

        if not s3_uris_by_basename:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload images to S3"
            )

        # Create a mapping with full paths as keys for metadata objects
        # (since metadata.filename contains full paths)
        s3_uris_by_fullpath = {}
        for processed_file in processed_files:
            basename = processed_file.name
            if basename in s3_uris_by_basename:
                s3_uris_by_fullpath[str(processed_file.absolute())] = s3_uris_by_basename[basename]

        # Add S3 URIs back to metadata objects
        documents = []
        for metadata in metadata_list:
            if s3_uris_by_fullpath.get(metadata.filename):
                metadata.s3_uri = s3_uris_by_fullpath.get(metadata.filename)

            metadata_dict = metadata.to_dict()
            tag_string = ''
            for key, value in metadata_dict.items():
                tag_string += f'{key}:{value}, '

            page_content = f'{metadata['description']} Tags: [{tag_string}]'
            document = Document(
                page_content=page_content,
                metadata=metadata
            )
            documents.append(document)

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
        s3_uris = s3_uris_by_basename

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
