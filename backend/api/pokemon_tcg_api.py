import asyncio
import logging
from re import findall
from typing import Any

from httpx import AsyncClient, HTTPStatusError, RequestError, Response

from config import API_KEYS, BASE_URL, TIMEOUTS


class PokemonTCGAPI:
    """Handles asynchronous requests to the Pokémon TCG API."""

    def __init__(self) -> None:
        self.api_keys: list[str] = API_KEYS
        self.base_url = BASE_URL
        self.timeouts = TIMEOUTS
        self.key_number = 0
        self.retried_request = False

    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        timeout_type: str = "default",
    ) -> Any:
        """Send an API request, handling retries, API keys and response errors."""
        logger = logging.getLogger(__name__)

        if not self.api_keys:
            return {"success": False, "error": ""}

        if self.key_number > len(self.api_keys) - 1:
            logger.error(
                "All API keys have run out of tokens."
                "Please wait until tomorrow to try again, or add a new key in the .env file."
            )
            return {"success": False, "error": ""}

        headers = {} if headers is None else headers
        headers["X-API-Key"] = self.api_keys[self.key_number]

        url = f"{self.base_url}{endpoint}"
        logger.info(f"Trying '{method} {url}'")

        try:
            async with AsyncClient(timeout=self.timeouts[timeout_type]) as client:
                response = await client.request(method, url, headers=headers)

            # Retry a server error once after a short delay.
            if (
                findall(r"\b5\d{2}\b", str(response.status_code))
                and not self.retried_request
            ):
                logger.warning("There has been a server error. Trying ahain")
                self.retried_request = True

                await asyncio.sleep(2.5)
                return await self._request(method, endpoint, headers, timeout_type)

            self.retried_request = False

            if response.status_code == 401:
                logger.warning(
                    "401: The request got denied due to a failty API key."
                    "Trying again with a different key if there is another."
                )

            if response.status_code == 429:
                logger.warning(
                    "429: The request got denied due to the API key having run out of tokens."
                    "Trying again with a different key if there is another."
                )

            # Move to the next API key when the current key is rejected or rate-limited.
            if response.status_code in [401, 429]:
                self.key_number = self.key_number + 1

                headers.pop("X-API-Key")
                return await self._request(method, endpoint, headers, timeout_type)

            response.raise_for_status()

            logger.info(f"The call has succeeded with code: {response.status_code}")
            return {"success": True, "data": response.json()["data"]}

        except HTTPStatusError as error:
            logger.warning("API returned an unsuccessful status: %s", error)
            return {"success": False, "error": str(error)}

        except RequestError as error:
            logger.warning("API request failed: %s", error)
            return {"success": False, "error": str(error)}

        except (KeyError, ValueError) as error:
            logger.warning("Failed to parse API response: %s", error)
            return {"success": False, "error": str(error)}

    async def __get_all_pages(
        self,
        method: str,
        endpoint: str,
        start_page: int = 1,
        timeout_type: str = "default",
    ) -> Any:
        """Retrieve all pages of results and combine them into one response."""
        response = await self._request(
            method, f"{endpoint}&page={start_page}", {}, timeout_type
        )

        if not response["success"]:
            return response

        page = start_page + 1
        while True:
            next_response = await self._request(
                method, f"{endpoint}&page={page}", {}, timeout_type
            )

            if not next_response["success"]:
                return next_response

            if next_response["data"] == []:
                break

            response["data"].extend(next_response["data"])
            page += 1

        return response

    async def get_sets(self) -> Any:
        """Retrieve all Pokémon TCG sets."""
        return await self.__get_all_pages("GET", "/v1/sets?game=pokemon&per_page=100")

    async def get_set(self, set_id: int) -> Any:
        """Retrieve a specific set by its ID."""
        return await self._request("GET", f"/v1/sets/{set_id}", {}, "card_list")

    async def get_cards(self, set_id: int, start_page: int = 1) -> Any:
        """Retrieve all cards belonging to a set."""
        return await self.__get_all_pages(
            "GET", f"/v1/sets/{set_id}/cards?per_page=100", start_page, "card_list"
        )

    async def get_card(self, card_id: int) -> Any:
        """Retrieve a specific card by its ID."""
        return await self._request("GET", f"/v1/cards/{card_id}")

    async def get_card_prices(self, card_id: int) -> Any:
        """Retrieve price information for a specific card."""
        return await self._request("GET", f"/v1/cards/{card_id}/prices")

    async def get_image(self, image_url: str) -> Any:
        """Download an image and return its bytes and content type."""
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Trying 'GET {image_url}'")
            async with AsyncClient(timeout=self.timeouts["image"]) as client:
                response: Response = await client.get(image_url)

            if response.status_code == 404:
                logger.warning("404: Image does not exist.")

                return {
                    "success": True,
                    "data": {"image_data": None, "content_type": "False"},
                }

            response.raise_for_status()

            content_type = response.headers.get("Content-Type")

            if content_type is None:
                logger.warning("Image response did not contain a Content-Type header.")
                return {
                    "success": False,
                    "error": "",
                }

            logger.info("Succesfully obtained the image!")
            return {
                "success": True,
                "data": {"image_data": response.content, "content_type": content_type},
            }

        except HTTPStatusError as error:
            logger.warning("Image request returned an unsuccessful status: %s", error)
            return {"success": False, "error": str(error)}

        except RequestError as error:
            logger.warning("Image request failed: %s", error)
            return {"success": False, "error": str(error)}
