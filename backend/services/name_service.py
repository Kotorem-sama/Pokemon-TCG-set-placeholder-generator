def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters from filename to ensure filesystem compatibility.

    Args:
        filename: The filename to sanitize

    Returns:
        str: Sanitized filename with invalid characters removed or replaced
    """
    invalid_characters = ["<", ">", ":", '"', "\\", "|", "?", "*"]

    for character in invalid_characters:
        filename = filename.replace(character, "")

    return filename.replace("/", "-")
