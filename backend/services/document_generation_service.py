import logging
from pathlib import Path

from database.db_operations import Card_operations, Set_operations
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader


class DocumentGeneration:
    """
    Generates PDF documents containing card placeholder images in a grid layout.
    
    This class handles the layout calculations and PDF generation for Pokémon card
    placeholders, arranging them in a configurable grid (default 3x3) with proper
    spacing and margins.
    """
    logger = logging.getLogger(__name__)

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
        """Initialize DocumentGeneration with database operations."""
        try:
            self.card_operations = Card_operations()
            self.set_operations = Set_operations()
            self.logger.info("DocumentGeneration initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing DocumentGeneration: {e}")
            raise

    def generate_pdf(self, image_paths: list[str]) -> None:
        """
        Generate a PDF document containing card images arranged in a grid layout.
        
        Creates a multi-page PDF with images arranged in rows and columns. Each page
        contains a 3x3 grid of cards. Images are scaled to fit the page while maintaining
        aspect ratio, with configurable margins and gaps between cards.
        
        Args:
            image_paths: List of file paths to card images to include in the PDF
            
        Raises:
            ValueError: If image_paths is empty
            FileNotFoundError: If any image file cannot be found
            OSError: If PDF file cannot be created or written
            Exception: If any unexpected error occurs during PDF generation
        """
        try:
            # Validate input
            if not image_paths:
                raise ValueError("image_paths list cannot be empty")
            
            self.logger.info(f"Starting PDF generation with {len(image_paths)} images")
            
            # Setup output directory
            output_path = Path(__file__).parent.parent / "data" / "generated"
            output_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory ensured: {output_path}")
            
            # Generate output file path from the first image's parent directory name
            file_path = output_path / f"{Path(image_paths[0]).parent.name}.pdf"
            self.logger.info(f"PDF output path: {file_path}")

            print(str())

            # Initialize PDF canvas
            pdf = Canvas(str(file_path), pagesize=(self.PAGE_WIDTH, self.PAGE_HEIGHT))
            self.logger.info(f"PDF canvas created with page size: {self.PAGE_WIDTH}x{self.PAGE_HEIGHT}")

            # Calculate card dimensions based on page size and grid layout
            # The card width is constrained by either the horizontal space or vertical space
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
            self.logger.info(f"Calculated card dimensions: {card_width}x{card_height}")

            # Iterate through images and place them in the grid
            for index, path in enumerate(image_paths):
                try:
                    # Determine grid position
                    slot = index % (self.COLUMNS * self.ROWS)

                    # Create new page if current page is full
                    if index > 0 and slot == 0:
                        pdf.showPage()
                        self.logger.info(f"New page created for image {index + 1}")

                    column = slot % self.COLUMNS
                    row = slot // self.COLUMNS

                    # Calculate position based on grid layout
                    x = self.MARGIN_X + column * (card_width + self.GAP_X)
                    y = (
                        self.PAGE_HEIGHT
                        - self.MARGIN_Y
                        - card_height
                        - self.LABEL_HEIGHT
                        - row * (card_height + self.LABEL_HEIGHT + self.GAP_Y)
                    )

                    image_path = Path(path)
                    
                    # Validate image file exists
                    if not image_path.is_file():
                        self.logger.warning(f"Image file not found, skipping: {image_path}")
                        continue

                    # Draw image on PDF
                    pdf.drawImage(  # pyright: ignore[reportUnknownMemberType]
                        ImageReader(image_path),
                        x,
                        y,
                        width=card_width,
                        height=card_height,
                        preserveAspectRatio=True,
                        anchor="c",
                    )
                    self.logger.info(f"Image {index + 1} placed at position ({x}, {y}): {image_path.name}")

                except FileNotFoundError as e:
                    self.logger.error(f"Image file not found at index {index}: {path} - {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing image at index {index} ({path}): {e}")
                    continue

            # Save the PDF
            try:
                pdf.save()
                self.logger.info(f"PDF generated successfully: {file_path}")
            except OSError as e:
                self.logger.error(f"Error saving PDF to {file_path}: {e}")
                raise
            except Exception as e:
                self.logger.error(f"Unexpected error while saving PDF: {e}")
                raise

        except ValueError as e:
            self.logger.error(f"Invalid input to generate_pdf: {e}")
            raise
        except FileNotFoundError as e:
            self.logger.error(f"File not found during PDF generation: {e}")
            raise
        except OSError as e:
            self.logger.error(f"OS error during PDF generation: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during PDF generation: {e}")
            raise