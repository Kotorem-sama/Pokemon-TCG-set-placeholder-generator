import asyncio
import logging
import sys
from pathlib import Path

import pytest
from database.db_setup import DatabaseSetup as database
from initializer import startup


async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    database_path = startup()
    if database_path is None:
        sys.exit()

    await tests()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    db_context.close()


async def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = logging.getLogger(__name__)
    logger.info("Executing unit tests...")

    BACKEND_DIR = Path(__file__).resolve().parent
    TESTS_DIR = BACKEND_DIR / "tests"

    test_result = pytest.main([str(TESTS_DIR)])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        return

    logger.info("Tests have successfully been conducted!")


if __name__ == "__main__":
    asyncio.run(main())
