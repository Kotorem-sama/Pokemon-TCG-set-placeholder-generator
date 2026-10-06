from pathlib import Path
from database.db_setup import DatabaseSetup as database
import subprocess
import sys

def startup() -> str | None:
    BACKEND_DIR = Path(__file__).resolve().parent
    DATABASE_DIR = BACKEND_DIR / "database"
    DATABASE_PATH = DATABASE_DIR / "pokemon_cards.db"

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    requirements_file = BACKEND_DIR / "requirements.txt"

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements_file)
            ],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as error:
        print("Failed to install dependencies:")
        print(error.stderr)
        return None

    if not DATABASE_PATH.exists():
        db = database(str(DATABASE_PATH))
        db_context = db.initialise_db(db.connect_db())
        db_context.close()
    
    db = database(str(DATABASE_PATH))
    if not db.integrity_check():
        print("Failed to initialise database. Please try again later.")
        Path.unlink(DATABASE_PATH)

        return None

    return str(DATABASE_PATH)