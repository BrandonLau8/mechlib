from typing import Optional

from pydantic import BaseModel


class GoogleAuthRequest(BaseModel):
    """Request for Google OAuth authentication"""
    id_token: str  # Google ID token from frontend

class GoogleAuthResponse(BaseModel):
    """Response for Google OAuth authentication"""
    access_token: str
    token_type: str = "bearer"
    email: str
    name: str
    picture: str

class UserInfoResponse(BaseModel):
    """Response for user info endpoint"""
    email: str
    name: str

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
    score_threshold: float = 0.5 #Overridden by frontend
    use_hybrid: bool = True
    keyword_weight: float = 0.5 #Not used


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
