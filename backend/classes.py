from logging import getLogger
from typing import Any


class Set:
    """Represents a Pokémon TCG set and its synchronisation status."""

    def __init__(
        self,
        id: int,
        name: str,
        slug: str,
        abbreviation: str | None,
        release_date: str | None,
        card_count: int | None,
        sync_complete: int,
    ):
        """Initialize a set with its identifying information and metadata."""
        self.id = id
        self.name = name
        self.slug = slug
        self.abbreviation = abbreviation
        self.release_date = release_date
        self.card_count = card_count
        self.sync_complete = sync_complete

    @classmethod
    def from_api_to_Set(cls, jsondata: Any):
        """Create a Set from API data, returning a fallback object if invalid."""
        logger = getLogger(__name__)
        try:
            new_set = cls(
                jsondata["id"],
                jsondata["name"],
                jsondata["slug"],
                jsondata["abbreviation"],
                jsondata["release_date"],
                jsondata["card_count"],
                0,
            )

            return new_set
        except (KeyError, TypeError, ValueError) as error:
            logger.warning(f"There has been an exception when creating a set: {error}.")

            # A special ID and status indicate that the API data could not be converted.
            new_set = cls(0, "", "", None, None, None, 9)
            return new_set

    def __str__(self):
        """Return a readable representation of the set."""
        return f"{self.name} ({self.release_date})"

    def __repr__(self):
        """Use the readable string representation when displaying the object."""
        return self.__str__()

    def get_dict(self) -> dict[str, int | str]:
        """Return the set's attributes as a dictionary for database operations."""
        dictionary: dict[str, int | str] = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "abbreviation": self.abbreviation if self.abbreviation is not None else "",
            "release_date": self.release_date if self.release_date is not None else "",
            "card_count": self.card_count if self.card_count is not None else 0,
            "sync_complete": self.sync_complete,
        }
        return dictionary


class Card:
    """Represents a Pokémon card and its associated metadata."""

    def __init__(
        self,
        id: int,
        set_id: int,
        name: str,
        number: str | None,
        rarity: str | None,
        card_variants: list[str] | None = None,
    ):
        """Initialize a card with its details and optional variants."""
        self.id = id
        self.set_id = set_id
        self.name = name
        self.number = number
        self.rarity = rarity
        self.card_variants = [] if card_variants is None else card_variants

    @classmethod
    def from_api_to_Card(cls, jsondata: Any, set_id: int):
        """Create a Card from API data, returning a fallback object if invalid."""
        logger = getLogger(__name__)
        try:
            new_card = cls(
                jsondata["id"],
                set_id,
                jsondata["name"],
                jsondata["number"],
                jsondata["rarity"],
            )

            return new_card
        except (KeyError, TypeError, ValueError) as error:
            logger.warning(
                f"There has been an exception when creating a card: {error}."
            )

            # A special ID indicates that the API data could not be converted.
            new_card = cls(0, 0, "", None, None, None)
            return new_card

    def __str__(self):
        """Return a readable representation of the card."""
        return f"{self.name} ({self.number})"

    def __repr__(self):
        """Use the readable string representation when displaying the object."""
        return self.__str__()

    def get_dict(self) -> dict[str, int | str | list[str]]:
        """Return the card's attributes as a dictionary for database operations."""
        dictionary: dict[str, int | str | list[str]] = {
            "id": self.id,
            "set_id": self.set_id,
            "name": self.name,
            "number": self.number if self.number is not None else "",
            "rarity": self.rarity if self.rarity is not None else "",
            "card_variants": self.card_variants,
        }
        return dictionary
