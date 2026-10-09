from logging import getLogger
from pathlib import Path

from services.name_service import sanitize_filename


class ImageUtils:
    """Utility methods for image operations and file management."""

    SUPPORTED_EXTENSIONS: list[str] = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
    ]

    def __init__(self) -> None:
        self.logger = getLogger(__name__)

    def get_images_in_set_folder(self, set_name: str) -> list[str]:
        """
        Retrieve all image file paths for a given Pokémon set.

        Args:
            set_name: Name of the Pokémon set folder

        Returns:
            list[str]: List of absolute paths to image files, sorted alphabetically
        """

        set_name = sanitize_filename(set_name)

        try:
            set_directory = (
                Path(__file__).resolve().parent.parent / "data" / "generated" / set_name
            )

            if not set_directory.exists():
                self.logger.warning(f"Set folder not found: {set_directory}")
                return []

            image_files = [
                str(image_file)
                for image_file in set_directory.iterdir()
                if image_file.is_file()
                and image_file.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ]

            image_files.sort()
            self.logger.info(f"Found {len(image_files)} images in set '{set_name}'")
            return image_files

        except Exception as e:
            self.logger.error(f"Error retrieving images for set '{set_name}': {e}")
            return []
