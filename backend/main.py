import asyncio
import logging
import sys

import pytest

from database.db_setup import DatabaseSetup as database
from initializer import startup

from services.image_generation import generate_images_for_card

from database.db_operations import Card_operations, Set_operations


async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    database_path = startup()
    if database_path is None:
        sys.exit()

    # await tests()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    current_set = Set_operations().get_set_by_name(db_context, "Ascended Heroes")
    current_card = Card_operations().get_card_by_id(db_context, 7034)
    if current_set is not None and current_card is not None:
        generate_images_for_card(db_context, current_card, current_set.name)

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
