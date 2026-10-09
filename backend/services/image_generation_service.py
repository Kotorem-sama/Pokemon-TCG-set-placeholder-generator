from io import BytesIO
from logging import getLogger
from os.path import isfile
from pathlib import Path

from database.db_operations import Card, Card_operations, Set_operations
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from services.name_service import sanitize_filename


class ImageGeneration:
    def __init__(
        self, card_operations: Card_operations, set_operations: Set_operations
    ) -> None:
        self.logger = getLogger(__name__)
        self.card_operations = card_operations
        self.set_operations = set_operations

    def retrieve_extension(self, image_tuple: tuple[bytes, str]) -> str:
        """
        Determine file extension based on MIME type.

        Args:
            image_tuple: A tuple containing (image_bytes, mime_type_string)

        Returns:
            str: File extension (e.g., ".jpg", ".png") or ".fail" if MIME type is not recognized
        """
        try:
            match image_tuple[1].lower():
                case "image/jpeg":
                    return ".jpg"
                case "image/png":
                    return ".png"
                case "image/gif":
                    return ".gif"
                case "image/webp":
                    return ".webp"
                case "image/bmp":
                    return ".bmp"
                case "image/tiff":
                    return ".tiff"
                case "image/svg+xml":
                    return ".svg"
                case "image/x-icon":
                    return ".ico"
                case "image/vnd.microsoft.icon":
                    return ".ico"
                case _:
                    self.logger.warning(f"Unrecognized MIME type: {image_tuple[1]}")
                    return ".fail"
        except (IndexError, TypeError) as e:
            self.logger.error(f"Error retrieving extension from image tuple: {e}")
            return ".fail"

    def save_image(
        self, extension: str, file_name: str, set_name: str, image: Image.Image
    ):
        """
        Save an image to the generated data directory with directory structure based on set name.

        Creates the directory structure if it doesn't exist. Skips saving if file already exists.

        Args:
            extension: File extension (e.g., ".jpg", ".png")
            file_name: Name of the file (will be sanitized)
            set_name: Name of the Pokémon set (will be sanitized)
            image: PIL Image object to save

        Raises:
            OSError: If directory creation or image saving fails
        """
        try:
            set_name = sanitize_filename(set_name)
            file_name = sanitize_filename(file_name)
            SET_DIR: Path = (
                Path(__file__).resolve().parent.parent / "data" / "generated" / set_name
            )
            SET_DIR.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Set directory ensured: {SET_DIR}")

            image_directory = SET_DIR / f"{file_name}{extension}"
            if isfile(image_directory):
                self.logger.info(f"Image already exists, skipping: {image_directory}")
                return

            image.save(image_directory)
            self.logger.info(f"Image saved successfully: {image_directory}")
        except OSError as e:
            self.logger.error(
                f"OS error while saving image '{file_name}' for set '{set_name}': {e}"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error while saving image: {e}")

    def image_processor(
        self,
        current_image: tuple[bytes, str],
        current_card: Card,
        set_name: str,
        variant: str,
    ):
        """
        Process a card image by converting it to grayscale and combining with template overlay.

        Args:
            current_image: Tuple containing (image_bytes, mime_type)
            current_card: Card object with card metadata
            set_name: Name of the Pokémon set
            variant: Card variant (e.g., "Holo", "Reverse Holo")
        """
        try:
            extension = self.retrieve_extension(current_image)
            self.logger.info(
                f"Processing image for card: {current_card.name} ({variant})"
            )

            with Image.open(BytesIO(current_image[0])) as im:
                im = self.combine_with_template(im, variant, current_card.rarity)

                grayscale_image = im.convert("L")
                self.save_image(
                    extension,
                    f"{current_card.number} - {current_card.name} ({variant})",
                    set_name,
                    grayscale_image,
                )
        except Exception as e:
            self.logger.error(
                f"Error processing image for card '{current_card.name}': {e}"
            )

    def get_template(self, variant: str):
        """
        Load a template image and adjust its alpha channel opacity.

        Args:
            variant: Template variant name (e.g., "Holo", "Reverse Holo")

        Returns:
            PIL Image: Template image with adjusted opacity, or None if template not found
        """
        try:
            template_path = (
                Path(__file__).resolve().parent.parent
                / "data"
                / "templates"
                / f"{variant}.png"
            )

            if not template_path.is_file():
                self.logger.warning(f"Template file not found: {template_path}")
                return None

            template = Image.open(template_path).convert("RGBA")

            alpha_channel = template.getchannel("A")
            opacity = 100 / 255
            alpha_channel = ImageEnhance.Brightness(alpha_channel).enhance(opacity)

            template.putalpha(alpha_channel)
            self.logger.info(f"Template loaded successfully: {variant}")

            return template
        except Exception as e:
            self.logger.error(f"Error loading template '{variant}': {e}")
            return None

    def combine_with_template(
        self, im: Image.Image, variant: str, card_rarity: str | None
    ):
        """
        Combine a card image with a template overlay if applicable.

        Checks if the card rarity is in the special rarities list. If the template file
        exists and rarity is not special, the template is composited over the base image.

        Args:
            im: Base card image (PIL Image)
            variant: Template variant to use
            card_rarity: Rarity of the card (may be None)

        Returns:
            PIL Image: Combined image or original image if no template is applied
        """
        try:
            template_path = (
                Path(__file__).resolve().parent.parent / "data" / "templates"
            )
            rarities = [
                "Double Rare",
                "Illustration Rare",
                "Mega Attack Rare",
                "Mega Hyper Rare",
                "Promo",
                "RBG Rare",
                "Special Illustration Rare",
                "Ultra Rare",
                "Futuristic Rare",
            ]

            template_file = template_path / f"{variant}.png"
            base_image = im.convert("RGBA")

            if not template_file.is_file() or card_rarity in rarities:
                self.logger.info(
                    f"No template applied for {variant} (rarity: {card_rarity})"
                )
                return base_image

            template = self.get_template(variant)

            if template is None:
                self.logger.warning(
                    f"Template is None, returning base image for variant: {variant}"
                )
                return base_image

            template = template.convert("RGBA")

            target_size: tuple[int, int] = (base_image.width, base_image.height)

            if template.size != target_size:
                self.logger.info(
                    f"Template resized from {template.size} to {target_size}"
                )
                template = ImageOps.fit(template, base_image.size)

            result = Image.alpha_composite(base_image, template)
            self.logger.info(f"Template combined successfully for variant: {variant}")
            return result
        except Exception as e:
            self.logger.error(f"Error combining template for variant '{variant}': {e}")
            return im.convert("RGBA")

    def generate_placeholder(
        self,
        current_card: Card,
        variant: str,
        set_name: str,
        width: int = 744,
        height: int = 1039,
    ):
        """
        Generate a placeholder card image with card name and variant text.

        Creates a light gray rectangular card with rounded corners and centered text.
        Text is wrapped across multiple lines if it exceeds the maximum width.

        Args:
            current_card: Card object containing name and number
            variant: Card variant (e.g., "Holo", "Reverse Holo")
            set_name: Name of the Pokémon set
            width: Image width in pixels (default: 744)
            height: Image height in pixels (default: 1039)
        """
        try:
            self.logger.info(
                f"Generating placeholder for {current_card.name} ({variant})"
            )

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
            font_options = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                "/Library/Fonts/Arial.ttf",  # macOS
            ]

            font = None
            for font_path in font_options:
                if Path(font_path).is_file():
                    try:
                        font = ImageFont.truetype(font_path, max(16, width // 16))
                        break
                    except Exception:
                        continue

            if font is None:
                self.logger.warning("No TrueType font found, using default font")
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

                    # If even a single word is too long, force it onto a new line anyway
                    if (
                        draw.textbbox((0, 0), current_line, font=font)[2]
                        > max_text_width
                    ):
                        lines.append(current_line)
                        current_line = ""

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
            self.save_image(
                ".png",
                f"{current_card.number} - {current_card.name} ({variant})",
                set_name,
                image,
            )
            self.logger.info(f"Placeholder saved for {current_card.name} ({variant})")
        except Exception as e:
            self.logger.error(
                f"Error generating placeholder for card '{current_card.name}': {e}"
            )

    def generate_images_for_card(self, current_card: Card, set_name: str):
        """
        Generate images for all variants of a card.

        Retrieves all variants and the card's image from the database. If no image exists,
        generates placeholder images for each variant. Otherwise, processes the actual image.

        Args:
            current_card: Card object to generate images for
            set_name: Name of the Pokémon set
        """
        try:
            self.logger.info(f"Generating images for card: {current_card.name}")

            card_variants = self.card_operations.get_variants(current_card.id)
            card_image = self.card_operations.get_image(current_card.id)

            if card_image is None:
                self.logger.info(
                    f"No image found for {current_card.name}, generating placeholders"
                )
                for variant in card_variants:
                    self.generate_placeholder(current_card, variant, set_name, 287, 400)
            else:
                self.logger.info(f"Processing actual image for {current_card.name}")
                for variant in card_variants:
                    self.image_processor(card_image, current_card, set_name, variant)
        except Exception as e:
            self.logger.error(
                f"Error generating images for card '{current_card.name}': {e}"
            )

    def generate_images_for_set(self, set_id: int) -> bool:
        """
        Generate images for all cards in a Pokémon set.

        Retrieves all cards for the set and generates images for each card across all variants.

        Args:
            set_id: ID of the Pokémon set
        """
        try:
            self.logger.info(f"Starting image generation for set ID: {set_id}")

            current_set = self.set_operations.get_set_by_id(set_id)

            if current_set is None:
                self.logger.error(f"Set with ID {set_id} not found.")
                return False

            cards_in_set = self.card_operations.get_cards_by_set(set_id)
            self.logger.info(
                f"Found {len(cards_in_set)} cards in set '{current_set.name}'"
            )

            for card in cards_in_set:
                self.generate_images_for_card(card, current_set.name)

            self.logger.info(f"Completed image generation for set: {current_set.name}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating images for set ID {set_id}: {e}")
            return False
