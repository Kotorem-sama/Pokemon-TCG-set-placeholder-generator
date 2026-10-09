from logging import getLogger

logger = getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters from filename to ensure filesystem compatibility.

    Args:
        filename: The filename to sanitize

    Returns:
        str: Sanitized filename with invalid characters removed or replaced
    """
    try:
        invalid_characters = ["<", ">", ":", '"', "\\", "|", "?", "*"]

        for character in invalid_characters:
            filename = filename.replace(character, "")

        return filename.replace("/", "-")
    except Exception as e:
        logger.error(f"Error sanitizing filename '{filename}': {e}")
        return "unnamed"
