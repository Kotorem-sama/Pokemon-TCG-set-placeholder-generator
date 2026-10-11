from fastapi import FastAPI
from backend.services.backend_service import Backend
from logging import getLogger
from pathlib import Path
from sys import exit

from backend.core.startup import startup
from pytest import main as testmain

app = FastAPI(
    title="Pokémon TCG Set Lister",
    description="Generate printable Pokémon TCG set lists.",
    version="1.0.0",
)

def tests():
    """Run the project's unit tests and stop the application on failure."""

    logger = getLogger(__name__)
    logger.info("Executing unit tests...")

    BACKEND_DIR = Path(__file__).resolve().parent

    test_result = testmain([str(BACKEND_DIR / "tests")])

    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        exit(1)

    logger.info("Tests have successfully been conducted!")

db = startup()
if db is None:
    exit()

tests()

backend_service = Backend(db.db_context)

@app.get("/")
def home():
    return {"message": "Pokémon TCG Set Lister backend is running."}


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/sets/years")
async def get_years():
    return await backend_service.get_years()