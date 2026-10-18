from os import path
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from flask import jsonify, send_file, Flask

from backend.core.startup import get_database, startup
from backend.services.backend_service import Backend

app = FastAPI(
    title="Pokémon TCG Set Lister",
    description="Generate printable Pokémon TCG set lists.",
    version="1.0.0",
)
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
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


@app.get("/set/{set_name}")
def get_sets_by_name(set_name: str):
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        set_info = backend_service.get_sets_by_name(set_name)
    finally:
        backend_service.database.database.context.close()

    return set_info


@app.get("/sets/years")
def get_years():
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        years = backend_service.get_years()
    finally:
        backend_service.database.database.context.close()

    return years if years else []


@app.get("/sets/{year}")
def get_sets_by_year(year: int):
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        sets_in_year = backend_service.get_sets_in_year(year)
    finally:
        backend_service.database.database.context.close()

    return sets_in_year if sets_in_year else []


@app.get("/sets/{set_id}/variants")
async def get_variants_in_set(set_id: int):
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        set_variants = await backend_service.get_variants_in_set(set_id)
    finally:
        backend_service.database.database.context.close()

    return set_variants if set_variants else []


@app.get("/sets/{set_id}/rarities")
async def get_rarities_in_set(set_id: int):
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        set_rarities = await backend_service.get_rarities_in_set(set_id)
    finally:
        backend_service.database.database.context.close()

    return set_rarities if set_rarities else []


@app.post("/sets/{set_id}/sync")
async def sync_set(set_id: int):
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        result = await backend_service.sync_service.sync_set(set_id)
    finally:
        backend_service.database.database.context.close()

    return {"success": result}


@app.post("/sets/sync_all")
async def sync_all_sets():
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        result = await backend_service.sync_service.sync_sets()
    finally:
        backend_service.database.database.context.close()

    return {"success": result}


@app.post("/sets/{set_id}/document")
async def generate_document(set_id: int, options: dict[str, list[str]]):
    backend_service = Backend(get_database("pokemon_cards"))

    try:
        output_path = await backend_service.get_document(
            set_id, options["rarities"], options["variants"]
        )
        if not output_path or not path.exists(output_path):
            return jsonify({"error": "Document was not generated"}), 500

        return send_file(
            output_path,
            as_attachment=True,
            download_name="pokemon-set-placeholders.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    finally:
        backend_service.database.database.context.close()

