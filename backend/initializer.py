import logging
import subprocess
import sys
from logging import Logger as LoggerModel
from pathlib import Path

from database.db_setup import DatabaseSetup as database


def startup() -> str | None:
    """Set up logging, dependencies and the database before starting the application."""
    logger = setup_logging()

    if not install_dependencies(logger):
        return None

    return setup_database(logger)


def setup_logging() -> LoggerModel:
    """Configure application logging for both the console and log file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("pokemon_tcg_sync.log"),
            logging.StreamHandler(),  # Console output
        ],
    )
    return logging.getLogger(__name__)


def install_dependencies(logger: LoggerModel) -> bool:
    """Install the project's dependencies from requirements.txt."""
    BACKEND_DIR: Path = Path(__file__).resolve().parent
    logger.info("Installing dependencies...")

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(BACKEND_DIR / "requirements.txt"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Installed dependencies succesfully.")
        return True

    except subprocess.CalledProcessError as error:
        logger.error(f"Failed to install dependencies: {error.stderr}")
        return False


def setup_database(logger: LoggerModel) -> str | None:
    """Create and validate the application's SQLite database."""
    BACKEND_DIR: Path = Path(__file__).resolve().parent
    DATABASE_DIR = BACKEND_DIR / "database"
    DATABASE_PATH = DATABASE_DIR / "pokemon_cards.db"

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Setting up the database.")

    if not DATABASE_PATH.exists():
        db = database(str(DATABASE_PATH))
        db_context = db.initialise_db(db.connect_db())
        db_context.close()

    db = database(str(DATABASE_PATH))
    if not db.integrity_check():
        logger.error("Failed to initialise database. Please try again later.")
        Path.unlink(DATABASE_PATH)

        return None

    logger.info("Initialised the database succesfully!")

    return str(DATABASE_PATH)
