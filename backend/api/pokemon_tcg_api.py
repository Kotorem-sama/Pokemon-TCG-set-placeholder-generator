from config import API_KEY, BASE_URL, TIMEOUT
from httpx import AsyncClient
from typing import Any

class PokemonTCGAPI:
    def __init__(self) -> None:
        self.api_key = API_KEY
        self.base_url = BASE_URL
        self.timeout = TIMEOUT

    async def _request(self, method:str, endpoint:str, headers: dict[str, str] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"

        assert self.api_key is not None
        headers = {} if headers is None else headers
        headers["X-API-Key"] = self.api_key
        try:

            async with AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers)

            response.raise_for_status()

            return { "success": True, "data": response.json()["data"] }
        
        except Exception as error:
            return { "success": False, "error": str(error) }

    async def __get_all_pages(self, method:str, endpoint:str, start_page:int = 1) -> Any:
        response = await self._request(method, f"{endpoint}&page={start_page}")

        if not response["success"]:
            return response
        
        page = start_page+1
        while True:
            next_response = await self._request(method, f"{endpoint}&page={page}")

            if not next_response["success"]:
                return next_response

            if next_response['data'] == []:
                break
            
            response['data'].extend(next_response['data'])
            page += 1

        return response

    async def get_sets(self) -> Any:
        return await self.__get_all_pages("GET", "/v1/sets?game=pokemon&per_page=100")

    async def get_set(self, set_id: int) -> Any:
        return await self._request("GET", f"/v1/sets/{set_id}")

    async def get_cards(self, set_id:int, start_page:int = 1) -> Any:
        return await self.__get_all_pages("GET", f"/v1/sets/{set_id}/cards?per_page=100", start_page)

    async def get_card(self, card_id: int) -> Any:
        return await self._request("GET", f"/v1/cards/{card_id}")

    async def get_card_prices(self, card_id: int) -> Any:
        return await self._request("GET", f"/v1/cards/{card_id}/prices")