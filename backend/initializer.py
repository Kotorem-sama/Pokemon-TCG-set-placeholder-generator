from pathlib import Path
from database.db_setup import DatabaseSetup as database
import subprocess
import sys

def startup() -> str:
    BACKEND_DIR = Path(__file__).resolve().parent
    DATABASE_DIR = BACKEND_DIR / "database"
    DATABASE_PATH = DATABASE_DIR / "pokemon_cards.db"

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    requirements_file = BACKEND_DIR / "requirements.txt"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file)
        ],
        check=True
    )

    if not DATABASE_PATH.exists():
        db = database(str(DATABASE_PATH))
        db_context = db.initialise_db(db.connect_db())
        db_context.close()

    return str(DATABASE_PATH)