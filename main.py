
# This is a sample Python script.
import logging
import os
from pathlib import Path
from platform import processor
from typing import Any, Dict


import exiftool
import logger
import questionary
import requests
from aiohttp.web_fileresponse import content_type
from botocore.exceptions import ClientError

from config import config
from src.img_fetcher import ImageFetcher
from prompt_toolkit.shortcuts import CompleteStyle

from src.img_processor import ImageProcessor
from src.s3_store import S3_StoreManager
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

    fetcher = ImageFetcher()
    s3_manager = S3_StoreManager()
    processor = ImageProcessor()
    vector_manager = VectorStoreManager()

    # Get Images to Add Metadata
    path = fetcher.input_path()

    # Get local_path
    path_list = fetcher.get_images(path)
    s3_uri_list = s3_manager.upload_all_files(path)


    if len(path_list) == len(s3_uri_list):
        try:
            processor.add_metadata(path_list)
            for i in range(len(path_list)):
                file = path_list[i]
                s3_uri = s3_uri_list[i]
                s3_url = s3_manager.generate_presigned_url(s3_uri)

                extracted_metadata = processor.extract_metadata(file, s3_url, s3_uri)
                documents = processor.make_documents(extracted_metadata)
                vector_manager.add_documents(documents)
        except Exception as e:
            logging.error(f'Processing failed: {str(e)}')
    else:
        logging.error('Local and S3 Paths Mismatched')

    # vector_manager = VectorStoreManager()
    # vector_manager.search()