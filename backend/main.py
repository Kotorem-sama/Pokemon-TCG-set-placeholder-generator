import asyncio
import logging
import sys
from pathlib import Path

import pytest
from database.db_setup import DatabaseSetup as database
from initializer import startup
from services.document_generation_service import DocumentGeneration
from services.image_utils import ImageUtils
from database.db_operations import Set_operations


async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    database_path = startup()
    if database_path is None:
        sys.exit()

    await tests()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    current_set = Set_operations().get_set_by_name(db_context, "30th")
    if current_set is not None:
        DocumentGeneration().generate_pdf(ImageUtils.get_images_in_set_folder(current_set.name))

    db_context.close()


async def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = logging.getLogger(__name__)
    logger.info("Executing unit tests...")

    BACKEND_DIR = Path(__file__).resolve().parent

    test_result = pytest.main([str(BACKEND_DIR / "tests")])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        return

    logger.info("Tests have successfully been conducted!")


if __name__ == "__main__":
    asyncio.run(main())
