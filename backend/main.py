import asyncio
import logging
import sys

import pytest
from database.db_operations import Card_operations
from database.db_setup import DatabaseSetup as database
from initializer import startup
from services.image_generation import generate_images_for_set
from services.sync_service import SyncService


async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    database_path = startup()
    if database_path is None:
        sys.exit()

    await tests()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    Card_operations().reset_set_cards(db_context, 5500216)
    await SyncService().sync_set(db_context, 5500216)

    generate_images_for_set(db_context, 5500216)

    # await SyncService().sync_sets(db_context)

    db_context.close()


async def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = logging.getLogger(__name__)
    logger.info("Executing unit tests...")

    test_result = pytest.main(["tests"])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        return

    logger.info("Tests have successfully been conducted!")


if __name__ == "__main__":
    asyncio.run(main())
