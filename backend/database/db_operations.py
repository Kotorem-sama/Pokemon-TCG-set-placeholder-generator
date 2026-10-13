from logging import getLogger
from sqlite3 import Connection, Row
from sqlite3 import Error as db_error

from backend.models import Card, Set


class DatabaseOperations:
    def __init__(self, context: Connection) -> None:
        self.sets = SetOperations(context)
        self.cards = CardOperations(context)
        self.variants = CardVariantsOperations(context)
        self.images = CardImageOperations(context)


class DatabaseOperationsBaseClass:
    def __init__(
        self, table_name: str, context: Connection, columns: list[str]
    ) -> None:
        if table_name not in ["sets", "cards", "card_variants", "card_images"]:
            raise ValueError(f"Unknown table: {table_name}")

        self.logger = getLogger(__name__)
        self.table_name = table_name
        self.context = context
        self.columns: dict[str, str] = {c: f":{c}" for c in columns}

    def get(
        self,
        values: dict[str, str | int],
        what_clause: str,
        join_clause: str = "",
        where_clause: str = "1=1",
        suffix: str = "",
        fetch_all: bool = False,
    ) -> list[dict[str, str | int | bytes | None]]:
        """Gets data from table_name using a custom SQL query."""
        cursor = self.context.cursor()
        try:
            cursor.execute(
                f"SELECT {what_clause} FROM {self.table_name} {join_clause} WHERE {where_clause} {suffix}",
                values,
            )
            rows: list[Row] = (
                cursor.fetchall()
                if fetch_all
                else [row for row in [cursor.fetchone()] if row]
            )
            return [dict(row) for row in rows]
        except db_error:
            self.logger.exception("Failed to get information from database.")
            return []
        finally:
            cursor.close()

    def add(self, new_entry: dict[str, str | int | bytes | None]) -> bool:
        """Adds data to the set table."""
        self.logger.info(f"Adding '{new_entry}' to the table '{self.table_name}'.")
        cursor = self.context.cursor()

        try:
            cols = ", ".join(self.columns)
            params = ", ".join(self.columns.values())
            cursor.execute(
                f"""INSERT INTO {self.table_name} ({cols})            
            VALUES({params})""",
                new_entry,
            )

            self.context.commit()
            self.logger.info(
                f"Successfully added '{new_entry}' to the table '{self.table_name}'!"
            )
            return True

        except db_error as error:
            self.logger.warning(
                f"Failed to insert '{new_entry}' into the table '{self.table_name}': {error}."
            )
            return False

        finally:
            cursor.close()

    def update(self, update_entry: dict[str, str | int | bytes | None]) -> bool:
        self.logger.info(f"Updating {update_entry} to the table {self.table_name}.")
        cursor = self.context.cursor()
        try:
            assignments = ", ".join(
                f"{col} = {param}" for col, param in self.columns.items() if col != "id"
            )
            cursor.execute(
                f"UPDATE {self.table_name} SET {assignments} WHERE id = :id",
                update_entry,
            )
            self.context.commit()
            self.logger.info(
                f"Successfully updated '{update_entry}' to table '{self.table_name}'!"
            )
            return cursor.rowcount > 0
        except db_error as error:
            self.logger.warning(
                f"Failed to update '{update_entry}' in table '{self.table_name}': {error}."
            )
            return False

        finally:
            cursor.close()

    def delete(self, values: dict[str, str | int | bytes | None]) -> bool:
        """Delete inserted id from the class' table."""
        self.logger.info(
            f"Attempting to delete '{values}' from table '{self.table_name}'."
        )

        if not values or any(col not in self.columns for col in values):
            self.logger.warning(
                f"Invalid delete keys {list(values)} for '{self.table_name}'."
            )
            return False

        where_clause = " AND ".join(f"{col} = :{col}" for col in values)

        cursor = self.context.cursor()
        try:
            cursor.execute(
                f"""DELETE FROM {self.table_name} WHERE {where_clause}""",
                values,
            )
            self.context.commit()

            self.logger.info(
                f"Successfully deleted '{values}' from table '{self.table_name}'!"
            )
            return cursor.rowcount > 0
        except db_error as error:
            self.logger.warning(
                f"Failed to delete '{values}' from table '{self.table_name}': {error}."
            )
            return False
        finally:
            cursor.close()


class SetOperations(DatabaseOperationsBaseClass):
    """Provides database operations for Pokémon TCG sets."""

    def __init__(self, context: Connection) -> None:
        super().__init__(
            "sets",
            context,
            [
                "id",
                "name",
                "slug",
                "abbreviation",
                "release_date",
                "card_count",
                "sync_complete",
            ],
        )

    def __cast_as_sets(
        self, data: list[dict[str, str | int | bytes | None]]
    ) -> list[Set]:
        sets: list[Set] = []

        for db_set in data:
            set_id = db_set.get("id")
            name = db_set.get("name")
            slug = db_set.get("slug")
            abbreviation = db_set.get("abbreviation")
            release_date = db_set.get("release_date")
            card_count = db_set.get("card_count")
            sync_complete = db_set.get("sync_complete")

            if (
                not isinstance(set_id, int)
                or not isinstance(name, str)
                or not isinstance(slug, str)
                or not isinstance(sync_complete, int)
            ):
                self.logger.warning(
                    f"Cannot create a set from the giving data: {db_set}."
                )
                continue

            sets.append(
                Set(
                    set_id,
                    name,
                    slug,
                    abbreviation if isinstance(abbreviation, str) else None,
                    release_date if isinstance(release_date, str) else None,
                    card_count if isinstance(card_count, int) else None,
                    sync_complete,
                )
            )
        return sets

    def get_by_year(self, year: int) -> list[Set]:
        """Retrieve all sets released in a specific year."""
        return self.__cast_as_sets(
            self.get(
                {"year": str(year)},
                "*",
                where_clause="substr(release_date, 1, 4) = :year",
                fetch_all=True,
            )
        )

    def get_all(self) -> list[Set]:
        """Retrieve all sets from the database."""
        return self.__cast_as_sets(self.get({}, "*", fetch_all=True))

    def get_by_id(self, set_id: int) -> Set | None:
        """Retrieve set by it's id."""
        current_set = self.__cast_as_sets(
            self.get({"id": set_id}, "*", where_clause="id = :id")
        )
        return None if not current_set else current_set[0]

    def get_by_name(self, set_name: str) -> Set | None:
        """Retrieve sets matching a name."""
        current_set = self.__cast_as_sets(
            self.get({"name": set_name}, "*", where_clause="name = :name")
        )
        return None if not current_set else current_set[0]

    def get_release_date_years(self) -> list[str]:
        """Retrieve all years of sets that are in the database. Returns a list of strings."""
        years = self.get(
            {},
            "DISTINCT substr(release_date, 1, 4) AS year",
            where_clause="release_date IS NOT NULL AND release_date != ''",
            suffix="ORDER BY year DESC",
            fetch_all=True,
        )
        return [str(year["year"]) for year in years]


class CardOperations(DatabaseOperationsBaseClass):
    """Provides database operations for Pokémon TCG cards and their properties."""

    def __init__(self, context: Connection) -> None:
        super().__init__("cards", context, ["id", "set_id", "name", "number", "rarity"])

    def __cast_as_cards(
        self, data: list[dict[str, str | int | bytes | None]]
    ) -> list[Card]:
        """Helper function that can cast database responses into type Card."""
        cards: list[Card] = []

        for db_set in data:
            card_id = db_set.get("id")
            set_id = db_set.get("set_id")
            name = db_set.get("name")
            number = db_set.get("number")
            rarity = db_set.get("rarity")

            if (
                not isinstance(card_id, int)
                or not isinstance(set_id, int)
                or not isinstance(name, str)
            ):
                self.logger.warning(
                    f"Cannot create a card from the giving data: {db_set}."
                )
                continue

            cards.append(
                Card(
                    card_id,
                    set_id,
                    name,
                    number if isinstance(number, str) else None,
                    rarity if isinstance(rarity, str) else None,
                )
            )
        return cards

    def get_all(self) -> list[Card]:
        """Retrieve all cards from the database."""
        return self.__cast_as_cards(self.get({}, "*", fetch_all=True))

    def get_in_set(self, set_id: int) -> list[Card]:
        """Retrieve all cards belonging to a specific set."""
        return self.__cast_as_cards(
            self.get(
                {"set_id": set_id},
                "*",
                where_clause="set_id = :set_id",
                suffix="ORDER BY number ASC, name ASC",
                fetch_all=True,
            )
        )

    def get_amount_in_set(self, set_id: int) -> int:
        """Retrieve amount of cards that are in a set."""
        card_amount = self.get(
            {"set_id": set_id}, "COUNT(*)", where_clause="set_id = (:set_id)"
        )[0]["COUNT(*)"]
        return 0 if not card_amount or not isinstance(card_amount, int) else card_amount

    def get_by_card_id(self, card_id: int) -> Card | None:
        """Retrieve a card using its ID."""
        current_card = self.__cast_as_cards(
            self.get({"id": card_id}, "*", where_clause="id = :id")
        )
        return None if not current_card else current_card[0]

    def get_rarities_in_set(self, set_id: int) -> list[str]:
        """Retrieve all rarities that are in a set."""
        rarities = self.get(
            {"set_id": set_id},
            "rarity",
            where_clause="set_id = :set_id AND rarity IS NOT NULL",
            suffix="""GROUP BY rarity
            ORDER BY CASE rarity
                WHEN 'Common' THEN 1
                WHEN 'Uncommon' THEN 2
                WHEN 'Rare' THEN 3
                ELSE 4
            END, MIN(CAST(number AS INTEGER))""",
            fetch_all=True,
        )
        return [str(rarity["rarity"]) for rarity in rarities]


class CardVariantsOperations(DatabaseOperationsBaseClass):
    def __init__(
        self,
        context: Connection,
    ) -> None:
        super().__init__("card_variants", context, ["card_id", "variant"])

    def get_by_card_id(self, card_id: int) -> list[str]:
        """Retrieve all variants belonging to a card in a predefined order."""
        variants = self.get(
            {"card_id": card_id},
            "variant",
            where_clause="card_id = :card_id",
            suffix="""ORDER BY CASE variant
                        WHEN 'Normal' THEN 1
                        WHEN 'Reverse Holofoil' THEN 2
                        WHEN 'Holofoil' THEN 3
                        ELSE 4
                    END, variant ASC
                    """,
            fetch_all=True,
        )

        return [str(variant["variant"]) for variant in variants]

    def get_in_set(self, set_id: int) -> list[str]:
        """Retrieve all unique variant types used within a set."""
        variants = self.get(
            {"set_id": set_id},
            "DISTINCT variant",
            "JOIN cards ON card_variants.card_id = cards.id",
            "cards.set_id = :set_id",
            fetch_all=True,
        )
        return [str(variant["variant"]) for variant in variants]

    def delete_all_by_card_id(self, card_id: int) -> bool:
        return self.delete({"card_id": card_id})


class CardImageOperations(DatabaseOperationsBaseClass):
    """Provides database operations for Pokémon TCG cards and their properties."""

    def __init__(self, context: Connection) -> None:
        super().__init__(
            "card_images", context, ["card_id", "image_data", "content_type"]
        )

    def get_by_card_id(self, card_id: int) -> tuple[bytes, str] | None:
        image = self.get(
            {"card_id": card_id}, "image_data, content_type", "card_id = :card_id"
        )[0]
        if not image:
            return None

        if not isinstance(image["image_data"], bytes) or not isinstance(
            image["content_type"], str
        ):
            return None

        return (image["image_data"], image["content_type"])
