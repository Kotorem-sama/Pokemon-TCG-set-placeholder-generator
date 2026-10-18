from logging import getLogger
from sqlite3 import Connection, Row
from sqlite3 import Error as db_error

from backend.models import Card, Set


class DatabaseOperations:
    """Single entry point for all database access.

    Creates table-specific operation helpers for sets, cards, card variants,
    and card images. Each helper shares the supplied SQLite connection.
    """

    def __init__(self, context: Connection) -> None:
        """Create table-specific helpers bound to one SQLite connection.

        Args:
            context: An open SQLite connection configured with ``sqlite3.Row``
                as its row factory.
        """
        self.sets = SetOperations(context)
        self.cards = CardOperations(context)
        self.variants = CardVariantsOperations(context)
        self.images = CardImageOperations(context)


class DatabaseOperationsBaseClass:
    """Provide generic CRUD operations for one allow-listed table.

    Table-specific operation classes inherit from this class and add typed
    query helpers. SQL values use named parameters; SQL structure such as
    selected columns and clauses is interpolated and must therefore come from
    trusted application code, not user input.
    """

    def __init__(
        self, table_name: str, context: Connection, columns: list[str]
    ) -> None:
        """Bind the operations to one table.

        Args:
            table_name: One of ``sets``, ``cards``, ``card_variants``, or
                ``card_images``.
            context: Open SQLite connection. Its row factory must be
                `sqlite3.Row`, so rows can be converted to dictionaries.
            columns: Table columns used to construct inserts and updates.

        Raises:
            ValueError: If ``table_name`` is not an allow-listed table.
        """
        if table_name not in ["sets", "cards", "card_variants", "card_images"]:
            raise ValueError(f"Unknown table: {table_name}")

        self.logger = getLogger(__name__)
        self.table_name = table_name
        self.context = context
        # Maps each column name to its named placeholder, e.g. {"name": ":name"}.
        self.columns: dict[str, str] = {column: f":{column}" for column in columns}

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
            Dictionaries keyed by the selected column names or aliases. Returns
            an empty list when the query succeeds with no matches. When
            ``fetch_all`` is False, the result contains at most one row.

        Notes:
            SQLite errors are logged and converted to an empty list, so this
            method does not distinguish a failed query from a successful query
            with no matching rows.
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
        except db_error:
            self.logger.exception("Failed to get information from database.")
            return []
        finally:
            cursor.close()

    def add(self, new_entry: dict[str, str | int | bytes | None]) -> bool:
        """Insert a new row into this table.

        Args:
            new_entry: Column name to value. Must contain every column of the
                table, otherwise the insert fails.

        Returns:
            True if the insert succeeded. False if SQLite rejected it, for
            example because a primary key or unique value already exists.

        Notes:
            A successful insert is committed by this method. A SQLite error is
            logged and reported as False; this implementation does not
            explicitly roll back in the failure path.
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
        """Update an existing row identified by its ``id``.

        Args:
            update_entry: Mapping of every table column to its new value,
                including ``id``. The ``id`` identifies the row and is not
                modified.

        Returns:
            True if at least one row was updated; otherwise False. This
            implementation expects an ``id`` column and is not suitable for
            tables keyed by other columns.

        Notes:
            Successful updates are committed. SQLite errors are logged and
            reported as False; this implementation does not explicitly roll
            back in the failure path.
        """
        self.logger.info(f"Updating {update_entry} to the table {self.table_name}.")
        cursor = self.context.cursor()
        try:
            # Builds e.g. "name = :name, slug = :slug". The id is not overwritten.
            assignments = ", ".join(
                f"{column} = {placeholder}"
                for column, placeholder in self.columns.items()
                if column != "id"
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
        """Delete rows matching all supplied column-value pairs.

        Args:
            values: Non-empty mapping of valid table columns to values. The
                conditions are combined with ``AND``; for example,
                ``{"id": 5}`` or ``{"card_id": 3, "variant": "Normal"}``.

        Returns:
            True if at least one row was deleted. False if ``values`` is empty,
            contains an unknown column, no rows matched, or SQLite reported an
            error.

        Notes:
            Successful deletes are committed. Invalid keys and SQLite errors
            are logged; this implementation does not explicitly roll back on
            a database error.
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
            return False
        finally:
            cursor.close()


class SetOperations(DatabaseOperationsBaseClass):
    """Query and modify Pokémon TCG set records."""

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
        """Convert valid database rows into ``Set`` objects.

        Rows missing required fields or containing invalid required types are
        logged and skipped. Optional values of unexpected types are converted
        to ``None``.
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
        """Return all sets in the database, or an empty list if none exist."""
        return self.__cast_as_sets(self.get({}, "*", fetch_all=True))

    def get_by_id(self, set_id: int) -> Set | None:
        """Return the set with this ID, or ``None`` if no row is returned."""
        matching_sets = self.__cast_as_sets(
            self.get({"id": set_id}, "*", where_clause="id = :id")
        )
        return matching_sets[0] if matching_sets else None

    def get_by_name(self, set_name: str) -> Set | None:
        """Return the set matching this name, or ``None`` if no row is returned."""
        matching_sets = self.__cast_as_sets(
            self.get({"name": set_name}, "*", where_clause="name = :name")
        )
        return matching_sets[0] if matching_sets else None

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
    """Query and modify Pokémon TCG card records."""

    def __init__(self, context: Connection) -> None:
        super().__init__("cards", context, ["id", "set_id", "name", "number", "rarity"])

    def __cast_as_cards(
        self, data: list[dict[str, str | int | bytes | None]]
    ) -> list[Card]:
        """Convert valid database rows into ``Card`` objects.

        Rows missing required fields or containing invalid required types are
        logged and skipped. ``number`` and ``rarity`` become ``None`` if their
        values are not strings.
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
        """Return all cards in the database, or an empty list if none exist."""
        return self.__cast_as_cards(self.get({}, "*", fetch_all=True))

    def get_in_set(self, set_id: int) -> list[Card]:
        """Return a set's cards ordered by number and then name."""
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
        """Return the number of card rows belonging to a set.

        Returns zero when no count row is available, including when the
        underlying generic query returned no rows after an SQLite error.
        """
        count_rows = self.get(
            {"set_id": set_id}, "COUNT(*) AS total", where_clause="set_id = :set_id"
        )
        # COUNT(*) normally returns one row, including when the count is zero.
        # The generic getter can return an empty list when its query fails.
        if not count_rows:
            return 0

        card_total = count_rows[0]["total"]
        return card_total if isinstance(card_total, int) else 0

    def get_by_id(self, card_id: int) -> Card | None:
        """Return the card with this ID, or ``None`` if no row is returned."""
        matching_cards = self.__cast_as_cards(
            self.get({"id": card_id}, "*", where_clause="id = :id")
        )
        return matching_cards[0] if matching_cards else None

    def get_rarities_in_set(self, set_id: int) -> list[str]:
        """Retrieve the distinct rarities used in a set.

        Common, Uncommon and Rare come first, in that order. Other rarities
        follow, ordered by the lowest card number that has that rarity.
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
    """Query and modify card-variant records.

    A variant represents a printing such as ``Normal``, ``Holofoil``, or
    ``Reverse Holofoil``. A card may have multiple variant records.
    """

    def __init__(
        self,
        context: Connection,
    ) -> None:
        super().__init__("card_variants", context, ["card_id", "variant"])

    def get_by_card_id(self, card_id: int) -> list[str]:
        """Return a card's variants in the application's preferred order."""
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
        """Return the distinct variant names used by cards in a set."""
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
        """Delete all variant rows for a card.

        Returns True if one or more rows were deleted; otherwise False.
        """
        return self.delete({"card_id": card_id})


class CardImageOperations(DatabaseOperationsBaseClass):
    """Query and modify downloaded image records for cards."""

    def __init__(self, context: Connection) -> None:
        super().__init__(
            "card_images", context, ["card_id", "image_data", "content_type"]
        )

    def get_by_card_id(self, card_id: int) -> tuple[bytes, str] | None:
        """Return a card's stored image data and MIME type.

        Returns:
            A tuple ``(image_bytes, content_type)`` when valid image bytes and a
            string content type are stored. Returns ``None`` when no row exists
            or either value has an unexpected type.
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
