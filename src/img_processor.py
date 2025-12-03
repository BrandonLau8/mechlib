import datetime
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import exiftool
import questionary

from langchain_core.documents import Document


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

    def __init__(self):
        self.exiftool = exiftool.ExifToolHelper()

    def _get_metadata(self, path_list: list[Path]):
        et = self.exiftool
        tags = [
            'FileName',
            # 'SourceFile',
            'Description'
            'Brand',
            'Materials',
            'Mechanism',
            'Project',
            'Person',
            'Timestamp',
        ]
        metadata:List[Dict[str,Any]] = et.get_tags(path_list, tags)
        for tag in metadata:
            logger.info(tag)

    @staticmethod
    def _validate_metadata(metadata:Dict[str, Any]) -> bool:
        nonnulls = ['description', 'person']
        metadata_keylist = list(metadata.keys())
        all_found = True
        for nonnull in nonnulls:
            if nonnull not in metadata_keylist:
                all_found = False
                break

        if all_found:
            logger.info('Metadata Validated')
            return True
        else:
            logger.error('Metadata Not Validated')
            return False

    def make_documents(self, metadata:Dict[str, Any]) -> List[Document] | None:
        if self._validate_metadata(metadata):
            documents = []
            tag_string = ''
            for key, value in metadata.items():
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
        else:
            return None

    def extract_metadata(self, file_path:Path, s3_url:str, s3_uri:str) -> Dict[str, Any]:

        try:
            metadata = {
                'filename': None,
                # 'sourcefile': None,
                "description": None,
                "brand": None,
                "materials": None,
                'mechanism': None,
                "project": None,
                "person": None,
                'timestamp': None,
                "s3_url": s3_url,
                "s3_uri": s3_uri
            }
            logger.info(f'Adding S3 URL: {metadata["s3_url"]}')
            et = self.exiftool
            # Get all metadata from the image
            for data in et.get_metadata(str(file_path)):
                for img_key, img_value in data.items():
                    if ':' in img_key:
                        img_key = img_key.split(':', 1)
                        img_key = img_key[1]

                        # Extract title from FileName (without extension)
                        if 'FileName' in img_key:
                            # Remove file extension (.png, .jpg, etc.)
                            metadata["filename"] = Path(img_value).stem
                            logger.info(f'Extracted FileName: {metadata["filename"]}')

                        # Extract description
                        if 'Description' in img_key:
                            metadata['description'] = img_value
                            logger.info(f'Extracted Description: {metadata["description"]}')

                        # Extract brand
                        if 'Brand' in img_key:
                            metadata['brand'] = img_value
                            logger.info(f'Extracted Brand: {metadata["brand"]}')

                        # Extract materials
                        if 'Materials' in img_key:
                            metadata['materials'] = img_value
                            logger.info(f'Extracted Materials: {metadata["materials"]}')

                        # Extract mechanism
                        if 'Mechanism' in img_key:
                            metadata['mechanism'] = img_value
                            logger.info(f'Extracted Mechanism: {metadata["mechanism"]}')

                        # Extract project
                        if 'Project' in img_key:
                            metadata['project'] = img_value
                            logger.info(f'Extracted Project: {metadata["project"]}')

                        # Extract person
                        if 'Person' in img_key:
                            metadata['person'] = img_value
                            logger.info(f'Extracted Person: {metadata["person"]}')

                        # Extract timestamp
                        if 'Timestamp' in img_key:
                            metadata['timestamp'] = img_value
                            logger.info(f'Extracted Timestamp: {metadata["timestamp"]}')

            return metadata
        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {str(e)}")
            return {}



    @staticmethod
    def _input_metadata() -> Dict[str, str]:
        answers = questionary.form(
            description=questionary.text('Description: ', multiline=True),
            brand=questionary.text('Brand: '),

            materials=questionary.checkbox(
                'Materials: ',
                choices=[
                    'Plastic',
                    'Metal',
                    'Silicone'
                ],
            ),

            mechanism=questionary.text('Mechanism: '),
            project=questionary.text('Project: '),
            person=questionary.text('Person: ')

        ).ask()
        logging.info(answers)

        return answers

    def add_metadata(self, path_list: list[Path]) -> bool:
        answers = self._input_metadata()

        try:
            # Get absolute path to config file
            config_path = str(Path(__file__).parent.parent / '.ExifTool_config')
            # logger.info(f'Config path: {config_path}')

            # Use subprocess to run exiftool directly (we know this works from CLI)
            cmd = [
                'exiftool',
                '-config', config_path,
                f'-XMP-mechlib:Project={answers['person']}',
                f'-XMP-mechlib:Person={answers['person']}',
                f'-XMP-mechlib:Brand={answers['brand']}',
                f'-XMP-mechlib:Materials={answers['materials']}',
                f'-XMP-mechlib:Mechanism={answers['mechanism']}',
                f'-XMP-mechlib:Project={answers['project']}',
                f'-XMP-mechlib:Person={answers['person']}',
                f'-XMP-mechlib:Description={answers['description']}',
                f'-XMP-mechlib:Timestamp={datetime.datetime.now().astimezone().strftime("%Y:%m:%d %H:%M:%S %Z")}',
                '-overwrite_original',

            ]
            cmd.extend(str(path) for path in path_list)
            logger.info(f'Running command: {" ".join(cmd)}')
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f'exiftool failed: {result.stderr}')
                return False

            logger.info(f'exiftool output: {result.stdout}')
            logger.info('✓ Tags written successfully!')

            self._get_metadata(path_list)

            return True

        except Exception as e:

            logger.error(f"Error adding tags to {path_list}: {str(e)}")

            return False
