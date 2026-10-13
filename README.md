# Pokémon TCG Set Placeholder Generator

This repository is a local Python utility that downloads Pokémon TCG set and card data from `tcgapi.dev`, stores it in SQLite, and generates placeholder card images plus a printable PDF sheet.

The project is intended to run on a developer machine, not as a hosted service.

## What it does

- Connects to the Pokémon TCG API at `https://api.tcgapi.dev`
- Loads API keys from `backend/.env`
- Creates the SQLite database if it does not exist
- Syncs set metadata and card data from the API
- Saves card metadata, image binaries, and variant records in SQLite
- Builds generated placeholder images for each card in a set
- Arranges those images into a PDF sheet in a 3x3 grid layout
- Cleans up the generated image directory after the final PDF is created
- Exposes set information (years, sets per year, variants, rarities) through a FastAPI backend

## Current application behavior

The entry point is the FastAPI app in `backend/app.py`.

When the app is imported (for example by `uvicorn`), it:

1. Configures logging
2. Creates and integrity-checks the SQLite database
3. Skips the unit tests (`startup(unit_tests=False)`). Run them separately, see [Tests](#tests).

Every request opens its own SQLite connection through `get_database()` and closes it when the request finishes. SQLite connections cannot be shared between threads, so connections are never kept between requests.

### API endpoints

| Endpoint | Description |
| --- | --- |
| `GET /` | Simple "backend is running" message |
| `GET /health` | Health check, returns `{"status": "ok"}` |
| `GET /favicon.ico` | Serves the favicon |
| `GET /sets/years` | All release years that have sets, newest first |
| `GET /sets/{year}` | All sets released in a given year |
| `GET /sets/{set_id}/variants` | Card variants used in a set |
| `GET /sets/{set_id}/rarities` | Rarities used in a set |

`Backend.get_document(set_name)` (in `backend/services/backend_service.py`) syncs the set, generates the images and creates the PDF. It is not exposed through an endpoint yet.

## Stack

- Python
- SQLite
- `FastAPI` and `uvicorn` for the backend API
- `httpx` for API requests
- `Pillow` for image processing and card generation
- `reportlab` for PDF creation
- `python-dotenv` for environment config
- `pytest` for tests
- `natsort` for stable file ordering

## Repository layout

```text
.
├── README.md
└── backend/
    ├── 1st-startup/
    │   ├── first_startup.py          # One-time dependency installation
    │   ├── requirements.txt          # Python dependencies
    │   └── .example.env              # Example API-key configuration
    ├── app.py                        # FastAPI application / entry point
    ├── core/
    │   ├── config.py                 # Dotenv-based config loading
    │   └── startup.py                # Logging, DB bootstrapping and test runner
    ├── database/
    │   ├── db_setup.py               # SQLite connection and schema setup
    │   ├── db_operations.py          # DatabaseOperations: sets, cards, variants, images
    │   └── pokemon_cards.db          # Created at runtime
    ├── functions/
    │   ├── folder_functions.py       # Generated image folder helpers
    │   └── name_functions.py         # File name sanitising
    ├── models/                       # Set and Card model classes
    ├── services/
    │   ├── backend_service.py        # Orchestrates sync, images, and PDF generation
    │   ├── pokemon_tcg_api_service.py # API client for tcgapi.dev
    │   ├── sync_service.py           # Synchronization logic
    │   ├── image_generation_service.py
    │   └── document_generation_service.py
    └── tests/                        # Database operation tests
```

## Setup

All commands are run from the repository root.

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies (either command works):

```bash
python backend/1st-startup/first_startup.py
# or
python -m pip install -r backend/1st-startup/requirements.txt
```

3. Create the environment file:

```bash
cp backend/1st-startup/.example.env backend/.env
```

4. Add your Pokémon TCG API key(s) to `backend/.env`:

```env
POKEMON_TCG_API_KEY_LIST=tcg_live_<40-hex-characters>,tcg_live_<another-40-hex-characters>
```

The configuration loader validates each key using the required `tcg_live_` + 40-character hexadecimal format.

## Running the app

```bash
uvicorn backend.app:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive API documentation.

The command must be run from the repository root, because the code imports modules as `backend.<package>`.

## Tests

```bash
python -m pytest backend/tests
```

The tests use an in-memory SQLite database and cover the database operations for sets, cards, variants and images.

## Generating a PDF

`Backend.get_document(set_name)` performs the following steps:

- synchronizes the available sets from the API
- looks up the set by name
- downloads card data, images and variants for that set
- generates placeholder images saved under `backend/data/generated/<set-name>/`
- creates a PDF named after the set folder in `backend/data/generated/`

## Database structure

The database file is created at:

```text
backend/database/pokemon_cards.db
```

The schema contains:

- `sets`
- `cards`
- `card_variants`
- `card_images`

These tables store the set metadata, card records, variant names, and downloaded image data.

## Output files

Generated assets are saved under:

```text
backend/data/generated/
```

For a successful run, the workflow creates:

- a per-set folder containing generated card images
- a PDF document in the same generated directory

The PDF is saved under the generated folder name, and the source image directory is removed after PDF generation completes.

## Notes about the current implementation

This project is still intentionally narrow in scope:

- there is no interactive command-line selector, and PDF generation is not exposed through an endpoint yet
- there is no production deployment setup
- the code expects a valid API key and a set that already exists in the database or can be synced from the API catalog

## Contributing

The key files to inspect for extending behavior are:

- `backend/app.py` — FastAPI routes
- `backend/core/startup.py` — logging, database setup and test runner
- `backend/services/backend_service.py` — set-to-PDF orchestration
- `backend/services/sync_service.py` — API/database synchronization
- `backend/services/image_generation_service.py` — card image rendering
- `backend/services/document_generation_service.py` — PDF layout generation
- `backend/database/db_operations.py` — SQLite data access layer
- `backend/core/config.py` — API config and environment loading

## License

No license has been specified for this repository yet.

## Repository owner

`Kotorem-sama`
