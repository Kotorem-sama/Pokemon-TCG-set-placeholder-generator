from PIL import Image, ImageEnhance
from io import BytesIO
from pathlib import Path

def retreive_extension(image_tuple: tuple[bytes, str]) -> str:
    match image_tuple[1].lower():
        case "image/jpeg":
            return ".jpg"
        case _:
            return ".fail"

def sanitize_filename(filename:str) -> str:
    invalid_characters = ["<", ">", ":", '"', "\\", "|", "?", "*"]

    for character in invalid_characters:
        filename = filename.replace(character, "")
    
    return filename.replace("/", "-")

def image_processor(current_image: tuple[bytes, str], card_number: str, set_name: str, variant:str):
    set_name = sanitize_filename(set_name)
    extension = retreive_extension(current_image)
    file_name = sanitize_filename(f"{card_number} - {variant}")

    SET_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "generated" / set_name
    SET_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(BytesIO(current_image[0])) as im:
        image_directory = SET_DIR / f"{file_name}{extension}"

        if variant in ["Holofoil", "Reverse Holofoil"]:
            template = get_template(variant).convert("RGBA")
            im = Image.alpha_composite(im.convert("RGBA"), template)

        grayscale_image = im.convert("L")
        grayscale_image.save(image_directory)

def get_template(variant:str):
    template_path = Path(__file__).resolve().parent.parent / "data" / "templates" / f"{variant}.png"
    template = Image.open(template_path).convert("RGBA")

    alpha_channel = template.getchannel("A")
    opacity = 64 / 255
    alpha_channel = ImageEnhance.Brightness(alpha_channel).enhance(opacity)

    template.putalpha(alpha_channel)

    return template