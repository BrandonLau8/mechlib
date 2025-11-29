import logging
from pathlib import Path
from typing import List, Optional, Dict

import exiftool
import questionary
from prompt_toolkit.shortcuts import CompleteStyle

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

    @staticmethod
    def input_path()->Path:
        answer=questionary.path(
            "Where is your image path?",
            complete_style=CompleteStyle.MULTI_COLUMN
        ).ask()

        img_path = Path(answer).absolute()

        return img_path

    def get_images(self, path:Path) -> List[Path]:

        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return []

        if path.is_dir():
            path_list = self._get_paths(path)
            return path_list

        elif path.is_file():
            # Check if it's an image
            if path.suffix.lower() in self.SUPPORTED_FORMATS:
                path_list = self._get_path(path)
                return path_list
            else:
                logger.warning(f"Image file is not supported: {path}")
                return []
        else:
            logger.warning(f"Not Directory: {path}")
            return []

    def _get_paths(self, directory:Path) -> List[Path]:
        """
        Get all image file paths from local directory

        Returns:
            List of Path objects pointing to image files
        """
        # Find all supported image files
        paths = []
        for path in directory.rglob('*'):
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_FORMATS:
                paths.append(path)


        logger.info(f"{len(paths)} images in directory: {directory}")
        for path in paths:
            logger.info(f'Found: {path}')

        return paths


    def _get_path(self, path:Path) -> List[Path]:
        """
        Get image file path from local directory

        Returns:
            List of Path objects pointing to image files
        """
        paths = []
        if path.is_file() and path.suffix.lower() in self.SUPPORTED_FORMATS:
            paths.append(path)
        logger.info(f'Found: {path}')
        return paths



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


