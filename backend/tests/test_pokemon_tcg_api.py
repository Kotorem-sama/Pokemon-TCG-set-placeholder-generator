from asyncio import run
from unittest.mock import AsyncMock, MagicMock, patch

from api.pokemon_tcg_api import PokemonTCGAPI


def run_request(json_data):
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    response.json.return_value = json_data

    client = MagicMock()
    client.request = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client)
    client_context.__aexit__ = AsyncMock(return_value=None)

    api = PokemonTCGAPI()
    api.api_keys = ["test-key"]
    with patch("api.pokemon_tcg_api.AsyncClient", return_value=client_context):
        return run(api._request("GET", "/test"))


def test_request_returns_data_from_valid_response():
    assert run_request({"data": [{"id": 1}]}) == {
        "success": True,
        "data": [{"id": 1}],
    }


def test_request_rejects_non_object_json():
    assert run_request(None) == {"success": False}
    assert run_request([]) == {"success": False}


def test_request_rejects_response_without_data():
    assert run_request({"unexpected": "shape"}) == {"success": False}
