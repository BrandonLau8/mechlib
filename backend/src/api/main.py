import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import config
from src.api.routers import auth, image
from src.mechlib.s3_store import S3_StoreManager
from src.mechlib.vector_store import VectorStoreManager

# Configure logging - must happen before creating loggers
logging.basicConfig(
    level=config.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Override uvicorn's configuration
)

logger = logging.getLogger(__name__)
logger.info(f"Application logging configured at level: {config.log_level}")

app = FastAPI(title="MechLib Image Processor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",  # Alternative localhost
    ],
    allow_credentials=True,  # Required for Authorization headers
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(image.router, tags=["images"])



@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"message": "MechLib Image Processor API", "status": "running"}

@app.get("/s3_health")
def s3_health():
    try:
        s3_manager = S3_StoreManager()
        return {"message": "S3 Check", "status": "running"}
    except Exception as e:
        logger.error(f"S3 Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/vectordb_health")
def vectordb_health():
    try:
        vector_store = VectorStoreManager()
        return {"message": "PGVector DB Check", "status": "running"}
    except Exception as e:
        logger.error(f"PGVector Health Check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")




