from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from services.image_utils import ImageUtils

from PIL import Image


class DocumentGeneration:
    """
    Generates PDF documents containing card placeholder images in a grid layout.

    This class handles the layout calculations and PDF generation for Pokémon card
    placeholders, arranging them in a configurable grid (default 3x3) with proper
    spacing and margins.
    """

    COLUMNS = 3
    ROWS = 3

    PAGE_WIDTH, PAGE_HEIGHT = A4

    MARGIN_X = 24
    MARGIN_Y = 24

    GAP_X = 8
    GAP_Y = 8

    LABEL_HEIGHT = 12

    CARD_ASPECT_RATIO = 287 / 400

    def __init__(self) -> None:
        """Initialize DocumentGeneration."""
        self.logger = getLogger(__name__)

    def _filter_valid_images(self, image_paths: list[str]) -> list[str]:
        """
        Filter image paths to only include files that exist.

        Args:
            image_paths: List of file paths to validate

        Returns:
            list[str]: Filtered list of valid image paths
        """
        valid_images: list[str] = []
        for path in image_paths:
            image_path = Path(path)
            if image_path.is_file():
                try:
                    with Image.open(image_path) as img:
                        img.verify()
                        valid_images.append(path)
                except (IOError, SyntaxError):
                    self.logger.warning("Image file not found, skipping: %s", image_path)
            else:
                self.logger.warning("Image file not found, skipping: %s", image_path)

        return valid_images

    def generate_pdf(self, image_paths: list[str], set_name: str) -> None:
        """
        Generate a PDF document containing card images arranged in a grid layout.

        Images that are missing or cannot be read are skipped with a log entry.
        No gaps are left in the grid for skipped images.

        Args:
            image_paths: List of file paths to card images to include in the PDF

        Raises:
            ValueError: If image_paths is empty or contains no valid images
            OSError: If the output directory cannot be created or written
        """
        if not image_paths:
            self.logger.warning("image_paths list cannot be empty")
            return

        # Filter to only valid images, no gaps in grid
        valid_images = self._filter_valid_images(image_paths)

        if not valid_images:
            self.logger.warning("No valid images found in image_paths")
            return

        self.logger.info("Starting PDF generation with %d images", len(valid_images))

        output_path = Path(__file__).parent.parent / "data" / "generated"
        output_path.mkdir(parents=True, exist_ok=True)

        # Name the PDF after the first image's parent directory
        pdf_name = f"{Path(valid_images[0]).parent.name}.pdf"
        final_path = output_path / pdf_name
        self.logger.info("PDF output path: %s", final_path)

        # Write to temp file first, then rename on success
        with NamedTemporaryFile(
            suffix=".pdf", dir=output_path, delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            pdf = Canvas(temp_path, pagesize=(self.PAGE_WIDTH, self.PAGE_HEIGHT))

            # Card width is constrained by either horizontal or vertical space
            card_width = min(
                (self.PAGE_WIDTH - 2 * self.MARGIN_X - (self.COLUMNS - 1) * self.GAP_X)
                / self.COLUMNS,
                (
                    self.PAGE_HEIGHT
                    - 2 * self.MARGIN_Y
                    - (self.ROWS - 1) * self.GAP_Y
                    - self.ROWS * self.LABEL_HEIGHT
                )
                / self.ROWS
                * self.CARD_ASPECT_RATIO,
            )
            card_height = card_width / self.CARD_ASPECT_RATIO

            for index, path in enumerate(valid_images):
                slot = index % (self.COLUMNS * self.ROWS)

                if index > 0 and slot == 0:
                    pdf.showPage()

                column = slot % self.COLUMNS
                row = slot // self.COLUMNS

                x = self.MARGIN_X + column * (card_width + self.GAP_X)
                y = (
                    self.PAGE_HEIGHT
                    - self.MARGIN_Y
                    - card_height
                    - self.LABEL_HEIGHT
                    - row * (card_height + self.LABEL_HEIGHT + self.GAP_Y)
                )

                image_path = Path(path)

                try:
                    pdf.drawImage(  # pyright: ignore[reportUnknownMemberType]
                        ImageReader(image_path),
                        x,
                        y,
                        width=card_width,
                        height=card_height,
                        preserveAspectRatio=True,
                        anchor="c",
                    )
                except (OSError, ValueError):
                    self.logger.exception(
                        "Could not draw image at index %d (%s), skipping",
                        index,
                        path,
                    )
                    continue

            pdf.save()

            # Atomic rename: only happens if save succeeded
            final_path.unlink(missing_ok=True)
            Path(temp_path).rename(final_path)

            self.logger.info("PDF generated successfully: %s", final_path)
            ImageUtils().remove_set_images(set_name)
        except OSError:
            # Clean up temp file on failure
            try:
                Path(temp_path).unlink()
            except OSError:
                self.logger.warning("Could not delete temp file: %s", temp_path)
            self.logger.exception("Failed to generate PDF")
        except Exception:
            # Clean up temp file on any other error
            try:
                Path(temp_path).unlink()
            except OSError:
                self.logger.warning("Could not delete temp file: %s", temp_path)
            self.logger.exception("Unexpected error during PDF generation")
