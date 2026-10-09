# Pokémon TCG Set Placeholder Generator

This project is a local-only Python utility for fetching Pokémon TCG set and card data from tcgapi.dev, saving it in SQLite, and generating card images and a PDF placeholder sheet.

The current launcher targets the `ME: 30th Celebration` set. The set must already exist in the database; the launcher does not populate the set catalog.

## What it does

- Connects to the Pokémon TCG API at `https://api.tcgapi.dev`
- Loads one or more API keys from an environment file
- Syncs set metadata and card data for selected Pokémon sets
- Stores data in SQLite tables for:
  - `sets`
  - `cards`
  - `card_variants`
  - `card_images`
- Generates card images and a PDF from a set already present in the database

## Stack

- Python
- SQLite
- `httpx` for API requests
- `fastapi` and `uvicorn` are listed in dependencies but are not used by the current launcher
- `Pillow` and `reportlab` are used for image and PDF generation

## Repository layout

```text
.
├── .gitignore
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
    │   └── document_generation_service.py
    ├── classes.py                   # Set and Card model classes
    ├── config.py                    # Dotenv-based config loading
    ├── initializer.py               # Dependency install + DB bootstrapping
    ├── placeholder_pdf_creator.py   # Orchestrates sync, images, and PDF generation
    ├── main.py                      # Entry point for running sync tasks
    ├── requirements.txt             # Python dependencies
    ├── .example.env                 # Example API-key configuration
    └── tests/                       # Database operation tests
```

## Setup

1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. Install the dependencies before starting the launcher:

```bash
python -m pip install -r backend/requirements.txt
```

The launcher imports `python-dotenv` and `pytest` before its startup installer runs, so this installation step is required in a clean environment.

3. Create `backend/.env` from the example file:

```bash
cp backend/.example.env backend/.env
```

4. Set one or more valid API keys in `backend/.env`:

```env
POKEMON_TCG_API_KEY_LIST=tcg_live_<40-hex-characters>,tcg_live_<another-40-hex-characters>
```

The config loader accepts a comma-separated list and filters keys that do not match the `tcg_live_` plus 40 hexadecimal characters format. The launcher also invokes the package installer during startup.

## Running the project

From the repository root, run:

```bash
python backend/main.py
```

The launcher installs dependencies, creates and checks the SQLite database, runs the tests in `backend/tests`, and asks the PDF workflow to process `ME: 30th Celebration`.

The requested set must already be in the database. The launcher does not call the set-catalog sync method, so a newly created database has no set to process and no PDF will be produced. The API key is needed when the workflow syncs cards and images for a set.

## Current behavior

When the requested set is present, the PDF workflow:

1. Synchronizes the set's information and card data with the API
2. Saves card metadata, variants, and downloaded images in SQLite
3. Generates image files for the set, including template overlays where applicable
4. Creates an A4 PDF with up to nine card images per page

Generated images and PDFs are written under `backend/data/generated/`. The PDF is named after the set's generated-image folder.

## Database

The database is created at:

```text
backend/database/pokemon_cards.db
```

The schema includes:

- `sets`: metadata for each Pokémon TCG set
- `cards`: card-level data for each card in a set
- `card_variants`: printings/variant names for cards
- `card_images`: downloaded image blobs and content type information

## Important note

The current launcher is not yet a set-selection workflow. It is hard-coded to one set name, and a set catalog must be populated in the database before it can generate output. Further work could include:

- synchronizing the set catalog from the API in the launcher
- allowing users to choose which set to generate
- additional validation and tests

## Contributing

If you want to extend the project, the main areas to look at are:

- `backend/api/pokemon_tcg_api.py` for API access
- `backend/services/sync_service.py` for synchronization logic
- `backend/services/image_generation_service.py` and `backend/services/document_generation_service.py` for output generation
- `backend/database/db_operations.py` for data storage and queries
- `backend/main.py` for starting the sync flow

## License

No license has been specified in this repository yet.

## Contact / repo owner

Repository owner: `Kotorem-sama`

This project was created as a local utility and is intended to run on a developer machine rather than as a hosted web application.
