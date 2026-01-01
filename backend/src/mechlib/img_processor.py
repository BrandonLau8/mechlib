import datetime
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
import exiftool
from exiftool import ExifTool

from langchain_core.documents import Document

from .metadata_fetcher import Metadata

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

    def __init__(self, metadata_list, path_list:Optional[list]):
        self.exiftool:ExifTool = exiftool.ExifToolHelper()
        self.metadata_list: list[Metadata] = metadata_list
        self.documents: list[Document] = []
        self.path_list: Optional[list[Path]] = path_list

    # def _get_path(self, path:Path) -> Path | None:
    #     for p in self.path_list:
    #         if p == path:
    #             return path
    #     return None

    def _get_tags(self, processed_files:list[Path]):
        et = self.exiftool
        tags = [
            'FileName',
            'Description',
            'Brand',
            'Materials',
            'Process',
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
                # Get absolute path to config file (backend/.ExifTool_config)
                config_path = str(Path(__file__).parent.parent.parent / '.ExifTool_config')
                logger.info(f'Config path: {config_path}')

                # Use subprocess to run exiftool directly (we know this works from CLI)
                cmd = [
                    'exiftool',
                    '-config', config_path,
                    f'-XMP-mechlib:Project={metadata.project}',
                    f'-XMP-mechlib:Person={metadata.person}',
                    f'-XMP-mechlib:Brand={metadata.brand}',
                    f'-XMP-mechlib:Mechanism={metadata.mechanism}',
                    f'-XMP-mechlib:Description={metadata.description}',
                    f'-XMP-mechlib:Timestamp={datetime.datetime.now().astimezone().strftime("%Y:%m:%d %H:%M:%S %Z")}',
                    '-overwrite_original',
                    metadata.filename

                ]
                # Add materials (array)
                for material in metadata.materials:
                    cmd.insert(-2, f"-XMP-mechlib:Materials={material}")

                # Add process (array)
                for process in metadata.process:
                    cmd.insert(-2, f"-XMP-mechlib:Process={process}")

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
                # self._get_tags(processed_files)

            return processed_files

        except Exception as e:
            logger.error(f"Error adding tags to {str(e)}")
            return []

    def s3_uris_to_metadata(self, img_data:dict):
        print(f"DEBUG s3_uris_to_metadata: img_data keys = {list(img_data.keys())}")
        logger.info(f"s3_uris_to_metadata called with img_data keys: {list(img_data.keys())}")
        for metadata in self.metadata_list:
            print(f"DEBUG: Looking for filename = {metadata.filename}")
            logger.info(f"Looking for metadata.filename: {metadata.filename}")
            if img_data.get(metadata.filename):
                metadata.s3_uri = img_data.get(metadata.filename)
                print(f"DEBUG: s3_uri SET to {metadata.s3_uri}")
                logger.info(f's3_uri added in {metadata.filename}: {metadata.s3_uri}')
            else:
                print(f"DEBUG: s3_uri NOT FOUND for {metadata.filename}, available: {list(img_data.keys())}")
                logger.warning(f's3_uri not added in {metadata.filename}. Available keys: {list(img_data.keys())}')

    def make_documents(self) -> List[Document]:
        documents = []

        for metadata in self.metadata_list:
            metadata_dict = metadata.to_dict()
            tag_string = ''
            for key, value in metadata_dict.items():
                tag_string += f'{key}:{value}, '

            page_content = f'{metadata.description} Tags: [{tag_string}]'
            document = Document(
                page_content=page_content,
                metadata=metadata_dict
            )
            logger.info(f'Document made {document}')

            documents.append(document)
            logger.info(f'Listed documents {documents}')

        return documents



    def extract_metadata_from_imgs(self):
        """Extract XMP metadata from images and update existing Metadata objects."""
        try:
            # Get absolute path to config file (backend/.ExifTool_config)
            config_path = str(Path(__file__).parent.parent.parent / '.ExifTool_config')

            # Use subprocess to run exiftool with config file
            for file_path in self.path_list:
                filename = file_path.name

                # Find the corresponding Metadata object in self.metadata_list
                metadata = None
                for m in self.metadata_list:
                    if m.filename == filename:
                        metadata = m
                        break

                if not metadata:
                    logger.warning(f"No Metadata object found for {filename}")
                    continue

                # Run exiftool with config to read XMP-mechlib tags
                cmd = [
                    'exiftool',
                    '-config', config_path,
                    '-XMP-mechlib:Description',
                    '-XMP-mechlib:Brand',
                    '-XMP-mechlib:Materials',
                    '-XMP-mechlib:Process',
                    '-XMP-mechlib:Mechanism',
                    '-XMP-mechlib:Project',
                    '-XMP-mechlib:Person',
                    '-XMP-mechlib:Timestamp',
                    '-j',  # JSON output for easier parsing
                    str(file_path)
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f'exiftool failed for {filename}: {result.stderr}')
                    continue

                # Parse JSON output
                import json
                data = json.loads(result.stdout)[0]  # First element is the file

                # Update the existing Metadata object
                if 'Description' in data:
                    metadata.description = data['Description']
                    logger.info(f'Extracted Description: {metadata.description}')

                if 'Brand' in data:
                    metadata.brand = data['Brand']
                    logger.info(f'Extracted Brand: {metadata.brand}')

                if 'Materials' in data:
                    # Materials is an array in XMP
                    materials = data['Materials']
                    if isinstance(materials, str):
                        metadata.materials = [materials]
                    else:
                        metadata.materials = materials
                    logger.info(f'Extracted Materials: {metadata.materials}')

                if 'Process' in data:
                    # Process is an array in XMP
                    process = data['Process']
                    if isinstance(process, str):
                        metadata.process = [process]
                    else:
                        metadata.process = process
                    logger.info(f'Extracted Process: {metadata.process}')

                if 'Mechanism' in data:
                    metadata.mechanism = data['Mechanism']
                    logger.info(f'Extracted Mechanism: {metadata.mechanism}')

                if 'Project' in data:
                    metadata.project = data['Project']
                    logger.info(f'Extracted Project: {metadata.project}')

                if 'Person' in data:
                    metadata.person = data['Person']
                    logger.info(f'Extracted Person: {metadata.person}')

                if 'Timestamp' in data:
                    metadata.timestamp = data['Timestamp']
                    logger.info(f'Extracted Timestamp: {metadata.timestamp}')

                logger.info(f'✓ Metadata extracted from {filename}')

        except Exception as e:
            logger.error(f"Extraction Failed: {str(e)}", exc_info=True)





