from logging import getLogger
from sqlite3 import Connection, Row
from sqlite3 import Error as db_error

from backend.models import Card, Set


class DatabaseOperations:
    def __init__(
        self, table_name: str, context: Connection, columns: list[str] | tuple[str]
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
        where_clause: str = "1=1",
        suffix: str = "",
        fetch_all: bool = False,
    ) -> list[dict[str, str | int | bytes | None]]:
        """Gets data from table_name using a custom SQL query."""
        cursor = self.context.cursor()
        try:
            cursor.execute(
                f"SELECT {what_clause} FROM {self.table_name} WHERE {where_clause} {suffix}",
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

    def add(self, new_entry: dict[str, str | int | None]) -> bool:
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

    def update(self, update_entry: dict[str, str | int | None]) -> bool:
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

    def delete(self, column_name: str, values: dict[str, str | int]) -> bool:
        """Delete inserted id from the class' table."""
        self.logger.info(
            f"Attempting to delete '{column_name}' from table '{self.table_name}'."
        )

        if column_name not in self.columns:
            self.logger.warning(
                f"Unknown column '{column_name}' for table '{self.table_name}'."
            )
            return False

        cursor = self.context.cursor()

        try:
            cursor.execute(
                f"""DELETE FROM {self.table_name} WHERE {column_name}=(:{column_name})""",
                values,
            )
            self.context.commit()
        except db_error as error:
            self.logger.warning(
                f"Failed to delete '{column_name}' from table '{self.table_name}': {error}."
            )
            return False
        finally:
            cursor.close()

        self.logger.info(
            f"Successfully deleted '{column_name}' from table '{self.table_name}'!"
        )
        return True


class SetOperations(DatabaseOperations):
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

    def cast_as_sets(
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

    def get_sets_by_year(self, year: int) -> list[Set]:
        """Retrieve all sets released in a specific year."""
        return self.cast_as_sets(
            self.get(
                {"year": str(year)}, "*", "substr(release_date, 1, 4) = :year", "", True
            )
        )

    def get_all_sets(self) -> list[Set]:
        """Retrieve all sets from the database."""
        return self.cast_as_sets(self.get({}, "*", fetch_all=True))

    def get_set_by_id(self, set_id: int) -> Set | None:
        """Retrieve set by it's id."""
        current_set = self.cast_as_sets(self.get({"id": set_id}, "*", "id = :id"))
        return None if not current_set else current_set[0]

    def get_set_by_name(self, set_name: str) -> Set | None:
        """Retrieve sets matching a name."""
        current_set = self.cast_as_sets(
            self.get({"name": set_name}, "*", "name = :name")
        )
        return None if not current_set else current_set[0]

    def get_set_years(self) -> list[str]:
        """Retrieve all years of sets that are in the database. Returns a list of strings."""
        years = self.get(
            {},
            "DISTINCT substr(release_date, 1, 4)",
            "release_date IS NOT NULL AND release_date != ''",
            "ORDER BY substr(release_date, 1, 4) DESC",
            True,
        )
        return [str(year["substr(release_date, 1, 4)"]) for year in years]

    def get_rarities_in_set(self, set_id: int) -> list[str]:
        """Retrieve all rarities that are in a set."""
        self.table_name = "cards"
        rarities = self.get(
            {"set_id": set_id},
            "rarity",
            "set_id = :set_id AND rarity IS NOT NULL",
            """GROUP BY rarity
            ORDER BY CASE rarity
                WHEN 'Common' THEN 1
                WHEN 'Uncommon' THEN 2
                WHEN 'Rare' THEN 3
                ELSE 4
            END, MIN(CAST(number AS INTEGER))""",
            True,
        )
        self.table_name = "sets"
        return [str(rarity["rarity"]) for rarity in rarities]


class Card_operations:
    """Provides database operations for Pokémon TCG cards and their properties."""

    def __init__(self, db_context: Connection) -> None:
        self.logger = getLogger(__name__)
        self.db_context = db_context

    def __get_card_by_query(
        self, query: str, values: dict[str, str | int | None]
    ) -> Card | None:
        """Retrieve a single card using a custom SQL query."""
        cursor = self.db_context.cursor()

        cursor.execute(f"""SELECT * FROM cards WHERE {query}""", values)
        card_row = cursor.fetchone()
        cursor.close()

        if card_row is None:
            return None

        return Card(
            card_row["id"],
            card_row["set_id"],
            card_row["name"],
            card_row["number"],
            card_row["rarity"],
        )

    def __get_cards_by_query(
        self, query: str, values: dict[str, str | int | None]
    ) -> list[Card]:
        """Retrieve multiple cards using a custom SQL query."""
        cursor = self.db_context.cursor()

        cursor.execute("""SELECT * FROM cards """ + query, values)
        tuple_list = cursor.fetchall()
        cursor.close()
        card_list: list[Card] = []

        for tpl in tuple_list:
            card_list.append(
                Card(
                    tpl["id"], tpl["set_id"], tpl["name"], tpl["number"], tpl["rarity"]
                )
            )

        return card_list

    def add_card(self, new_card: Card) -> bool:
        """Add a new card to the database."""

        self.logger.info(f"Adding card '{new_card}' to the database.")
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO cards 
            (id, set_id, name, number, rarity)            
            VALUES(:id, :set_id, :name, :number, :rarity)
            """,
                new_card.get_dict(),
            )
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                f"Failed to insert card '{new_card}' into the database: {error}."
            )
            return False

        finally:
            cursor.close()

        self.logger.info(f"Successfully added card '{new_card}' to the database!")
        return True

    def get_all_cards(self) -> list[Card]:
        """Retrieve all cards from the database."""
        return self.__get_cards_by_query("", {})

    def get_cards_by_set(self, set_id: int) -> list[Card]:
        """Retrieve all cards belonging to a specific set."""
        return self.__get_cards_by_query(
            "WHERE set_id = :set_id ORDER BY number ASC, name ASC", {"set_id": set_id}
        )

    def get_cards_amount(self, set_id: int) -> int:
        self.logger.info(
            f"Trying to get the amount of cards that are in set '{set_id}'."
        )
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                "SELECT COUNT(*) FROM cards WHERE set_id = (:set_id)",
                {"set_id": set_id},
            )
            return cursor.fetchone()[0]
        except db_error as error:
            self.logger.warning(
                f"Failed to get card amount from set '{set_id}'. Error: {error}"
            )
            return 0
        finally:
            cursor.close()

    def get_cards_by_rarity(self, rarity: str) -> list[Card]:
        """Retrieve all cards with a specific rarity."""
        return self.__get_cards_by_query("WHERE rarity = :rarity", {"rarity": rarity})

    def get_card_by_id(self, id: int) -> Card | None:
        """Retrieve a card using its ID."""
        return self.__get_card_by_query("id = :id", {"id": id})

    def update_card(self, updated_card: Card) -> bool:
        """Update an existing card in the database."""

        self.logger.info(f"Updating {updated_card} in the database.")
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                """
                UPDATE cards SET
                    set_id = :set_id,
                    name = :name,
                    number = :number,
                    rarity = :rarity
                WHERE id = :id""",
                {
                    "id": updated_card.id,
                    "set_id": updated_card.set_id,
                    "name": updated_card.name,
                    "number": updated_card.number,
                    "rarity": updated_card.rarity,
                },
            )
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                f"Failed to update card '{updated_card}' in the database: {error}."
            )
            return False

        finally:
            cursor.close()

        self.logger.info(f"Successfully update card '{updated_card}' in the database!")
        return True

    def delete_card(self, card_id: int) -> bool:
        """Delete a card from the database."""

        self.logger.info(f"Deleting card '{card_id}' from the database.")
        cursor = self.db_context.cursor()

        try:
            cursor.execute("""DELETE FROM cards WHERE id=(:id)""", {"id": card_id})
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                f"Failed to delete card '{card_id}' from the database: {error}."
            )
            return False

        finally:
            cursor.close()

        self.logger.info(f"Successfully deleted card '{card_id}' from the database!")
        return True

    # Card variant operations starts here
    def __get_variants_by_query(
        self, query: str, values: dict[str, str | int | None]
    ) -> list[str]:
        """Retrieve card variants using a custom SQL query."""
        cursor = self.db_context.cursor()

        cursor.execute(query, values)
        tuple_list = cursor.fetchall()
        cursor.close()
        variants_list: list[str] = []

        for tpl in tuple_list:
            variants_list.append(tpl["variant"])

        return variants_list

    def add_variant(self, card_id: int, variant: str) -> bool:
        """Add a variant to a card in the database."""

        self.logger.info(
            f"Adding card variant '{variant}' of card '{card_id}' to the database."
        )
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO card_variants (card_id, variant) VALUES (:card_id, :variant)""",
                {"card_id": card_id, "variant": variant},
            )
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                f"Failed to add card variant '{variant}' of card '{card_id}' to the database: {error}."
            )
            return False

        finally:
            cursor.close()

        self.logger.info(
            f"Successfully added card variant '{variant}' of card '{card_id}' to the database."
        )
        return True

    def get_variants(self, card_id: int) -> list[str]:
        """Retrieve all variants belonging to a card in a predefined order."""
        return self.__get_variants_by_query(
            """
            SELECT variant
            FROM card_variants
            WHERE card_id = :card_id
            ORDER BY CASE variant
                WHEN 'Normal' THEN 1
                WHEN 'Reverse Holofoil' THEN 2
                WHEN 'Holofoil' THEN 3
                ELSE 4
            END, variant ASC
            """,
            {"card_id": card_id},
        )

    def get_variant_types_in_set(self, set_id: int) -> list[str]:
        """Retrieve all unique variant types used within a set."""
        return self.__get_variants_by_query(
            """SELECT DISTINCT variant FROM card_variants
                                            JOIN cards ON card_variants.card_id = cards.id
                                            WHERE cards.set_id = :set_id""",
            {"set_id": set_id},
        )

    def delete_variant(self, card_id: int, variant: str) -> bool:
        """Delete a specific variant from a card."""

        self.logger.info("Deleting variant '%s' from card '%s'", variant, card_id)
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                """DELETE FROM card_variants WHERE (card_id, variant)=(:card_id, :variant)""",
                {"card_id": card_id, "variant": variant},
            )
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                "Failed to delete variant '%s' of card '%s' from the database: '%s'.",
                variant,
                card_id,
                error,
            )
            return False

        finally:
            cursor.close()

        self.logger.info(
            "Successfully deleted variant '%s' of card '%s' from the database.",
            variant,
            card_id,
        )
        return True

    def delete_variants(self, card_id: int) -> bool:
        """Delete all variants belonging to a card."""
        variants = self.get_variants(card_id)
        if not variants:
            return True

        for variant in variants:
            if not self.delete_variant(card_id, variant):
                return False

        return True

    # Card image operations
    def save_image(self, card_id: int, image_data: bytes, content_type: str) -> bool:
        """Save a card image to the database."""

        self.logger.info(f"Adding card image of card '{card_id}' to the database.")
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO card_images (card_id, image_data, content_type) VALUES (:card_id, :image_data, :content_type)""",
                {
                    "card_id": card_id,
                    "image_data": image_data,
                    "content_type": content_type,
                },
            )
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                f"Failed to add image of card '{card_id}' to the database: {error}."
            )
            return False

        finally:
            cursor.close()

        self.logger.info(f"Successfully added image of card {card_id} to the database.")
        return True

    def get_image(self, card_id: int) -> tuple[bytes, str] | None:
        """Retrieve a card image and its content type."""
        cursor = self.db_context.cursor()

        cursor.execute(
            """SELECT * FROM card_images WHERE card_id = :card_id""",
            {"card_id": card_id},
        )
        image = cursor.fetchone()
        cursor.close()

        if image is None:
            return None

        if image["image_data"] is None:
            return None

        return image["image_data"], image["content_type"]

    def delete_image(self, card_id: int) -> bool:
        """Delete a card image from the database."""

        self.logger.info(f"Deleting image of card '{card_id}' from the database.")
        cursor = self.db_context.cursor()

        try:
            cursor.execute(
                """DELETE FROM card_images WHERE card_id=:card_id""",
                {"card_id": card_id},
            )
            self.db_context.commit()

        except db_error as error:
            self.logger.warning(
                f"Failed to delete image of card '{card_id}' from the database: {error}."
            )
            return False

        finally:
            cursor.close()

        self.logger.info(
            f"Successfully deleted image of card '{card_id}' from the database"
        )
        return True

    def delete_card_and_properties(self, card_id: int) -> bool:
        """Delete a card and all associated images and variants."""
        if self.get_image(card_id) is not None:
            if not self.delete_image(card_id):
                return False

        if self.get_variants(card_id):
            if not self.delete_variants(card_id):
                return False

        if self.get_card_by_id(card_id) is not None:
            if not self.delete_card(card_id):
                return False

        return True
