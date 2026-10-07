from sqlite3 import Connection
from sqlite3 import Error as db_error
from classes import Set, Card

class Set_operations:
    def __get_set_from_query(self, db_context: Connection, query:str, values:dict[str, str | int | None]) -> Set | None:
            cursor = db_context.cursor()
    
            cursor.execute(f"""SELECT * FROM sets WHERE {query}""", values)
            set_row = cursor.fetchone()
            if set_row is None:
                return None
            
            return Set(set_row["id"],
                       set_row["name"],
                       set_row["slug"],
                       set_row["abbreviation"],
                       set_row["release_date"],
                       set_row["card_count"],
                       set_row["sync_complete"])
        
    def __get_sets_from_query(self, db_context: Connection, query:str, values:dict[str, str | int | None]) -> list[Set]:
        cursor = db_context.cursor()

        cursor.execute(f"SELECT * FROM sets {query} ORDER BY release_date DESC", values)
        tuple_list = cursor.fetchall()
        set_list:list[Set] = []
        
        for tpl in tuple_list:
            set_list.append(Set(tpl["id"],
                    tpl["name"],
                    tpl["slug"],
                    tpl["abbreviation"],
                    tpl["release_date"],
                    tpl["card_count"],
                    tpl["sync_complete"]))

        return set_list
    
    def add_set(self, db_context: Connection, new_set: Set) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""INSERT INTO sets 
            (id, name, slug, abbreviation, release_date, card_count, sync_complete)            
            VALUES(:id, :name, :slug, :abbreviation, :release_date, :card_count, :sync_complete)"""
                           , new_set.get_dict())

            db_context.commit()
        except db_error as error:
            print(f"Failed to insert set: {error}")

            return False
        return True

    def get_sets_by_year(self, db_context: Connection, year:int) -> list[Set]:
        return self.__get_sets_from_query(db_context, """WHERE 
            strftime('%Y', release_date) = :year""", {"year": str(year)})

    def get_all_sets(self, db_context: Connection) -> list[Set]:
        return self.__get_sets_from_query(db_context, "", {})

    def get_set_by_id(self, db_context: Connection, id:int) -> Set | None:
        return self.__get_set_from_query(db_context, "id = :id", {"id": id})

    def get_set_by_slug(self, db_context: Connection, slug:str) -> Set | None:
        return self.__get_set_from_query(db_context, "slug = :slug", {"slug": slug})

    def get_set_by_name(self, db_context: Connection, name:str) -> Set | None:
        return self.__get_set_from_query(db_context, "name LIKE :name", {"name": f"%{name}%"})
    
    def update_set(self, db_context: Connection, updated_set: Set) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""
                UPDATE sets SET
                    name = :name,
                    slug = :slug,
                    abbreviation = :abbreviation,
                    release_date = :release_date,
                    card_count = :card_count,
                    sync_complete = :sync_complete
                WHERE id = :id""", {
                "id": updated_set.id,
                "name": updated_set.name,
                "slug": updated_set.slug,
                "abbreviation": updated_set.abbreviation,
                "release_date": updated_set.release_date,
                "card_count": updated_set.card_count,
                "sync_complete": updated_set.sync_complete
            })

            db_context.commit()

        except db_error as error:
            print(f"Failed to update set: {error}")
            return False

        return True

    def delete_set(self, db_context: Connection, set_id:int) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""DELETE FROM sets WHERE id=(:id)""", {"id" : set_id})
            db_context.commit()
        except db_error as error:
            print(f"Failed to delete set: {error}")
            return False

        return True

    def is_set_complete(self, db_context: Connection, current_set:Set) -> bool:
        cards_in_set = Card_operations().get_cards_by_set(db_context, current_set.id)

        if len(cards_in_set) == current_set.card_count:
            return True

        return False

class Card_operations:
    def __get_card_by_query(self, db_context: Connection, query:str, values:dict[str, str | int | None]) -> Card | None:
        cursor = db_context.cursor()

        cursor.execute(f"""SELECT * FROM cards WHERE {query}""", values)
        card_row = cursor.fetchone()
        if card_row is None:
            return None
        
        return Card(card_row["id"],
                    card_row["set_id"],
                    card_row["name"],
                    card_row["number"],
                    card_row["rarity"])

    def __get_cards_by_query(self, db_context: Connection, query:str, values:dict[str, str | int | None]) -> list[Card]:
        cursor = db_context.cursor()

        cursor.execute(f"""SELECT * FROM cards {query}""", values)
        tuple_list = cursor.fetchall()
        card_list:list[Card] = []
                    
        for tpl in tuple_list:
            card_list.append(Card(tpl["id"],
                tpl["set_id"],
                tpl["name"],
                tpl["number"],
                tpl["rarity"]))

        return card_list
    
    def add_card(self, db_context: Connection, new_card: Card) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""INSERT INTO cards 
            (id, set_id, name, number, rarity)            
            VALUES(:id, :set_id, :name, :number, :rarity)
            """, new_card.get_dict())

            db_context.commit()
        except db_error as error:
            print(f"Failed to insert card: {error}")

            return False
        return True

    def get_all_cards(self, db_context: Connection) -> list[Card]:
        return self.__get_cards_by_query(db_context, "", {})

    def get_cards_by_set(self, db_context: Connection, set_id: int) -> list[Card]:
        return self.__get_cards_by_query(db_context, "WHERE set_id = :set_id", {"set_id": set_id})

    def get_cards_by_rarity(self, db_context: Connection, rarity: str) -> list[Card]:
        return self.__get_cards_by_query(db_context, "WHERE rarity = :rarity", {"rarity": rarity})

    def get_card_by_id(self, db_context: Connection, id:int) -> Card | None:
        return self.__get_card_by_query(db_context, "id = :id", {"id": id})

    def update_card(self, db_context: Connection, updated_card: Card) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""
                UPDATE cards SET
                    set_id = :set_id,
                    name = :name,
                    number = :number,
                    rarity = :rarity
                WHERE id = :id""", {
                "id": updated_card.id,
                "set_id": updated_card.set_id,
                "name": updated_card.name,
                "number": updated_card.number,
                "rarity": updated_card.rarity
            })

            db_context.commit()

        except db_error as error:
            print(f"Failed to update card: {error}")
            return False

        return True

    def delete_card(self, db_context: Connection, card_id:int) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""DELETE FROM cards WHERE id=(:id)""", {"id" : card_id})
            db_context.commit()
        except db_error as error:
            print(f"Failed to delete card: {error}")
            return False

        return True

    # Card variant operations starts here
    def __get_variants_by_query(self, db_context: Connection, query:str, values:dict[str, str | int | None]) -> list[str]:
        cursor = db_context.cursor()

        cursor.execute(query, values)
        tuple_list = cursor.fetchall()
        variants_list: list[str] = []

        for tpl in tuple_list:
            variants_list.append(tpl["variant"])

        return variants_list

    def add_variant(self, db_context: Connection, card_id:int, variant:str) -> bool:
        cursor = db_context.cursor()
        
        try:
            cursor.execute("""INSERT INTO card_variants (card_id, variant) VALUES (:card_id, :variant)""",
                           {"card_id": card_id, "variant": variant})
            db_context.commit()
        except db_error as error:
            print(f"Failed to add variant: {error}")
            return False

        return True

    def get_variants(self, db_context: Connection, card_id:int) -> list[str]:
        return self.__get_variants_by_query(db_context, "SELECT variant FROM card_variants WHERE card_id = :card_id", {"card_id": card_id})

    def get_variant_types_in_set(self, db_context: Connection, set_id:int) -> list[str]:
        return self.__get_variants_by_query(db_context, """SELECT DISTINCT variant FROM card_variants
                                            JOIN cards ON card_variants.card_id = cards.id
                                            WHERE cards.set_id = :set_id""", {"set_id": set_id})

    def delete_variant(self, db_context: Connection, card_id:int, variant:str) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""DELETE FROM card_variants WHERE (card_id, variant)=(:card_id, :variant)""", {"card_id": card_id, "variant": variant})
            db_context.commit()
        except db_error as error:
            print(f"Failed to delete variant: {error}")
            return False

        return True

    def delete_variants(self, db_context:Connection, card_id:int) -> bool:
        variants = self.get_variants(db_context, card_id)
        if not variants:
            return True
        
        for variant in variants:
            if not self.delete_variant(db_context, card_id, variant):
                return False

        return True

    # Card image operations
    def save_image(self, db_context: Connection, card_id:int, image_data:bytes, content_type:str) -> bool:
        cursor = db_context.cursor()
        
        try:
            cursor.execute("""INSERT INTO card_images (card_id, image_data, content_type) VALUES (:card_id, :image_data, :content_type)""",
                            {"card_id": card_id, "image_data": image_data, "content_type": content_type})
            db_context.commit()
        except db_error as error:
            print(f"Failed to add image: {error}")
            return False

        return True

    def get_image(self, db_context: Connection, card_id:int) -> tuple[bytes, str] | None:
        cursor = db_context.cursor()
        
        cursor.execute("""SELECT * FROM card_images WHERE card_id = :card_id""", {"card_id": card_id})
        image = cursor.fetchone()
        if image is None:
            return None
        
        return image["image_data"], image["content_type"]

    def delete_image(self, db_context: Connection, card_id:int) -> bool:
        cursor = db_context.cursor()
        
        try:
            cursor.execute("""DELETE FROM card_images WHERE card_id=:card_id""", {"card_id": card_id})
            db_context.commit()
        except db_error as error:
            print(f"Failed to delete image: {error}")
            return False

        return True

    def delete_card_and_properties(self, db_context: Connection, card_id:int) -> bool:
        if not self.get_image(db_context, card_id) is None:
            if not self.delete_image(db_context, card_id):
                return False

        if self.get_variants(db_context, card_id):
            if not self.delete_variants(db_context, card_id):
                return False

        if not self.get_card_by_id(db_context, card_id) is None:
            if not self.delete_card(db_context, card_id):
                return False

        return True

    def reset_set_cards(self, db_context: Connection, set_id: int) -> bool:
        set_cards = self.get_cards_by_set(db_context, set_id)

        for card in set_cards:
            if not self.delete_card(db_context, card.id):
                print("Failed to remove card.")
                return False

        current_set = Set_operations().get_set_by_id(db_context, set_id)
        assert current_set
        current_set.sync_complete = 0
        Set_operations().update_set(db_context, current_set)

        return True