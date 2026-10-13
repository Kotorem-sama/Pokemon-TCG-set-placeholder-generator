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

    def get_dict(self) -> dict[str, str | int | bytes | None]:
        """Return the set's attributes as a dictionary for database operations."""
        dictionary: dict[str, str | int | bytes | None] = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "abbreviation": self.abbreviation,
            "release_date": self.release_date,
            "card_count": self.card_count,
            "sync_complete": self.sync_complete,
        }
        return dictionary
