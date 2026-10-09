from asyncio import run
from logging import getLogger
from pathlib import Path
from sys import exit

from database.db_setup import DatabaseSetup as database
from initializer import startup
from pytest import main as testmain
from placeholder_pdf_creator import SetToPDF


async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    database_path = startup()
    if database_path is None:
        exit()

    await tests()

    db_context = database(database_path).initialise_db()

    await SetToPDF(db_context).get_document("ME: 30th Celebration")

    db_context.close()


async def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = getLogger(__name__)
    logger.info("Executing unit tests...")

    BACKEND_DIR = Path(__file__).resolve().parent

    test_result = testmain([str(BACKEND_DIR / "tests")])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        return

    logger.info("Tests have successfully been conducted!")


if __name__ == "__main__":
    run(main())
