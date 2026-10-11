from asyncio import run
from logging import getLogger
from pathlib import Path
from sys import exit

from core.startup import startup
from pytest import main as testmain


async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    db = startup()
    if db is None:
        exit()

    await tests()

    db.db_context.close()


async def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = getLogger(__name__)
    logger.info("Executing unit tests...")

    BACKEND_DIR = Path(__file__).resolve().parent

    test_result = testmain([str(BACKEND_DIR / "tests")])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        exit(1)

    logger.info("Tests have successfully been conducted!")
