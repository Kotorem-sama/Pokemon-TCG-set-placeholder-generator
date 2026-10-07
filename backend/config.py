import os
from dotenv import load_dotenv

load_dotenv()

API_KEYS = [
    key.strip()
    for key in os.getenv("POKEMON_TCG_API_KEY_LIST", "").split(",")
    if key.strip()
]

BASE_URL = "https://api.tcgapi.dev"
TIMEOUT = 10

if not API_KEYS:
    raise ValueError("POKEMON_TCG_API_KEY is not set")