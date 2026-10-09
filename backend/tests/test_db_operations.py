from collections.abc import Generator
from sqlite3 import Connection

from classes import Card, Set
from database.db_operations import Card_operations, Set_operations
from database.db_setup import DatabaseSetup
from pytest import fixture


@fixture
def db_context() -> Generator[Connection, None, None]:
    db = DatabaseSetup(":memory:")
    connection = db.initialise_db()  # returns the connection that has the tables

    yield connection

    connection.close()

@fixture
def set_operations(db_context: Connection) -> Set_operations:
    return Set_operations(db_context)


@fixture
def card_operations(db_context: Connection) -> Card_operations:
    return Card_operations(db_context)


@fixture
def test_set() -> Set:
    return Set(1, "Test Set", "test-set", "TST", "2026-01-01", 3, 0)


@fixture
def test_card() -> Card:
    return Card(1, 1, "Test Card", "001", "Common", [])


# -------------------------
# Set tests
# -------------------------


def test_add_and_get_set(set_operations: Set_operations, test_set: Set):
    assert set_operations.add_set(test_set) is True

    result = set_operations.get_set_by_id(1)

    assert result is not None
    assert result.id == 1
    assert result.name == "Test Set"
    assert result.slug == "test-set"


def test_get_set_by_slug(set_operations: Set_operations, test_set: Set):
    set_operations.add_set(test_set)

    result = set_operations.get_set_by_slug("test-set")

    assert result is not None
    assert result.id == 1


def test_get_sets_by_year(set_operations: Set_operations, test_set: Set):
    set_operations.add_set(test_set)

    result = set_operations.get_sets_by_year(2026)

    assert len(result) == 1
    assert result[0].name == "Test Set"


def test_update_set(set_operations: Set_operations, test_set: Set):
    set_operations.add_set(test_set)

    test_set.name = "Updated Set"

    assert set_operations.update_set(test_set) is True

    result = set_operations.get_set_by_id(1)

    assert result is not None
    assert result.name == "Updated Set"


def test_delete_set(set_operations: Set_operations, test_set: Set):
    set_operations.add_set(test_set)

    assert set_operations.delete_set(1) is True

    assert set_operations.get_set_by_id(1) is None


# -------------------------
# Card tests
# -------------------------


def test_add_and_get_card(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)

    assert card_operations.add_card(test_card) is True

    result = card_operations.get_card_by_id(1)

    assert result is not None
    assert result.id == 1
    assert result.name == "Test Card"
    assert result.number == "001"


def test_get_cards_by_set(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    result = card_operations.get_cards_by_set(1)

    assert len(result) == 1
    assert result[0].name == "Test Card"


def test_get_cards_by_rarity(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    result = card_operations.get_cards_by_rarity("Common")

    assert len(result) == 1
    assert result[0].name == "Test Card"


def test_update_card(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    test_card.name = "Updated Card"

    assert card_operations.update_card(test_card) is True

    result = card_operations.get_card_by_id(1)

    assert result is not None
    assert result.name == "Updated Card"


def test_delete_card(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    assert card_operations.delete_card(1) is True

    assert card_operations.get_card_by_id(1) is None


# -------------------------
# Variant tests
# -------------------------


def test_add_and_get_variant(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    assert card_operations.add_variant(1, "Normal") is True

    result = card_operations.get_variants(1)

    assert result == ["Normal"]


def test_get_variant_types_in_set(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    card_operations.add_variant(1, "Normal")
    card_operations.add_variant(1, "Reverse Holofoil")

    result = card_operations.get_variant_types_in_set(1)

    assert set(result) == {"Normal", "Reverse Holofoil"}


def test_delete_variant(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    card_operations.add_variant(1, "Normal")

    assert card_operations.delete_variant(1, "Normal") is True

    assert card_operations.get_variants(1) == []


# -------------------------
# Image tests
# -------------------------


def test_save_and_get_image(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    image_data = b"fake image data"
    content_type = "image/png"

    assert card_operations.save_image(1, image_data, content_type) is True

    result = card_operations.get_image(1)

    assert result is not None

    stored_image, stored_content_type = result

    assert stored_image == image_data
    assert stored_content_type == content_type


def test_get_missing_image(card_operations: Card_operations):
    result = card_operations.get_image(999)

    assert result is None


def test_delete_image(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    card_operations.save_image(1, b"fake image data", "image/png")

    assert card_operations.delete_image(1) is True

    assert card_operations.get_image(1) is None


# -------------------------
# Cascade tests
# -------------------------


def test_delete_card_cascades_variants_and_image(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    card_operations.add_variant(1, "Normal")
    card_operations.save_image(1, b"fake image data", "image/png")

    assert card_operations.delete_card(1) is True

    assert card_operations.get_variants(1) == []
    assert card_operations.get_image(1) is None


def test_delete_set_cascades_cards(
    set_operations: Set_operations,
    card_operations: Card_operations,
    test_set: Set,
    test_card: Card,
):
    set_operations.add_set(test_set)
    card_operations.add_card(test_card)

    assert set_operations.delete_set(1) is True

    assert card_operations.get_card_by_id(1) is None
