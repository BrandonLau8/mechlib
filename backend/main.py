
import logging
from platform import processor

from src.mechlib.vector_store import VectorStoreManager
from src.mechlib.img_fetcher import ImageFetcher
from src.mechlib.img_processor import ImageProcessor

logger = logging.getLogger(__name__)


"""

- Select directory with images or individual image
- Either select or type preset tag names. 
- images uploaded to the cloud S3
- images processed into documents via langchain containing tag names and img_url
- documents are embedded into Pinecone Vector Database
"""




# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    logging.basicConfig(
        level=logging.INFO,
        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # # Select images from file or dir
    # path = ''
    # directory = None
    # fetcher = ImageFetcher()
    # fetcher.add_path(path)
    #
    # if fetcher.directory:
    #     directory = fetcher.directory
    #
    # # Add metadata to selected images
    # processor = ImageProcessor(fetcher.metadata_list)
    # processed_files = processor.metadata_to_imgs()
    #
    # # Upload to S3 and get S3_URIs
    # s3_manager = S3_StoreManager()
    # img_data = s3_manager.add_files(processed_files, directory)
    #
    # # Add S3_URIs to the metadata in selected images
    # processor.s3_uris_to_metadata(img_data)
    #
    # # Make Documents with all the Metadata
    # documents = processor.make_documents()
    #
    # # Add Documents to Vector Database
    # vector_manager = VectorStoreManager()
    # vector_manager.add_documents(documents)

    # Process Files Downloaded from S3
    from config import config

    # Configure paths
    LOCAL_DOWNLOAD_PATH = ''
    S3_DIRECTORY_PREFIX = None  # Set to the original S3 directory (e.g., "teardown_photos"), or None for root

    fetcher = ImageFetcher()
    fetcher.add_path(LOCAL_DOWNLOAD_PATH)

    processor = ImageProcessor(fetcher.metadata_list, fetcher.path_list)
    processor.extract_metadata_from_imgs()

    # Set S3 URIs (reconstructing from bucket + filename)
    # Since files came from S3, we know the bucket and can reconstruct URIs
    # IMPORTANT: Use S3_DIRECTORY_PREFIX, NOT the local directory name
    for metadata in processor.metadata_list:
        # Use the original S3 directory prefix where files were uploaded
        if S3_DIRECTORY_PREFIX:
            s3_key = f"{S3_DIRECTORY_PREFIX}/{metadata.filename}"
        else:
            s3_key = metadata.filename

        metadata.s3_uri = f"s3://{config.aws_bucket_name}/{s3_key}"
        logger.info(f"Set s3_uri for {metadata.filename}: {metadata.s3_uri}")

    documents = processor.make_documents()

    # Add Documents to Vector Database
    vector_manager = VectorStoreManager()
    vector_manager.add_documents(documents)
