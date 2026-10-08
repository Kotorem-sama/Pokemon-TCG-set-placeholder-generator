from PIL import Image, ImageEnhance
from io import BytesIO
from pathlib import Path
from os.path import isfile
from os import listdir

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
    
    image_directory = SET_DIR / f"{file_name}{extension}"
    if isfile(image_directory):
        return

    template_path = Path(__file__).resolve().parent.parent / "data" / "templates"

    with Image.open(BytesIO(current_image[0])) as im:
        # Apparently i do save rarities, so I should check whether something is a full art,
        # double rar, IR of SIR om er voor te zorgen dat de holofoil template niet wordt toegepast daar op.
        if f"{variant}.png" in listdir(template_path):
            template = get_template(variant).convert("RGBA")
            im = Image.alpha_composite(im.convert("RGBA"), template)

        grayscale_image = im.convert("L")
        grayscale_image.save(image_directory)

def get_template(variant:str):
    template_path = Path(__file__).resolve().parent.parent / "data" / "templates" / f"{variant}.png"
    template = Image.open(template_path).convert("RGBA")

    alpha_channel = template.getchannel("A")
    opacity = 100 / 255
    alpha_channel = ImageEnhance.Brightness(alpha_channel).enhance(opacity)

    template.putalpha(alpha_channel)

    return template