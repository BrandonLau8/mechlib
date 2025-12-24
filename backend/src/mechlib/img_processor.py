import datetime
import logging
import subprocess
from pathlib import Path
from typing import List
import exiftool
from exiftool import ExifTool

from langchain_core.documents import Document

from backend.src.mechlib.metadata_fetcher import Metadata

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Process images from the local path or cloud

    _input_metadata: Input metadata of path either directory or image
    :arg
    :return answers

    add_metadata: Add metadata to image(s)
    :arg image: Path
    :return bool

    _get_metadata: Get the metadata that was added
    :arg image: Path
    :return None

    extract_metadata: Extract metadata from image
    :arg image: Path
    :return metadata: Dict[str:Any]

    validate_metadata: Validate metadata
    :arg metadata:Dict[str, Any]
    :return bool

    make_documents: Turn metadata from image(s) into List of Langchain Documents
    :arg metadata: Dict[str:Any]
    :return document: Document | None
    https://reference.langchain.com/python/langchain_core/documents/#langchain_core.documents.base.Document

    Metadata
    - title: Image title
    - sourcefile: Image path
    - description: Detailed description
    - brand: Brand/manufacturer name
    - materials: List of materials or comma-separated string
    - project: Project name
    - person: Person's name associated with image
    - timestamp: Timestamp

    """

    def __init__(self, metadata_list):
        self.exiftool:ExifTool = exiftool.ExifToolHelper()
        self.metadata_list: list[Metadata] = metadata_list
        self.documents: list[Document] = []

    def _get_path(self, path:Path) -> Path | None:
        for p in self.path_list:
            if p == path:
                return path
        return None

    def _get_tags(self, processed_files:list[Path]):
        et = self.exiftool
        tags = [
            'FileName',
            'Description'
            'Brand',
            'Materials',
            'Mechanism',
            'Project',
            'Person',
            'Timestamp',
        ]

        metadata:List[dict] = et.get_tags(processed_files, tags)
        for tag in metadata:
            logger.info(tag)

    def get_metadata_list(self) -> list[Metadata]:
        return self.metadata_list

    def metadata_to_imgs(self) -> list[Path]:
        try:
            processed_files = []
            for metadata in self.metadata_list:
                # Get absolute path to config file
                config_path = str(Path(__file__).parent.parent / '.ExifTool_config')
                # logger.info(f'Config path: {config_path}')

                # Use subprocess to run exiftool directly (we know this works from CLI)
                cmd = [
                    'exiftool',
                    '-config', config_path,
                    f'-XMP-mechlib:Project={metadata.project}',
                    f'-XMP-mechlib:Person={metadata.person}',
                    f'-XMP-mechlib:Brand={metadata.brand}',
                    f'-XMP-mechlib:Materials={metadata.materials}',
                    f'-XMP-mechlib:Mechanism={metadata.mechanism}',
                    f'-XMP-mechlib:Description={metadata.description}',
                    f'-XMP-mechlib:Timestamp={datetime.datetime.now().astimezone().strftime("%Y:%m:%d %H:%M:%S %Z")}',
                    '-overwrite_original',
                    metadata.filename

                ]
                # Add materials (array)
                for material in metadata.materials:
                    cmd.insert(-2, f"-XMP-mechlib:Materials={material}")

                # Add Metadata to each Image
                # cmd.extend(str(path) for path in self.path_list)
                logger.info(f'Running command: {" ".join(cmd)}')
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f'exiftool failed: {result.stderr}')

                processed_file = Path(metadata.filename)
                processed_files.append(processed_file)

                logger.info(f'exiftool output: {result.stdout}')
                logger.info('✓ Tags written successfully!')

                # View Metadata
                self._get_tags(processed_files)

            return processed_files

        except Exception as e:
            logger.error(f"Error adding tags to {str(e)}")
            return []

    def s3_uris_to_metadata(self, img_data:dict):
        for metadata in self.metadata_list:
            if img_data.get(metadata.filename):
                metadata.s3_uri = img_data.get(metadata.filename)
                logger.info(f's3_uri added in {metadata.filename}')
            else:
                logger.warning(f's3_uri not added in {metadata.filename}')

    def make_documents(self) -> List[Document]:
        documents = []

        for metadata in self.metadata_list:
            metadata_dict = metadata.to_dict()
            tag_string = ''
            for key, value in metadata_dict.items():
                tag_string += f'{key}:{value}, '

            page_content = f'{metadata['description']} Tags: [{tag_string}]'
            document = Document(
                page_content=page_content,
                metadata=metadata
            )
            logger.info(f'Document made {document}')

            documents.append(document)
            logger.info(f'Listed documents {documents}')

        return documents

    # def remake_documents(self):

    # def extract_metadata(self, file_path:Path, s3_url:str, s3_uri:str) -> dict[str, Any]:
    #     try:
    #         metadata = self.metadata
    #         logger.info(f'Adding S3 URL: {metadata.s3_url}')
    #         et = self.exiftool
    #         # Get all metadata from the image
    #         for data in et.get_metadata(str(file_path)):
    #             for img_key, img_value in data.items():
    #                 if ':' in img_key:
    #                     img_key = img_key.split(':', 1)
    #                     img_key = img_key[1]
    #
    #                     # Extract title from FileName (without extension)
    #                     if 'FileName' in img_key:
    #                         # Remove file extension (.png, .jpg, etc.)
    #                         metadata["filename"] = Path(img_value).stem
    #                         logger.info(f'Extracted FileName: {metadata["filename"]}')
    #
    #                     # Extract description
    #                     if 'Description' in img_key:
    #                         metadata['description'] = img_value
    #                         logger.info(f'Extracted Description: {metadata["description"]}')
    #
    #                     # Extract brand
    #                     if 'Brand' in img_key:
    #                         metadata['brand'] = img_value
    #                         logger.info(f'Extracted Brand: {metadata["brand"]}')
    #
    #                     # Extract materials
    #                     if 'Materials' in img_key:
    #                         metadata['materials'] = img_value
    #                         logger.info(f'Extracted Materials: {metadata["materials"]}')
    #
    #                     # Extract mechanism
    #                     if 'Mechanism' in img_key:
    #                         metadata['mechanism'] = img_value
    #                         logger.info(f'Extracted Mechanism: {metadata["mechanism"]}')
    #
    #                     # Extract project
    #                     if 'Project' in img_key:
    #                         metadata['project'] = img_value
    #                         logger.info(f'Extracted Project: {metadata["project"]}')
    #
    #                     # Extract person
    #                     if 'Person' in img_key:
    #                         metadata['person'] = img_value
    #                         logger.info(f'Extracted Person: {metadata["person"]}')
    #
    #                     # Extract timestamp
    #                     if 'Timestamp' in img_key:
    #                         metadata['timestamp'] = img_value
    #                         logger.info(f'Extracted Timestamp: {metadata["timestamp"]}')
    #
    #         return metadata
    #     except Exception as e:
    #         logger.warning(f"Could not extract metadata from {file_path}: {str(e)}")
    #         return {}
    #
    #


