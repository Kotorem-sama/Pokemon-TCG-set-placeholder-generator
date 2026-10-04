import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("POKEMON_TCG_API_KEY")
BASE_URL = "https://api.tcgapi.dev"
TIMEOUT = 10

if API_KEY is None:
    raise ValueError("POKEMON_TCG_API_KEY is not set")

assert API_KEY is not None