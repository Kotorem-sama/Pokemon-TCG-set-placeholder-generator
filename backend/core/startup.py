from logging import WARNING, FileHandler, StreamHandler, basicConfig, getLogger
from pathlib import Path
from sys import exit as exit_program

from pytest import main

from backend.database.db_setup import Database


def startup(unit_tests: bool = True):
    """Set up logging, dependencies and the database before starting the application."""
    setup_logging()
    setup_database()

    if unit_tests:
        tests()


def setup_logging():
    """Configure application logging for both the console and log file."""
    basicConfig(
        level=WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            FileHandler("pokemon_tcg_sync.log"),
            StreamHandler(),
        ],
    )


def setup_database():
    """Create and validate the application's SQLite database."""
    logger = getLogger(__name__)

    db = Database("pokemon_cards")  # The database name without the .db extension
    db.initialise_db()
    logger.info("Database initialisation complete.")

    db.integrity_check()

    logger.info("Initialised the database successfully!")
    db.close_db()


def get_database(file_name: str) -> Database:
    db = Database(file_name)
    db.initialise_db()
    return db


def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = getLogger(__name__)
    logger.info("Executing unit tests...")

    BACKEND_DIR = Path(__file__).resolve().parent.parent

    test_result = main([str(BACKEND_DIR / "tests")])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        exit_program(1)

    logger.info("Tests have successfully been conducted!")
