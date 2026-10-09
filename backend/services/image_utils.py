from pathlib import Path
from logging import getLogger
from services.image_generation_service import ImageGeneration

class ImageUtils:
    """Utility methods for image operations and file management."""
    
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
    
    @staticmethod
    def get_images_in_set_folder(set_name: str) -> list[str]:
        """
        Retrieve all image file paths for a given Pokémon set.
        
        Args:
            set_name: Name of the Pokémon set folder
            
        Returns:
            list[str]: List of absolute paths to image files, sorted alphabetically
        """
        logger = getLogger(__name__)

        set_name = ImageGeneration().sanitize_filename(set_name)
        
        try:
            set_directory = (
                Path(__file__).resolve().parent.parent
                / "data"
                / "generated"
                / set_name
            )
            
            if not set_directory.exists():
                logger.warning(f"Set folder not found: {set_directory}")
                return []
            
            image_files = [
                str(image_file)
                for image_file in set_directory.iterdir()
                if image_file.is_file()
                and image_file.suffix.lower() in ImageUtils.SUPPORTED_EXTENSIONS
            ]
            
            image_files.sort()
            logger.info(f"Found {len(image_files)} images in set '{set_name}'")
            return image_files
            
        except Exception as e:
            logger.error(f"Error retrieving images for set '{set_name}': {e}")
            return []