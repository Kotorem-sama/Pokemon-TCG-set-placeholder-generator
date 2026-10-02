from sqlite3 import Connection
from sqlite3 import Error as db_error
from classes import Set, Card

class Set_operations:
    def add_set(self, db_context: Connection, new_set: Set) -> bool:
        cursor = db_context.cursor()

        try:
            cursor.execute("""INSERT INTO sets 
            (id, name, slug, abbreviation, release_date, card_count, last_synced_at)            
            VALUES(:id, :name, :slug, :abbreviation, :release_date, :card_count, :last_synced_at)
            """, new_set.get_dict())

            db_context.commit()
        except db_error as error:
            print(f"Failed to insert set: {error}")

            return False
        return True

    def get_set(self, db_context: Connection, query:str, values:dict[str, str | int | None]) -> Set | None:
        cursor = db_context.cursor()

        cursor.execute("""SELECT * FROM sets WHERE """ + query, values)
        set_row = cursor.fetchone()
        if set_row is None:
            return None
        
        return Set(set_row["id"],
                   set_row["name"],
                   set_row["slug"],
                   set_row["abbreviation"],
                   set_row["release_date"],
                   set_row["card_count"],
                   set_row["last_synced_at"])
    
    def get_all_sets(self, db_context: Connection) -> list[Set]:
        cursor = db_context.cursor()

        cursor.execute("""SELECT * FROM sets""")
        tuple_list = cursor.fetchall()
        set_list:list[Set] = []
        
        for tpl in tuple_list:
            set_list.append(Set(tpl["id"],
                   tpl["name"],
                   tpl["slug"],
                   tpl["abbreviation"],
                   tpl["release_date"],
                   tpl["card_count"],
                   tpl["last_synced_at"]))

        return set_list

    def get_sets_by_year(self, db_context: Connection, year:int) -> list[Set]:
        cursor = db_context.cursor()
        
        cursor.execute("""
            SELECT * FROM sets
            WHERE strftime('%Y', release_date) = :year
            """, {"year": str(year)})
        tuple_list = cursor.fetchall()
        set_list:list[Set] = []
        
        for tpl in tuple_list:
            set_list.append(Set(tpl["id"],
                tpl["name"],
                tpl["slug"],
                tpl["abbreviation"],
                tpl["release_date"],
                tpl["card_count"],
                tpl["last_synced_at"]))

        return set_list
    
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
                    last_synced_at = :last_synced_at
                WHERE id = :id""", {
                "id": updated_set.id,
                "name": updated_set.name,
                "slug": updated_set.slug,
                "abbreviation": updated_set.abbreviation,
                "release_date": updated_set.release_date,
                "card_count": updated_set.card_count,
                "last_synced_at": updated_set.last_synced_at
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