from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from backend.core.startup import startup, get_database
from backend.services.backend_service import Backend

app = FastAPI(
    title="Pokémon TCG Set Lister",
    description="Generate printable Pokémon TCG set lists.",
    version="1.0.0",
)
startup(unit_tests=False)


@app.get("/favicon.ico")
def get_favicon():
    BACKEND_DIR: Path = Path(__file__).resolve().parent
    favicon_dir = BACKEND_DIR / "data" / "website" / "favicon.ico"
    return FileResponse(favicon_dir)


@app.get("/")
def home():
    return {"message": "Pokémon TCG Set Lister backend is running."}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/sets/years")
async def get_years():
    db = get_database()
    backend_service = Backend(db.db_context)

    try:
        years = backend_service.get_years()
    finally:
        db.db_context.close()

    return years


@app.get("/sets/{year}")
def get_sets_by_year(year: int):
    db = get_database()
    backend_service = Backend(db.db_context)

    try:
        sets_in_year = backend_service.get_sets_in_year(year)
    finally:
        db.db_context.close()

    return sets_in_year


@app.get("/sets/{set_id}/variants")
def get_variants_in_set(set_id: int):
    db = get_database()
    backend_service = Backend(db.db_context)

    try:
        set_variants = backend_service.get_variants_in_set(set_id)
    finally:
        db.db_context.close()

    return set_variants


@app.get("/sets/{set_id}/rarities")
def get_rarities_in_set(set_id: int):
    db = get_database()
    backend_service = Backend(db.db_context)

    try:
        set_rarities = backend_service.get_rarities_in_set(set_id)
    finally:
        db.db_context.close()

    return set_rarities
