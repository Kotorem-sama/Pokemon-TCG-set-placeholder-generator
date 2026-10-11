from logging import WARNING, FileHandler, Logger, StreamHandler, basicConfig, getLogger
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import executable

from database.db_setup import DatabaseSetup as Database


def startup() -> Database | None:
    """Set up logging, dependencies and the database before starting the application."""
    logger = setup_logging()

    if not install_dependencies(logger):
        return None

    return setup_database(logger)


def setup_logging() -> Logger:
    """Configure application logging for both the console and log file."""
    basicConfig(
        level=WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            FileHandler("pokemon_tcg_sync.log"),
            StreamHandler(),  # Console output
        ],
    )
    return getLogger(__name__)


def install_dependencies(logger: Logger) -> bool:
    """Install the project's dependencies from requirements.txt."""
    BACKEND_DIR: Path = Path(__file__).resolve().parent
    logger.info("Installing dependencies...")

    try:
        run(
            [
                executable,
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

    except CalledProcessError as error:
        logger.error(f"Failed to install dependencies: {error.stderr}")
        return False


def setup_database(logger: Logger) -> Database | None:
    """Create and validate the application's SQLite database."""
    BACKEND_DIR: Path = Path(__file__).resolve().parent
    DATABASE_DIR = BACKEND_DIR / "database"
    DATABASE_PATH = DATABASE_DIR / "pokemon_cards.db"

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Setting up the database.")

    db = Database(str(DATABASE_PATH))
    db.initialise_db()
    if not db.integrity_check():
        logger.error("Failed to initialise database. Please try again later.")
        Path.unlink(DATABASE_PATH)

        return None

    logger.info("Initialised the database succesfully!")
    return db
