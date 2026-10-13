from logging import INFO, FileHandler, StreamHandler, basicConfig, getLogger
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import executable
from sys import exit as exit_program

basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        FileHandler("pokemon_tcg_sync.log"),
        StreamHandler(),
    ],
)

CURRENT_DIR: Path = Path(__file__).resolve().parent
logger = getLogger(__name__)
logger.info("Installing dependencies...")

try:
    run(
        [
            executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(CURRENT_DIR / "requirements.txt"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info("Installed dependencies succesfully.")

except CalledProcessError as error:
    logger.error(f"Failed to install dependencies: {error.stderr}")
    exit_program(1)
