from io import BytesIO
from os.path import isfile
from pathlib import Path
from sqlite3 import Connection

from database.db_operations import Card, Card_operations, Set_operations
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


def retreive_extension(image_tuple: tuple[bytes, str]) -> str:
    match image_tuple[1].lower():
        case "image/jpeg":
            return ".jpg"
        case _:
            return ".fail"


def sanitize_filename(filename: str) -> str:
    invalid_characters = ["<", ">", ":", '"', "\\", "|", "?", "*"]

    for character in invalid_characters:
        filename = filename.replace(character, "")

    return filename.replace("/", "-")


def save_image(extension: str, file_name: str, set_name: str, image: Image.Image):
    set_name = sanitize_filename(set_name)
    file_name = sanitize_filename(file_name)
    SET_DIR: Path = (
        Path(__file__).resolve().parent.parent / "data" / "generated" / set_name
    )
    SET_DIR.mkdir(parents=True, exist_ok=True)

    image_directory = SET_DIR / f"{file_name}{extension}"
    if isfile(image_directory):
        return

    image.save(image_directory)


def image_processor(
    current_image: tuple[bytes, str], current_card: Card, set_name: str, variant: str
):
    extension = retreive_extension(current_image)

    with Image.open(BytesIO(current_image[0])) as im:
        im = combine_with_template(im, variant, current_card.rarity)

        grayscale_image = im.convert("L")
        save_image(
            extension,
            f"{current_card.number} - {current_card.name} ({variant})",
            set_name,
            grayscale_image,
        )


def get_template(variant: str):
    template_path = (
        Path(__file__).resolve().parent.parent / "data" / "templates" / f"{variant}.png"
    )
    template = Image.open(template_path).convert("RGBA")

    alpha_channel = template.getchannel("A")
    opacity = 100 / 255
    alpha_channel = ImageEnhance.Brightness(alpha_channel).enhance(opacity)

    template.putalpha(alpha_channel)

    return template


def combine_with_template(im: Image.Image, variant: str, card_rarity: str | None):
    template_path = Path(__file__).resolve().parent.parent / "data" / "templates"
    rarities = [
        "Double Rare",
        "Illustration Rare",
        "Mega Attack Rare",
        "Mega Hyper Rare",
        "Promo",
        "RGB Rare",
        "Special Illustration Rare",
        "Ultra Rare",
        "Futuristic Rare",
        "RBG Rare",
    ]

    template_file = template_path / f"{variant}.png"
    base_image = im.convert("RGBA")

    if not template_file.is_file() or card_rarity in rarities:
        return base_image

    template = get_template(variant).convert("RGBA")

    target_size: tuple[int, int] = (base_image.width, base_image.height)

    if template.size != target_size:
        template = ImageOps.fit(template, base_image.size)

    return Image.alpha_composite(base_image, template)


def generate_placeholder(
    current_card: Card,
    variant: str,
    set_name: str,
    width: int = 744,
    height: int = 1039,
):
    """Generate a placeholder card image and return it as PNG bytes."""

    image = Image.new("RGB", (width, height), color="#E0E0E0")
    draw = ImageDraw.Draw(image)

    # Card border
    border_width = max(2, width // 100)
    corner_radius = max(10, width // 12)

    draw.rounded_rectangle(
        (
            border_width,
            border_width,
            width - border_width - 1,
            height - border_width - 1,
        ),
        radius=corner_radius,
        outline="#777777",
        width=border_width,
    )
    # Centered placeholder text
    try:
        font = ImageFont.truetype("arial.ttf", max(16, width // 16))
    except OSError:
        font = ImageFont.load_default()

    text = f"{current_card.name} ({variant})"
    max_text_width = width - 40

    # Wrap long names across multiple lines
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        candidate = f"{current_line} {word}".strip()

        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_text_width:
            current_line = candidate
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    line_heights = [
        draw.textbbox((0, 0), line, font=font)[3]
        - draw.textbbox((0, 0), line, font=font)[1]
        for line in lines
    ]

    total_height = sum(line_heights) + (len(lines) - 1) * 8
    y = (height - total_height) // 2

    for line, line_height in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2

        draw.text((x, y), line, fill="#555555", font=font)
        y += line_height + 8

    # Return PNG bytes instead of saving a file
    save_image(".png", f"{current_card.number} - {variant}", set_name, image)


def generate_images_for_card(db_context: Connection, current_card: Card, set_name: str):
    card_variants = Card_operations().get_variants(db_context, current_card.id)
    card_image = Card_operations().get_image(db_context, current_card.id)

    if card_image is None:
        for variant in card_variants:
            generate_placeholder(current_card, variant, set_name, 287, 400)
    else:
        for variant in card_variants:
            image_processor(card_image, current_card, set_name, variant)


def generate_images_for_set(db_context: Connection, set_id: int):
    current_set = Set_operations().get_set_by_id(db_context, set_id)

    if current_set is None:
        print(f"Set with ID {set_id} not found.")
        return

    cards_in_set = Card_operations().get_cards_by_set(db_context, set_id)

    for card in cards_in_set:
        generate_images_for_card(db_context, card, current_set.name)
