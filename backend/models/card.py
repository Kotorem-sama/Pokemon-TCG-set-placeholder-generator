from logging import getLogger
from typing import Any


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
