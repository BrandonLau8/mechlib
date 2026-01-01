import logging
from pathlib import Path

from .metadata_fetcher import Metadata

logger = logging.getLogger(__name__)


class ImageFetcher:
    """
    Get Images locally

    input_path: Input the path for image(s) directory or file
    :arg
    :return img_path:Path

    get_images: Get list of Image Paths from directory or file
    :arg img_path:str
    :return path_list:List[Path] OR []

    _get_paths: Get list of paths from directory
    :arg img_path:Path
    :return path_list: List[Path] OR []

    _get_path: Get list of paths from file
    :arg img_path:Path
    :return path_list: List[Path] OR []

    """

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}

    def __init__(self):
        self.metadata_list: list[Metadata] = []
        self.directory:str | None = None
        self.path_list:list[Path] = []




    def get_path(self, path:Path) -> Path | None:
        for p in self.paths:
            if p == path:
                logger.info(f'Found: {path}')
                return path

        logger.warning(f'Not Found: {path}')
        return None

    def add_path(self, path:str):
        path = Path(path)

        # Check if Path exists
        for metadata in self.metadata_list:
            if metadata.filename == path.name:
                logger.warning('Path already exists')

        # Add files from dir to Path List and create Metadata
        if path.is_dir():
            self.directory = path.name
            for p in path.rglob('*'):
                if p.is_file() and p.suffix.lower() in self.SUPPORTED_FORMATS:
                    metadata = Metadata(p.name)
                    self.metadata_list.append(metadata)
                    self.path_list.append(p)

            logger.info(f"Added {len(self.metadata_list)} images from directory: {str(path)}")

        # Add file to Path List and create Metadata
        elif path.is_file() and path.suffix.lower() in self.SUPPORTED_FORMATS:
            metadata = Metadata(path.name)
            self.metadata_list.append(metadata)
            self.path_list.append(path)

        else:
            logger.error('Could not add Path')

    def remove_path(self, path:str):
        try:
            for metadata in self.metadata_list:
                if metadata.filename != path:
                    path_metadata = metadata
                    self.metadata_list.remove(path_metadata)
                    break

            logger.info(f'Path Removed: {path}')

        except ValueError as e:
            logger.warning(f'Path Not Found: {path} {e}')


    # def identify_source(path: str) -> str:
    #     """
    #     Identify image source from path
    #
    #     Returns: 'local', 's3', 'gdrive', or 'url'
    #     """
    #     parsed = urlparse(path)
    #
    #     # Check URI scheme
    #     if parsed.scheme == 's3':
    #         return 's3'
    #     elif parsed.scheme == 'gs':  # Google Cloud Storage
    #         return 'gcs'
    #     elif 'drive.google.com' in path:
    #         return 'gdrive'
    #     elif parsed.scheme in ['http', 'https']:
    #         return 'url'
    #     elif parsed.scheme in ['', 'file'] or Path(path).exists():
    #         return 'local'
    #     elif parsed.scheme
    #     else:
    #         raise ValueError(f"Unknown source for path: {path}")


