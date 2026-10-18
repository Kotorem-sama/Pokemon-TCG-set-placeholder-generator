from collections.abc import Generator
from sqlite3 import Connection

from pytest import fixture

from backend.database.db_operations import DatabaseOperations
from backend.database.db_setup import Database
from backend.models import Card, Set


@fixture
def db_context() -> Generator[Connection, None, None]:
    db = Database(":memory:")
    db.initialise_db()

    yield db.context

    db.context.close()


@fixture
def db() -> Database:
    return Database(":memory:")


@fixture
def database(db: Database) -> DatabaseOperations:
    return DatabaseOperations(db)


@fixture
def test_set() -> Set:
    return Set(1, "Test Set", "test-set", "TST", "2026-01-01", 3, 0)


@fixture
def test_card() -> Card:
    return Card(1, 1, "Test Card", "001", "Common")


@fixture
def stored_card(database: DatabaseOperations, test_set: Set, test_card: Card) -> Card:
    """A card (and its parent set) that has been added to the database."""
    assert database.sets.add(test_set.get_dict()) is True
    assert database.cards.add(test_card.get_dict()) is True
    return test_card


# -------------------------
# Generic operations
# -------------------------


def test_unknown_table_is_rejected(db_context: Connection):
    from backend.database.db_operations import DatabaseOperationsBaseClass

    try:
        DatabaseOperationsBaseClass(
            "users; DROP TABLE sets", db_context, ["id"], ["id"]
        )
    except ValueError:
        return
    raise AssertionError("An unknown table name should raise a ValueError.")


def test_add_duplicate_returns_false(database: DatabaseOperations, test_set: Set):
    assert database.sets.add(test_set.get_dict()) is True
    assert database.sets.add(test_set.get_dict()) is False


def test_update_missing_entry_returns_false(
    database: DatabaseOperations, test_set: Set
):
    assert database.sets.update(test_set.get_dict()) is False


def test_delete_missing_entry_returns_false(database: DatabaseOperations):
    assert database.sets.delete({"id": 999}) is False


def test_delete_rejects_unknown_column(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())

    assert database.sets.delete({"nonexistent": 1}) is False
    assert database.sets.delete({}) is False
    assert database.sets.get_by_id(1) is not None


# -------------------------
# Set tests
# -------------------------


def test_add_and_get_set(database: DatabaseOperations, test_set: Set):
    assert database.sets.add(test_set.get_dict()) is True

    result = database.sets.get_by_id(1)

    assert result is not None
    assert result.id == 1
    assert result.name == "Test Set"
    assert result.slug == "test-set"


def test_get_missing_set(database: DatabaseOperations):
    assert database.sets.get_by_id(999) is None
    assert database.sets.get_by_name("Nope") is None


def test_set_with_null_fields(database: DatabaseOperations):
    null_set = Set(2, "Null Set", "null-set", None, None, None, 0)

    assert database.sets.add(null_set.get_dict()) is True

    result = database.sets.get_by_id(2)

    assert result is not None
    assert result.abbreviation is None
    assert result.release_date is None
    assert result.card_count is None


def test_get_set_by_name(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())

    result = database.sets.get_by_name("Test Set")

    assert result is not None
    assert result.id == 1


def test_get_all_sets(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())
    database.sets.add(Set(2, "Other", "other", None, "2025-05-05", 1, 0).get_dict())

    assert len(database.sets.get_all()) == 2


def test_get_sets_by_year(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())
    database.sets.add(Set(2, "Old", "old", None, "2025-05-05", 1, 0).get_dict())

    result = database.sets.get_by_year(2026)

    assert len(result) == 1
    assert result[0].name == "Test Set"
    assert database.sets.get_by_year(1999) == []


def test_get_release_date_years(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())
    database.sets.add(Set(2, "Old", "old", None, "2025-05-05", 1, 0).get_dict())
    database.sets.add(Set(3, "Same", "same", None, "2025-06-06", 1, 0).get_dict())
    database.sets.add(Set(4, "None", "none", None, None, 1, 0).get_dict())
    database.sets.add(Set(5, "Empty", "empty", None, "", 1, 0).get_dict())

    assert database.sets.get_release_date_years() == ["2026", "2025"]


def test_update_set(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())

    test_set.name = "Updated Set"

    assert database.sets.update(test_set.get_dict()) is True

    result = database.sets.get_by_id(1)

    assert result is not None
    assert result.name == "Updated Set"


def test_delete_set(database: DatabaseOperations, test_set: Set):
    database.sets.add(test_set.get_dict())

    assert database.sets.delete({"id": 1}) is True

    assert database.sets.get_by_id(1) is None


# -------------------------
# Card tests
# -------------------------


def test_add_and_get_card(database: DatabaseOperations, stored_card: Card):
    result = database.cards.get_by_id(1)

    assert result is not None
    assert result.name == "Test Card"
    assert result.set_id == 1


def test_get_missing_card(database: DatabaseOperations):
    assert database.cards.get_by_id(999) is None


def test_get_all_cards(database: DatabaseOperations, stored_card: Card):
    assert len(database.cards.get_all()) == 1


def test_get_cards_in_set(database: DatabaseOperations, stored_card: Card):
    result = database.cards.get_in_set(1)

    assert len(result) == 1
    assert result[0].id == 1
    assert database.cards.get_in_set(999) == []


def test_get_amount_in_set(database: DatabaseOperations, stored_card: Card):
    assert database.cards.get_amount_in_set(1) == 1
    assert database.cards.get_amount_in_set(999) == 0


def test_get_rarities_in_set(database: DatabaseOperations, stored_card: Card):
    database.cards.add(Card(2, 1, "Rare Card", "002", "Rare").get_dict())
    database.cards.add(Card(3, 1, "Promo Card", "003", "Promo").get_dict())
    database.cards.add(Card(4, 1, "Uncommon Card", "004", "Uncommon").get_dict())

    assert database.cards.get_rarities_in_set(1) == [
        "Common",
        "Uncommon",
        "Rare",
        "Promo",
    ]
    assert database.cards.get_rarities_in_set(999) == []


def test_update_card(database: DatabaseOperations, stored_card: Card):
    stored_card.name = "Updated Card"

    assert database.cards.update(stored_card.get_dict()) is True

    result = database.cards.get_by_id(1)

    assert result is not None
    assert result.name == "Updated Card"


def test_delete_card(database: DatabaseOperations, stored_card: Card):
    assert database.cards.delete({"id": 1}) is True

    assert database.cards.get_by_id(1) is None


def test_deleting_set_cascades_to_cards(
    database: DatabaseOperations, stored_card: Card
):
    assert database.sets.delete({"id": 1}) is True

    assert database.cards.get_by_id(1) is None


# -------------------------
# Variant tests
# -------------------------


def test_add_and_get_variants(database: DatabaseOperations, stored_card: Card):
    assert database.variants.add({"card_id": 1, "variant": "Holofoil"}) is True
    assert database.variants.add({"card_id": 1, "variant": "Normal"}) is True
    assert database.variants.add({"card_id": 1, "variant": "Reverse Holofoil"}) is True

    assert database.variants.get_by_card_id(1) == [
        "Normal",
        "Reverse Holofoil",
        "Holofoil",
    ]


def test_get_variants_in_set(database: DatabaseOperations, stored_card: Card):
    database.variants.add({"card_id": 1, "variant": "Normal"})
    database.variants.add({"card_id": 1, "variant": "Reverse Holofoil"})

    result = database.variants.get_in_set(1)

    assert sorted(result) == ["Normal", "Reverse Holofoil"]
    assert database.variants.get_in_set(999) == []


def test_delete_all_variants_by_card_id(
    database: DatabaseOperations, stored_card: Card
):
    database.variants.add({"card_id": 1, "variant": "Normal"})
    database.variants.add({"card_id": 1, "variant": "Holofoil"})

    assert database.variants.delete_all_by_card_id(1) is True

    assert database.variants.get_by_card_id(1) == []


# -------------------------
# Image tests
# -------------------------


def test_add_and_get_image(database: DatabaseOperations, stored_card: Card):
    assert (
        database.images.add(
            {"card_id": 1, "image_data": b"fake-image", "content_type": "image/png"}
        )
        is True
    )

    assert database.images.get_by_card_id(1) == (b"fake-image", "image/png")


def test_get_missing_image(database: DatabaseOperations):
    assert database.images.get_by_card_id(999) is None
