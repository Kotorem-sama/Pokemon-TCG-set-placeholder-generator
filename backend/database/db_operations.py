"""Database access layer: generic and per-table operations on the SQLite database.

Use `DatabaseOperations` as the entry point. It wraps a `Database` from
`db_setup` and exposes one operations object per table.
"""

from logging import getLogger
from sqlite3 import Connection, Row
from sqlite3 import Error as db_error

from backend.database.db_setup import Database
from backend.models import Card, Set


class DatabaseOperations:
    """Single entry point for all database access.

    Groups one operations class per table, so callers can use for example
    `database.sets.get_by_id(1)` or `database.cards.get_in_set(1)`.
    All of them share the same SQLite connection.

    Attributes:
        database: The `Database` this object works on.
        sets: Operations for the `sets` table.
        cards: Operations for the `cards` table.
        variants: Operations for the `card_variants` table.
        images: Operations for the `card_images` table.
    """

    def __init__(self, database: Database) -> None:
        """Create the per-table operations on the connection of `database`.

        Args:
            database: An initialised database. Its connection is shared by
                every operations object. This class does not close it.
        """
        self.database = database
        self.sets = SetOperations(database.context)
        self.cards = CardOperations(database.context)
        self.variants = CardVariantsOperations(database.context)
        self.images = CardImageOperations(database.context)


class DatabaseOperationsBaseClass:
    """Generic get/add/update/delete operations for a single table.

    Table-specific classes inherit from this class and add their own typed
    helper methods. Table and column names are inserted into the SQL text
    (SQLite cannot use placeholders for names), so they are only ever taken
    from this class' own allow-list and constructor arguments, never from
    user input. Actual values are always passed as named placeholders
    (`:name`) so SQLite escapes them.
    """

    def __init__(
        self,
        table_name: str,
        context: Connection,
        columns: list[str],
        primary_key_columns: list[str],
    ) -> None:
        """Bind the operations to one table.

        Args:
            table_name: Name of the table. Must be one of the known tables.
            context: Open SQLite connection. Its row factory must be
                `sqlite3.Row`, so rows can be converted to dictionaries.
            columns: All column names of the table, used by add/update/delete.
            primary_key_columns: The columns that make up the primary key of the table.

        Raises:
            ValueError: If `table_name` is not a known table.
        """
        if table_name not in ["sets", "cards", "card_variants", "card_images"]:
            raise ValueError(f"Unknown table: {table_name}")

        self.logger = getLogger(__name__)
        self.table_name = table_name
        self.context = context
        # Maps each column name to its named placeholder, e.g. {"name": ":name"}.
        self.columns: dict[str, str] = {column: f":{column}" for column in columns}
        self.primary_key_columns = primary_key_columns

    def get(
        self,
        values: dict[str, str | int],
        what_clause: str,
        join_clause: str = "",
        where_clause: str = "1=1",
        suffix: str = "",
        fetch_all: bool = False,
    ) -> list[dict[str, str | int | bytes | None]]:
        """Select data from this table using a custom query.

        Args:
            values: Values for the named placeholders used in the clauses,
                e.g. `{"id": 5}` for `where_clause="id = :id"`.
            what_clause: The columns or expressions to select, e.g. `"*"`.
            join_clause: Optional JOIN text, placed after the table name.
            where_clause: Filter condition. Selects every row by default.
            suffix: Text placed after the WHERE clause, e.g. `ORDER BY ...`.
            fetch_all: Return every matching row. If False, only the first
                matching row is returned.

        Returns:
            One dictionary per row, keyed by column name or alias. The list is
            empty when nothing matched or when the query failed.
        """
        cursor = self.context.cursor()
        try:
            cursor.execute(
                f"SELECT {what_clause} FROM {self.table_name} {join_clause} WHERE {where_clause} {suffix}",
                values,
            )
            result_rows: list[Row] = (
                cursor.fetchall()
                if fetch_all
                # fetchone() returns None when there is no row.
                else [row for row in [cursor.fetchone()] if row]
            )
            return [dict(row) for row in result_rows]
        finally:
            cursor.close()

    def add(self, new_entry: dict[str, str | int | bytes | None]) -> bool:
        """Insert a new row into this table.

        Args:
            new_entry: Column name to value. Must contain every column of the
                table, otherwise the insert fails.

        Returns:
            True if the row was added, False if the insert failed (for example
            because the id already exists).
        """
        self.logger.info(f"Adding '{new_entry}' to the table '{self.table_name}'.")
        cursor = self.context.cursor()

        try:
            column_names = ", ".join(self.columns)
            placeholders = ", ".join(self.columns.values())
            cursor.execute(
                f"""INSERT INTO {self.table_name} ({column_names})
            VALUES({placeholders})""",
                new_entry,
            )

            self.logger.info(
                f"Successfully added '{new_entry}' to the table '{self.table_name}'!"
            )
            return True

        except db_error as error:
            self.logger.warning(
                f"Failed to insert '{new_entry}' into the table '{self.table_name}': {error}."
            )
            self.context.rollback()
            return False

        finally:
            cursor.close()

    def update(self, update_entry: dict[str, str | int | bytes | None]) -> bool:
        """Update a row identified by this table's primary key.

        Primary-key columns identify the row and are not changed. Tables with
        no non-key columns cannot be updated with this method.

        Args:
            update_entry: Column name to value. Must contain every column of
                the table, including the primary key.

        Returns:
            True if a row was updated. False if columns are missing, no row
            matched the primary key, or the update failed.
        """
        primary_keys = self.primary_key_columns
        update_columns = [
            column for column in self.columns if column not in primary_keys
        ]

        if not update_columns or any(
            column not in update_entry for column in self.columns
        ):
            return False

        assignments = ", ".join(f"{column} = :{column}" for column in update_columns)
        where_clause = " AND ".join(f"{column} = :{column}" for column in primary_keys)

        cursor = self.context.cursor()
        try:
            cursor.execute(
                f"UPDATE {self.table_name} SET {assignments} WHERE {where_clause}",
                update_entry,
            )
            self.context.commit()
            return cursor.rowcount > 0
        except db_error as error:
            self.logger.warning(
                f"Failed to update '{update_entry}' in '{self.table_name}': {error}."
            )
            self.context.rollback()
            return False
        finally:
            cursor.close()

    def delete(self, values: dict[str, str | int | bytes | None]) -> bool:
        """Delete the rows that match every given column value.

        Args:
            values: Column name to value, combined with AND. For example
                `{"id": 5}` or `{"card_id": 3, "variant": "Normal"}`. Must not
                be empty, so a call can never delete a whole table by accident.

        Returns:
            True if at least one row was deleted. False if the keys are
            invalid, nothing matched, or the delete failed.
        """
        self.logger.info(
            f"Attempting to delete '{values}' from table '{self.table_name}'."
        )

        # Column names are inserted into the SQL text below, so only accept
        # names that belong to this table.
        if not values or any(column not in self.columns for column in values):
            self.logger.warning(
                f"Invalid delete keys {list(values)} for '{self.table_name}'."
            )
            return False

        where_clause = " AND ".join(f"{column} = :{column}" for column in values)

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
            self.context.rollback()
            return False
        finally:
            cursor.close()


class SetOperations(DatabaseOperationsBaseClass):
    """Provides database operations for Pokémon TCG sets.

    Rows are returned as `Set` objects.
    """

    def __init__(self, context: Connection) -> None:
        """Bind to the `sets` table.

        Args:
            context: Open SQLite connection with `sqlite3.Row` as row factory.
        """
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
            ["id"],
        )

    def __cast_as_sets(
        self, data: list[dict[str, str | int | bytes | None]]
    ) -> list[Set]:
        """Convert database rows into `Set` objects.

        Args:
            data: Row dictionaries as returned by `get`.

        Returns:
            The valid rows as `Set` objects. Rows that miss a required field
            (id, name, slug, sync_complete) are logged and skipped. The
            optional fields become None if they are not of the expected type.
        """
        converted_sets: list[Set] = []

        for set_row in data:
            set_id = set_row.get("id")
            name = set_row.get("name")
            slug = set_row.get("slug")
            abbreviation = set_row.get("abbreviation")
            release_date = set_row.get("release_date")
            card_count = set_row.get("card_count")
            sync_complete = set_row.get("sync_complete")

            if (
                not isinstance(set_id, int)
                or not isinstance(name, str)
                or not isinstance(slug, str)
                or not isinstance(sync_complete, int)
            ):
                self.logger.warning(
                    f"Cannot create a set from the giving data: {set_row}."
                )
                continue

            converted_sets.append(
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
        return converted_sets

    def get_by_year(self, year: int) -> list[Set]:
        """Retrieve all sets released in a specific year.

        The year is compared as text with the first four characters of
        `release_date` (stored as e.g. '2026-01-01'), so it is passed as a
        string.

        Args:
            year: Four-digit release year, e.g. 2026.

        Returns:
            The matching sets, or an empty list if there are none.
        """
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
        """Retrieve a set by its id.

        Args:
            set_id: Id of the set.

        Returns:
            The set, or None if it does not exist.
        """
        matching_sets = self.__cast_as_sets(
            self.get({"id": set_id}, "*", where_clause="id = :id")
        )
        return matching_sets[0] if matching_sets else None

    def get_by_name(self, set_name: str) -> list[Set]:
        """Retrieve the set with exactly this name.

        Args:
            set_name: Set name (case-insensitive).

        Returns:
            The matching sets, or an empty list if there are none.
        """
        matching_sets = self.__cast_as_sets(
            self.get(
                {"name": f"%{set_name.lower()}%"},
                "*",
                where_clause="name LIKE :name",
                fetch_all=True,
            )
        )
        return matching_sets if matching_sets else []

    def get_release_date_years(self) -> list[str]:
        """Retrieve every release year that has a set, newest first.

        Sets without a release date are ignored. Years are returned as strings,
        e.g. ['2026', '2025'].
        """
        year_rows = self.get(
            {},
            "DISTINCT substr(release_date, 1, 4) AS year",
            where_clause="release_date IS NOT NULL AND release_date != ''",
            suffix="ORDER BY year DESC",
            fetch_all=True,
        )
        return [str(year_row["year"]) for year_row in year_rows]


class CardOperations(DatabaseOperationsBaseClass):
    """Provides database operations for Pokémon TCG cards and their properties.

    Rows are returned as `Card` objects.
    """

    def __init__(self, context: Connection) -> None:
        """Bind to the `cards` table.

        Args:
            context: Open SQLite connection with `sqlite3.Row` as row factory.
        """
        super().__init__(
            "cards", context, ["id", "set_id", "name", "number", "rarity"], ["id"]
        )

    def __cast_as_cards(
        self, data: list[dict[str, str | int | bytes | None]]
    ) -> list[Card]:
        """Convert database rows into `Card` objects.

        Args:
            data: Row dictionaries as returned by `get`.

        Returns:
            The valid rows as `Card` objects. Rows that miss a required field
            (id, set_id, name) are logged and skipped. `number` and `rarity`
            become None if they are not text.
        """
        converted_cards: list[Card] = []

        for card_row in data:
            card_id = card_row.get("id")
            set_id = card_row.get("set_id")
            name = card_row.get("name")
            number = card_row.get("number")
            rarity = card_row.get("rarity")

            if (
                not isinstance(card_id, int)
                or not isinstance(set_id, int)
                or not isinstance(name, str)
            ):
                self.logger.warning(
                    f"Cannot create a card from the giving data: {card_row}."
                )
                continue

            converted_cards.append(
                Card(
                    card_id,
                    set_id,
                    name,
                    number if isinstance(number, str) else None,
                    rarity if isinstance(rarity, str) else None,
                )
            )
        return converted_cards

    def get_all(self) -> list[Card]:
        """Retrieve all cards from the database."""
        return self.__cast_as_cards(self.get({}, "*", fetch_all=True))

    def get_in_set(self, set_id: int) -> list[Card]:
        """Retrieve all cards belonging to a specific set, ordered by number.

        Args:
            set_id: Id of the set.

        Returns:
            The cards of the set, or an empty list if there are none.
        """
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
        """Count the cards that are stored for a set.

        Args:
            set_id: Id of the set.

        Returns:
            The number of stored cards, or 0 if there are none.
        """
        count_rows = self.get(
            {"set_id": set_id}, "COUNT(*) AS total", where_clause="set_id = :set_id"
        )
        # An empty list means the query itself failed.
        if not count_rows:
            return 0

        card_total = count_rows[0]["total"]
        return card_total if isinstance(card_total, int) else 0

    def get_by_id(self, card_id: int) -> Card | None:
        """Retrieve a card by its id.

        Args:
            card_id: Id of the card.

        Returns:
            The card, or None if it does not exist.
        """
        matching_cards = self.__cast_as_cards(
            self.get({"id": card_id}, "*", where_clause="id = :id")
        )
        return matching_cards[0] if matching_cards else None

    def get_rarities_in_set(self, set_id: int) -> list[str]:
        """Retrieve the distinct rarities used in a set.

        Common, Uncommon and Rare come first, in that order. Other rarities
        follow, ordered by the lowest card number that has that rarity.

        Args:
            set_id: Id of the set.

        Returns:
            The rarity names in that order. Cards without a rarity are ignored.
        """
        rarity_rows = self.get(
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
        return [str(rarity_row["rarity"]) for rarity_row in rarity_rows]


class CardVariantsOperations(DatabaseOperationsBaseClass):
    """Provides database operations for the variants of a card.

    A variant is a printing of a card, such as 'Normal', 'Holofoil' or
    'Reverse Holofoil'. Each card can have several variants.
    """

    def __init__(
        self,
        context: Connection,
    ) -> None:
        """Bind to the `card_variants` table.

        Args:
            context: Open SQLite connection with `sqlite3.Row` as row factory.
        """
        super().__init__(
            "card_variants", context, ["card_id", "variant"], ["card_id", "variant"]
        )

    def get_by_card_id(self, card_id: int) -> list[str]:
        """Retrieve all variants belonging to a card in a predefined order.

        The order is Normal, Reverse Holofoil, Holofoil, then any other
        variant alphabetically.

        Args:
            card_id: Id of the card.

        Returns:
            The variant names, or an empty list if the card has none.
        """
        variant_rows = self.get(
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

        return [str(variant_row["variant"]) for variant_row in variant_rows]

    def get_in_set(self, set_id: int) -> list[str]:
        """Retrieve all unique variant types used within a set.

        Args:
            set_id: Id of the set.

        Returns:
            The distinct variant names of all cards in the set, unordered.
        """
        # The set id is stored on the cards table, so join to reach it.
        variant_rows = self.get(
            {"set_id": set_id},
            "DISTINCT variant",
            join_clause="JOIN cards ON card_variants.card_id = cards.id",
            where_clause="cards.set_id = :set_id",
            fetch_all=True,
        )
        return [str(variant_row["variant"]) for variant_row in variant_rows]

    def delete_all_by_card_id(self, card_id: int) -> bool:
        """Delete every variant of a card.

        Args:
            card_id: Id of the card.

        Returns:
            True if any variant was deleted, otherwise False.
        """
        return self.delete({"card_id": card_id})


class CardImageOperations(DatabaseOperationsBaseClass):
    """Provides database operations for the downloaded image of each card.

    Each card has at most one image, stored as raw bytes with its MIME type.
    """

    def __init__(self, context: Connection) -> None:
        """Bind to the `card_images` table.

        Args:
            context: Open SQLite connection with `sqlite3.Row` as row factory.
        """
        super().__init__(
            "card_images",
            context,
            ["card_id", "image_data", "content_type"],
            ["card_id"],
        )

    def get_by_card_id(self, card_id: int) -> tuple[bytes, str] | None:
        """Retrieve the stored image of a card.

        Args:
            card_id: Id of the card.

        Returns:
            A tuple of (image bytes, MIME type such as 'image/png'), or None if
            the card has no stored image or the stored data is invalid.
        """
        image_rows = self.get(
            {"card_id": card_id},
            "image_data, content_type",
            where_clause="card_id = :card_id",
        )
        if not image_rows:
            return None

        image_row = image_rows[0]

        if not isinstance(image_row["image_data"], bytes) or not isinstance(
            image_row["content_type"], str
        ):
            return None

        return (image_row["image_data"], image_row["content_type"])
