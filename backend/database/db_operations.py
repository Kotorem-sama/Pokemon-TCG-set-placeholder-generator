from sqlite3 import Connection
from classes import Set, Card

class Set_operations:
    def add_set(self, db_context: Connection, new_set: Set) -> bool:
        cursor = db_context.cursor()
        try:
            cursor.execute("""INSERT INTO sets VALUES (:id, :name, :slug,
            :abbreviation, :release_date, :card_count, :last_synced_at)
            """, new_set.get_dict())
        except Exception as error:
            print(f"Failed to insert set: {error}")
            return False
        return True

    def get_set_by_id(self, db_context: Connection) -> bool:
        return True
    
    def get_set_by_slug(self, db_context: Connection) -> bool:
        return True
    
    def get_all_sets(self, db_context: Connection) -> bool:
        return True

    def get_sets_by_year(self, db_context: Connection) -> bool:
        return True
    
    def update_set(self, db_context: Connection) -> bool:
        return True

    def delete_set(self, db_context: Connection) -> bool:
        return True