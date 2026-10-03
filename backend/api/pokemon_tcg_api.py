from backend.config import API_KEY, BASE_URL, TIMEOUT
from httpx import AsyncClient
from typing import Any

class PokemonTCGAPI:
    def __init__(self) -> None:
        self.api_key = API_KEY
        self.base_url = BASE_URL
        self.timeout = TIMEOUT

    async def _request(self, method:str, endpoint:str) -> Any:
        url = f"{self.base_url}{endpoint}"

        assert self.api_key is not None
        headers = {
            "X-API-Key": self.api_key
        }

        async with AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, headers=headers)

        response.raise_for_status()
        return response.json() 
