import mimetypes
from pathlib import Path
from typing import Optional
import logging
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from config import config

logger = logging.getLogger(__name__)


class S3_StoreManager:
    """
    Handle S3 uploads for images
    https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

    upload_file: Upload file to S3 Bucket. Save key to be file path
    :arg file_path:Path
    :arg s3_key: Optional[str] = None
    :return s3_uri: list(str)

    upload_folder: Upload folder to S3 Bucket. Note: Files uploaded with directory as prefix
    :arg folder_path:Path
    :arg s3_prefix: str
    :return s3_uri_list: list(str)

    get_presigned_url: Get presigned URL for access to image URL before expiration. Open through browser.
    :arg s3_uri: str | Path
    :arg expiration: int

    """

    def __init__(self):
        self.aws_bucket_name = config.aws_bucket_name
        self.aws_region = config.aws_region

        if not self.aws_bucket_name:
            raise ValueError('AWS_S3_BUCKET not set in env')

        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        self.s3_resource = boto3.resource('s3', region_name=self.aws_region)
        self.expiration:int = 3600
        self.img_data:dict = {}


    def add_files(self, processed_files: list[Path], directory:Optional[str]):
        try:
            for file in processed_files:
                # If dir uploaded, use directory/filename as s3_key, else use just filename
                if directory:
                    s3_key = f"{directory}/{file.name}"
                else:
                    s3_key = file.name

                # Get the file type '.jpg', '.jpeg', '.png', '.webp'
                content_type, _ = mimetypes.guess_type(file.name)
                self.s3_client.upload_file(
                    file,
                    self.aws_bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'ContentDisposition': 'inline'
                    }
                )
                s3_uri = f"s3://{self.aws_bucket_name}/{s3_key}"

                self.img_data[file.name] = s3_uri

                logger.info(f"Uploaded {file.name} to {s3_uri}")

        except ClientError as e:
            logger.error(f"Failed to upload: {e}")

    def generate_presigned_url(self, s3_uri:str) -> str:
        try:
            # Ensure s3_uri is a string (defensive handling for corrupted data)
            if isinstance(s3_uri, bytes):
                logger.warning(f"s3_uri is bytes, converting to string: {s3_uri}")
                s3_uri = s3_uri.decode('utf-8')

            if s3_uri is None:
                raise ValueError("s3_uri cannot be None")

            s3_uri = str(s3_uri)  # Ensure it's a string
            logger.info(f"Generating presigned URL for: {s3_uri}")

            # Get the file type '.jpg', '.jpeg', '.png', '.webp'
            parsed = urlparse(s3_uri)

            s3_key = parsed.path.lstrip('/')
            content_type, _ = mimetypes.guess_type(s3_uri)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.aws_bucket_name,
                    'Key': s3_key,
                    'ResponseContentType': content_type,
                    'ResponseContentDisposition': 'inline'
                },
                ExpiresIn=self.expiration
            )
            logger.info(f"Generated presigned URL for {s3_uri} (valid for {self.expiration}s)")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_uri}: {e}")
            raise




    # def list_objects(self, prefix: str = '') -> list[str]:
    #     try:
    #         bucket = self.s3_resource.Bucket(self.bucket_name)
    #         files = [obj.key for obj in bucket.objects.filter(Prefix=prefix)]
    #         logger.info(f"Found {len(files)} files with prefix '{prefix}'")
    #         return files
    #
    #     except ClientError as e:
    #         logger.error(f"Failed to list files: {e}")
    #         raise
    #
    # def get_urls_for_files(self, prefix: str = '', expiration: int = 3600) -> dict[str, str]:
    #
    #     files = self.list_files(prefix)
    #     urls = {}
    #
    #     for s3_key in files:
    #         try:
    #             urls[s3_key] = self.generate_presigned_url(s3_key, expiration)
    #         except Exception as e:
    #             logger.error(f"Failed to generate URL for {s3_key}: {e}")
    #             continue
    #
    #     return urls
    #
