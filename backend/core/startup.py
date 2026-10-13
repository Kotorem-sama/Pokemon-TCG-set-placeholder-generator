from logging import WARNING, FileHandler, StreamHandler, basicConfig, getLogger
from pathlib import Path
from sys import exit as exit_program

from pytest import main

from backend.database.db_setup import DatabaseSetup


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


def setup_database() -> DatabaseSetup:
    """Create and validate the application's SQLite database."""
    logger = getLogger(__name__)
    database_dir = Path(__file__).resolve().parent.parent / "database"
    database_path = database_dir / "pokemon_cards.db"

    logger.info(
        f"Setting up the database. Database directory is set to {database_dir}."
    )
    database_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseSetup(str(database_path))
    db.initialise_db()
    logger.info("Database initialisation complete.")

    if not db.integrity_check():
        logger.error("Database integrity check failed.")
        db.db_context.close()
        database_path.unlink(missing_ok=True)
        exit_program(1)

    logger.info("Initialised the database succesfully!")
    return db


def get_database() -> DatabaseSetup:
    database_path = (
        Path(__file__).resolve().parent.parent / "database" / "pokemon_cards.db"
    )
    return DatabaseSetup(str(database_path))


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
