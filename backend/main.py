
import logging

from backend.src.mechlib.img_fetcher import ImageFetcher
from backend.src.mechlib.img_processor import ImageProcessor
from backend.src.mechlib.s3_store import S3_StoreManager
from backend.src.mechlib.pinecone_vector_store import VectorStoreManager

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

    # Select images from file or dir
    path = ''
    directory = None
    fetcher = ImageFetcher()
    fetcher.add_path(path)

    if fetcher.directory:
        directory = fetcher.directory

    # Add metadata to selected images
    processor = ImageProcessor(fetcher.metadata_list)
    processed_files = processor.metadata_to_imgs()

    # Upload to S3 and get S3_URIs
    s3_manager = S3_StoreManager()
    img_data = s3_manager.add_files(processed_files, directory)

    # Add S3_URIs to the metadata in selected images
    processor.s3_uris_to_metadata(img_data)

    # Make Documents with all the Metadata
    documents = processor.make_documents()

    # Add Documents to Vector Database
    vector_manager = VectorStoreManager()
    vector_manager.add_documents(documents)

