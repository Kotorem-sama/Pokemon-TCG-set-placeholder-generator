import logging
import os
import re

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

"""Load API configuration from the .env file."""
if not load_dotenv():
    logger.warning(
        "No '.env' file has been detected. "
        "Please use '.example.env', fill in an API key and rename the file to '.env'."
    )

API_KEYS: list[str] = [
    key.strip()
    for key in os.getenv("POKEMON_TCG_API_KEY_LIST", "").split(",")
    if key.strip()
]

BASE_URL: str = "https://api.tcgapi.dev"
TIMEOUTS = {
    "set_metadata": 10,
    "card_list": 30,  # More cards = longer
    "image": 60,       # Images are bigger
    "default": 10
}

# TCGAPI keys must use the format tcg_live_<40 hexadecimal characters>.
API_KEY_PATTERN = re.compile(r"^tcg_live_[a-f0-9]{40}$")

for key in API_KEYS.copy():
    if not API_KEY_PATTERN.fullmatch(key):
        logger.warning(
            "An API key does not match the expected format. "
            "Expected: tcg_live_<40 hexadecimal characters>"
        )
        API_KEYS.remove(key)

if not API_KEYS:
    logger.error(
        "No valid API key has been set. "
        "Please check the POKEMON_TCG_API_KEY_LIST value in your .env file."
    )
