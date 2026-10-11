from asyncio import run
from typing import Any

from pytest import mark

from services.sync_service import SyncService


class FakeAPI:
    def __init__(self, response: Any):
        self.response = response

    async def get_card_prices(self, card_id: int) -> Any:
        return self.response


class FakeCardOperations:
    def __init__(self, fail_on: str | None = None):
        self.variants: list[str] = []
        self.fail_on = fail_on

    def add_variant(self, card_id: int, variant: str) -> bool:
        if variant == self.fail_on:
            return False
        self.variants.append(variant)
        return True

    def delete_variants(self, card_id: int) -> bool:
        self.variants.clear()
        return True


def create_service(response: Any, fail_on: str | None = None) -> tuple[SyncService, FakeCardOperations]:
    card_operations = FakeCardOperations(fail_on)
    service = SyncService(None, FakeAPI(response), card_operations)
    return service, card_operations


@mark.parametrize(
    ("data", "expected"),
    [
        ([{"printing": "Normal"}, {"printing": "Foil"}], ["Normal", "Holofoil"]),
        ([{"printing": ""}], ["Normal"]),
        ([{}], ["Normal"]),
        ([], ["Normal"]),
    ],
)
def test_sync_card_variants_normalizes_valid_data(data, expected):
    service, card_operations = create_service({"success": True, "data": data})

    assert run(service.sync_card_variants(123, "Common")) is True
    assert card_operations.variants == expected


@mark.parametrize(
    "response",
    [
        {"success": True, "data": None},
        {"success": True, "data": "not-a-list"},
        {"success": True, "data": [{"printing": "Normal"}, None]},
        {"success": True, "data": [{"printing": ["not", "a", "string"]}]},
        None,
        [],
    ],
)
def test_sync_card_variants_rejects_malformed_data(response):
    service, card_operations = create_service(response)

    assert run(service.sync_card_variants(123, "Common")) is False
    assert card_operations.variants == []


def test_sync_card_variants_cleans_up_when_database_insert_fails():
    service, card_operations = create_service(
        {"success": True, "data": [{"printing": "Normal"}, {"printing": "Foil"}]},
        fail_on="Holofoil",
    )

    assert run(service.sync_card_variants(123, "Common")) is False
    assert card_operations.variants == []
