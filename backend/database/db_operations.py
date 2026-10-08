import logging
from sqlite3 import Connection
from sqlite3 import Error as db_error

from classes import Card, Set


class Set_operations:
    """Provides database operations for Pokémon TCG sets."""

    def __get_set_from_query(
        self, db_context: Connection, query: str, values: dict[str, str | int | None]
    ) -> Set | None:
        """Retrieve a single set using a custom SQL query."""
        cursor = db_context.cursor()

        cursor.execute(f"""SELECT * FROM sets WHERE {query}""", values)
        set_row = cursor.fetchone()
        if set_row is None:
            return None

        return Set(
            set_row["id"],
            set_row["name"],
            set_row["slug"],
            set_row["abbreviation"],
            set_row["release_date"],
            set_row["card_count"],
            set_row["sync_complete"],
        )

    def __get_sets_from_query(
        self, db_context: Connection, query: str, values: dict[str, str | int | None]
    ) -> list[Set]:
        """Retrieve multiple sets using a custom SQL query."""
        cursor = db_context.cursor()

        cursor.execute(f"SELECT * FROM sets {query} ORDER BY release_date DESC", values)
        tuple_list = cursor.fetchall()
        set_list: list[Set] = []

        for tpl in tuple_list:
            set_list.append(
                Set(
                    tpl["id"],
                    tpl["name"],
                    tpl["slug"],
                    tpl["abbreviation"],
                    tpl["release_date"],
                    tpl["card_count"],
                    tpl["sync_complete"],
                )
            )

        return set_list

    def add_set(self, db_context: Connection, new_set: Set) -> bool:
        """Add a new set to the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Adding set {new_set} to the database.")

        cursor = db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO sets 
            (id, name, slug, abbreviation, release_date, card_count, sync_complete)            
            VALUES(:id, :name, :slug, :abbreviation, :release_date, :card_count, :sync_complete)""",
                new_set.get_dict(),
            )
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to insert set '{new_set}' into the database: {error}.")
            return False

        logger.info(f"Succesfully added set '{new_set}' to the database!")
        return True

    def get_sets_by_year(self, db_context: Connection, year: int) -> list[Set]:
        """Retrieve all sets released in a specific year."""
        return self.__get_sets_from_query(
            db_context,
            """WHERE 
            strftime('%Y', release_date) = :year""",
            {"year": str(year)},
        )

    def get_all_sets(self, db_context: Connection) -> list[Set]:
        """Retrieve all sets from the database."""
        return self.__get_sets_from_query(db_context, "", {})

    def get_set_by_id(self, db_context: Connection, id: int) -> Set | None:
        """Retrieve a set using its ID."""
        return self.__get_set_from_query(db_context, "id = :id", {"id": id})

    def get_set_by_slug(self, db_context: Connection, slug: str) -> Set | None:
        """Retrieve a set using its slug."""
        return self.__get_set_from_query(db_context, "slug = :slug", {"slug": slug})

    def get_set_by_name(self, db_context: Connection, name: str) -> Set | None:
        """Retrieve sets matching a name."""
        return self.__get_set_from_query(
            db_context, "name LIKE :name", {"name": f"%{name}%"}
        )

    def update_set(self, db_context: Connection, updated_set: Set) -> bool:
        """Update an existing set in the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Updating set {updated_set} to the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute(
                """
                UPDATE sets SET
                    name = :name,
                    slug = :slug,
                    abbreviation = :abbreviation,
                    release_date = :release_date,
                    card_count = :card_count,
                    sync_complete = :sync_complete
                WHERE id = :id""",
                {
                    "id": updated_set.id,
                    "name": updated_set.name,
                    "slug": updated_set.slug,
                    "abbreviation": updated_set.abbreviation,
                    "release_date": updated_set.release_date,
                    "card_count": updated_set.card_count,
                    "sync_complete": updated_set.sync_complete,
                },
            )

            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to update set '{updated_set}' in the database: {error}.")
            return False

        logger.info(f"Succesfully updated set '{updated_set}' in the database.")
        return True

    def delete_set(self, db_context: Connection, set_id: int) -> bool:
        """Delete a set from the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting to delete set '{set_id}' from the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute("""DELETE FROM sets WHERE id=(:id)""", {"id": set_id})
            db_context.commit()
        except db_error as error:
            logger.warning(f"Failed to delete set '{set_id}' from the database: {error}.")
            return False

        logger.info(f"Succesfully deleted the set '{set_id}' from the database!")
        return True

    def is_set_complete(self, db_context: Connection, current_set: Set) -> bool:
        """Check whether all cards belonging to a set have been stored."""
        cards_in_set = Card_operations().get_cards_by_set(db_context, current_set.id)

        return len(cards_in_set) == current_set.card_count


class Card_operations:
    """Provides database operations for Pokémon TCG cards and their properties."""

    def __get_card_by_query(
        self, db_context: Connection, query: str, values: dict[str, str | int | None]
    ) -> Card | None:
        """Retrieve a single card using a custom SQL query."""
        cursor = db_context.cursor()

        cursor.execute(f"""SELECT * FROM cards WHERE {query}""", values)
        card_row = cursor.fetchone()

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
        self, db_context: Connection, query: str, values: dict[str, str | int | None]
    ) -> list[Card]:
        """Retrieve multiple cards using a custom SQL query."""
        cursor = db_context.cursor()

        cursor.execute(f"""SELECT * FROM cards {query}""", values)
        tuple_list = cursor.fetchall()
        card_list: list[Card] = []

        for tpl in tuple_list:
            card_list.append(
                Card(
                    tpl["id"], tpl["set_id"], tpl["name"], tpl["number"], tpl["rarity"]
                )
            )

        return card_list

    def add_card(self, db_context: Connection, new_card: Card) -> bool:
        """Add a new card to the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Adding card '{new_card}' to the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO cards 
            (id, set_id, name, number, rarity)            
            VALUES(:id, :set_id, :name, :number, :rarity)
            """,
                new_card.get_dict(),
            )
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to insert card '{new_card}' into the database: {error}.")
            return False

        logger.info(f"Succesfully added card '{new_card}' to the database!")
        return True

    def get_all_cards(self, db_context: Connection) -> list[Card]:
        """Retrieve all cards from the database."""
        return self.__get_cards_by_query(db_context, "", {})

    def get_cards_by_set(self, db_context: Connection, set_id: int) -> list[Card]:
        """Retrieve all cards belonging to a specific set."""
        return self.__get_cards_by_query(
            db_context, "WHERE set_id = :set_id", {"set_id": set_id}
        )

    def get_cards_by_rarity(self, db_context: Connection, rarity: str) -> list[Card]:
        """Retrieve all cards with a specific rarity."""
        return self.__get_cards_by_query(
            db_context, "WHERE rarity = :rarity", {"rarity": rarity}
        )

    def get_card_by_id(self, db_context: Connection, id: int) -> Card | None:
        """Retrieve a card using its ID."""
        return self.__get_card_by_query(db_context, "id = :id", {"id": id})

    def update_card(self, db_context: Connection, updated_card: Card) -> bool:
        """Update an existing card in the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Updating {updated_card} in the database.")
        cursor = db_context.cursor()

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
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to update card '{updated_card}' in the database: {error}.")
            return False

        logger.info(f"Succesfully update card '{updated_card}' in the database!")
        return True

    def delete_card(self, db_context: Connection, card_id: int) -> bool:
        """Delete a card from the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Deleting card '{card_id}' from the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute("""DELETE FROM cards WHERE id=(:id)""", {"id": card_id})
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to delete card '{card_id}' from the database: {error}.")
            return False

        logger.info(f"Succesfully deleted card '{card_id}' from the database!")
        return True

    # Card variant operations starts here
    def __get_variants_by_query(
        self, db_context: Connection, query: str, values: dict[str, str | int | None]
    ) -> list[str]:
        """Retrieve card variants using a custom SQL query."""
        cursor = db_context.cursor()

        cursor.execute(query, values)
        tuple_list = cursor.fetchall()
        variants_list: list[str] = []

        for tpl in tuple_list:
            variants_list.append(tpl["variant"])

        return variants_list

    def add_variant(self, db_context: Connection, card_id: int, variant: str) -> bool:
        """Add a variant to a card in the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Adding card variant '{variant}' of card '{card_id}' to the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO card_variants (card_id, variant) VALUES (:card_id, :variant)""",
                {"card_id": card_id, "variant": variant},
            )
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to add card variant '{variant}' of card '{card_id}' to the database: {error}.")
            return False

        logger.info(f"Succesfully added card variant '{variant}' of card '{card_id}' to the database.")
        return True

    def get_variants(self, db_context: Connection, card_id: int) -> list[str]:
        """Retrieve all variants belonging to a card."""
        return self.__get_variants_by_query(
            db_context,
            "SELECT variant FROM card_variants WHERE card_id = :card_id",
            {"card_id": card_id},
        )

    def get_variant_types_in_set(
        self, db_context: Connection, set_id: int
    ) -> list[str]:
        """Retrieve all unique variant types used within a set."""
        return self.__get_variants_by_query(
            db_context,
            """SELECT DISTINCT variant FROM card_variants
                                            JOIN cards ON card_variants.card_id = cards.id
                                            WHERE cards.set_id = :set_id""",
            {"set_id": set_id},
        )

    def delete_variant(
        self, db_context: Connection, card_id: int, variant: str
    ) -> bool:
        """Delete a specific variant from a card."""
        logger = logging.getLogger(__name__)
        logger.info("Deleting variant '%s' from card '%s'", variant, card_id)
        cursor = db_context.cursor()

        try:
            cursor.execute(
                """DELETE FROM card_variants WHERE (card_id, variant)=(:card_id, :variant)""",
                {"card_id": card_id, "variant": variant},
            )
            db_context.commit()

        except db_error as error:
            logger.warning("Failed to delete variant '%s' of card '%s' from the database: '%s'.", variant, card_id, error)
            return False

        logger.info("Succesfully deleted variant '%s' of card '%s' from the database.", variant, card_id)
        return True

    def delete_variants(self, db_context: Connection, card_id: int) -> bool:
        """Delete all variants belonging to a card."""
        variants = self.get_variants(db_context, card_id)
        if not variants:
            return True

        for variant in variants:
            if not self.delete_variant(db_context, card_id, variant):
                return False

        return True

    # Card image operations
    def save_image(
        self, db_context: Connection, card_id: int, image_data: bytes, content_type: str
    ) -> bool:
        """Save a card image to the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Adding card image of card '{card_id}' to the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute(
                """INSERT INTO card_images (card_id, image_data, content_type) VALUES (:card_id, :image_data, :content_type)""",
                {
                    "card_id": card_id,
                    "image_data": image_data,
                    "content_type": content_type,
                },
            )
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to add image of card '{card_id}' to the database: {error}.")
            return False

        logger.info(f"Succesfully added image of card {card_id} to the database.")
        return True

    def get_image(
        self, db_context: Connection, card_id: int
    ) -> tuple[bytes, str] | None:
        """Retrieve a card image and its content type."""
        cursor = db_context.cursor()

        cursor.execute(
            """SELECT * FROM card_images WHERE card_id = :card_id""",
            {"card_id": card_id},
        )
        image = cursor.fetchone()
        if image is None:
            return None

        return image["image_data"], image["content_type"]

    def delete_image(self, db_context: Connection, card_id: int) -> bool:
        """Delete a card image from the database."""
        logger = logging.getLogger(__name__)
        logger.info(f"Deleting image of card '{card_id}' from the database.")
        cursor = db_context.cursor()

        try:
            cursor.execute(
                """DELETE FROM card_images WHERE card_id=:card_id""",
                {"card_id": card_id},
            )
            db_context.commit()

        except db_error as error:
            logger.warning(f"Failed to delete image of card '{card_id}' from the database: {error}.")
            return False

        logger.info(f"Succesfully deleted image of card '{card_id}' from the database")
        return True

    def delete_card_and_properties(self, db_context: Connection, card_id: int) -> bool:
        """Delete a card and all associated images and variants."""
        if self.get_image(db_context, card_id) is not None:
            if not self.delete_image(db_context, card_id):
                return False

        if self.get_variants(db_context, card_id):
            if not self.delete_variants(db_context, card_id):
                return False

        if self.get_card_by_id(db_context, card_id) is not None:
            if not self.delete_card(db_context, card_id):
                return False

        return True

    def reset_set_cards(self, db_context: Connection, set_id: int) -> bool:
        """Delete all cards from a set and reset its sync status."""
        logger = logging.getLogger(__name__)
        set_cards = self.get_cards_by_set(db_context, set_id)

        for card in set_cards:
            if not self.delete_card(db_context, card.id):
                logger.warning(f"Failed to remove card '{card.id}' from the database.")
                return False

        current_set = Set_operations().get_set_by_id(db_context, set_id)
        assert current_set
        current_set.sync_complete = 0
        Set_operations().update_set(db_context, current_set)

        return True
