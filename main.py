
# This is a sample Python script.
import logging
import os
from typing import Any, Dict


import exiftool
import logger
import questionary


from config import config
from src.img_fetcher import ImageFetcher
from prompt_toolkit.shortcuts import CompleteStyle

from src.img_processor import ImageProcessor
from src.vector_store import VectorStoreManager

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

    # # Get Images to Add Metadata
    # img_path = ImageFetcher.input_path()
    # Upload images to S3 and get url to put into metadata
    # images = ImageFetcher().get_images(img_path)

    # Add Metadata to Images
    processor = ImageProcessor()

    # for image in images:
    #     if processor.add_metadata(image):
    #         extracted_metadata = processor.extract_metadata(image)
    #         documents = processor.make_documents(extracted_metadata)
    #         vector_store = VectorStoreManager()
    #         vector_store.add_documents(documents)
    #     else:
    #         logger.error('Image Processing Failed')

    test_dir = config.project_root / 'test'
    processor.extract_metadata(test_dir)