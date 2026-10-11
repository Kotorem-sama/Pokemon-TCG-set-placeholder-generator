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

## Current launcher behavior

The entry point is `backend/main.py`.

When the app starts, it:

1. Runs database and dependency setup
2. Executes the unit tests under `backend/tests`
3. Calls `SetToPDF(db.db_context).get_document("White flare")`

That means the current workflow is hard-coded to the set name `White flare` rather than exposing a user-selectable CLI or menu.

The set lookup is performed via a `LIKE` match, so the name does not need to be an exact string match to be found.

## Stack

- Python
- SQLite
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
    ├── api/
    │   └── pokemon_tcg_api.py       # API client for tcgapi.dev
    ├── database/
    │   ├── db_setup.py               # SQLite schema setup
    │   ├── db_operations.py          # CRUD operations for sets/cards/images
    │   └── pokemon_cards.db          # Created at runtime
    ├── services/
    │   ├── sync_service.py           # Synchronization logic
    │   ├── image_generation_service.py
    │   ├── document_generation_service.py
    │   └── set_to_pdf_service.py     # Orchestrates sync, images, and PDF generation
    ├── models/                      # Set and Card model classes
    ├── core/
    │   ├── config.py                 # Dotenv-based config loading
    │   └── startup.py                # Dependency install + DB bootstrapping
    ├── main.py                      # Entry point for running sync tasks
    ├── requirements.txt             # Python dependencies
    ├── .example.env                 # Example API-key configuration
    └── tests/                       # Database operation tests
```

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

3. Create the environment file:

```bash
cp backend/.example.env backend/.env
```

4. Add your Pokémon TCG API key(s):

```env
POKEMON_TCG_API_KEY_LIST=tcg_live_<40-hex-characters>,tcg_live_<another-40-hex-characters>
```

The configuration loader validates each key using the required `tcg_live_` + 40-character hexadecimal format.

## How the app works

The main startup flow is:

```bash
python backend/main.py
```

This triggers the following operations:

- `initializer.startup()` configures logging and installs dependencies
- the SQLite database is created and integrity-checked
- tests run from `backend/tests`
- the document generator synchronizes available sets and then attempts to fetch the set named `White flare`
- if the set exists, it downloads card data and images
- placeholder images are generated and saved under `backend/data/generated/<set-name>/`
- a PDF named after the set folder is generated in `backend/data/generated/`

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

- the set to process is hard-coded in `backend/main.py`
- there is no interactive command-line selector yet
- there is no production web interface or hosted deployment
- the code expects a valid API key and a set that already exists in the database or can be synced from the API catalog

## Contributing

The key files to inspect for extending behavior are:

- `backend/main.py` — launcher flow
- `backend/placeholder_pdf_creator.py` — set-to-PDF orchestration
- `backend/services/sync_service.py` — API/database synchronization
- `backend/services/image_generation_service.py` — card image rendering
- `backend/services/document_generation_service.py` — PDF layout generation
- `backend/database/db_operations.py` — SQLite data access layer
- `backend/config.py` — API config and environment loading

## License

No license has been specified for this repository yet.

## Repository owner

`Kotorem-sama`
