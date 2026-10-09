from PIL import Image, ImageEnhance, ImageOps
from io import BytesIO
from pathlib import Path
from os.path import isfile
from database.db_operations import Card

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

def image_processor(current_image: tuple[bytes, str], current_card: Card, set_name: str, variant:str):
    set_name = sanitize_filename(set_name)
    extension = retreive_extension(current_image)
    file_name = sanitize_filename(f"{current_card.number} - {variant}")

    SET_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "generated" / set_name
    SET_DIR.mkdir(parents=True, exist_ok=True)
    
    image_directory = SET_DIR / f"{file_name}{extension}"
    if isfile(image_directory):
        return

    with Image.open(BytesIO(current_image[0])) as im:
        im = combine_with_template(im, variant, current_card.rarity)

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

def combine_with_template(im: Image.Image, variant:str, card_rarity:str | None):
    template_path = Path(__file__).resolve().parent.parent / "data" / "templates"#
    rarities = [
        "Double Rare",
        "Illustration Rare",
        "Mega Attack Rare",
        "Mega Hyper Rare",
        "Promo",
        "RGB Rare",
        "Special Illustration Rare",
        "Ultra Rare",
    ]

    template_file = template_path / f"{variant}.png"
    base_image = im.convert("RGBA")

    if not template_file.is_file() or card_rarity in rarities:
        return base_image

    template = get_template(variant).convert("RGBA")

    target_size: tuple[int, int] = (
        base_image.width,
        base_image.height
    )

    if template.size != target_size:
        template = ImageOps.fit(template, base_image.size)

    return Image.alpha_composite(base_image, template)