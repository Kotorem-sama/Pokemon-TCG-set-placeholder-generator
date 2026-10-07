# Pokémon TCG Set Placeholder Generator

This project is a local-only Python utility for fetching Pokémon TCG set and card data from tcgapi.dev and saving it into a SQLite database. It is designed to support future generation of a Word document containing placeholders for a full Pokémon set.

Current status: the data sync layer is in place, but the final document-generation feature is not yet implemented.

## What it does

- Connects to the Pokémon TCG API at `https://api.tcgapi.dev`
- Loads one or more API keys from an environment file
- Syncs set metadata and card data for selected Pokémon sets
- Stores data in SQLite tables for:
  - `sets`
  - `cards`
  - `card_variants`
  - `card_images`
- Supports future placeholder document generation from the synced dataset

## Stack

- Python
- SQLite
- `httpx` for API requests
- `fastapi` and `uvicorn` are included in dependencies but are not currently the main app runtime
- `python-docx` is included for future document generation

## Repository layout

```text
.
├── .gitignore
├── .env.example
├── README.md
└── backend/
    ├── api/
    │   └── pokemon_tcg_api.py       # API client for tcgapi.dev
    ├── database/
    │   ├── db_setup.py               # SQLite schema setup
    │   ├── db_operations.py          # CRUD operations for sets/cards/images
    │   └── __init__.py
    ├── services/
    │   ├── SyncService.py            # Sync logic for sets/cards/images
    │   └── __init__.py
    ├── classes.py                   # Set and Card model classes
    ├── config.py                    # Dotenv-based config loading
    ├── initializer.py               # Dependency install + DB bootstrapping
    ├── main.py                      # Entry point for running sync tasks
    ├── requirements.txt             # Python dependencies
    └── tests/                       # Placeholder area for future automated tests
```

## Setup

1. Clone the repository.
2. Create a Python virtual environment if desired.
3. Install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

4. Create a `.env` file from the example:

```bash
cp .env.example .env
```

5. Add your API key(s):

```env
POKEMON_TCG_API_KEY_LIST=your-api-key-here,backup-key-here
```

The code accepts a comma-separated list of keys, so you can provide multiple tokens if needed.

## Running the project

From the repository root, run:

```bash
python backend/main.py
```

This currently triggers the startup sequence and syncs a fixed set (`"Ascended heroes"`) by default.

## Current behavior

When the app runs, it:

1. Initializes the SQLite database if it does not exist
2. Installs Python dependencies from `backend/requirements.txt`
3. Fetches set metadata from the API
4. Pulls card data for the configured set
5. Saves metadata, cards, variants, and card images into the database

## Database

The database is created at:

```text
backend/database/pokemon_cards.db
```

The schema includes:

- `sets`: metadata for each Pokémon TCG set
- `cards`: card-level data for each card in a set
- `card_variants`: printings/variant names for cards
- `card_images`: image blobs and content type information

## Important note

This project is not yet complete as a full placeholder document generator. The code currently covers the API sync and persistence layer. The next steps are expected to include:

- generating a Word document from saved data
- formatting placeholders for a Pokémon set
- creating a user-friendly CLI or workflow to choose which set to generate
- additional validation and tests

## Contributing

If you want to extend the project, the main areas to look at are:

- `backend/api/pokemon_tcg_api.py` for API access
- `backend/services/SyncService.py` for synchronization logic
- `backend/database/db_operations.py` for data storage and queries
- `backend/main.py` for starting the sync flow

## License

No license has been specified in this repository yet.

## Contact / repo owner

Repository owner: `Kotorem-sama`

This project was created as a local utility and is intended to run on a developer machine rather than as a hosted web application.
