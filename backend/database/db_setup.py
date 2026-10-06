from sqlite3 import Connection, connect, Row

class DatabaseSetup:

    def __init__(self, database_path:str):
        self.database_path = database_path

    def connect_db(self) -> Connection:
        conn = connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = Row
        return conn

    def integrity_check(self):
        db_context = self.connect_db()
        cursor = db_context.cursor()

        check = cursor.execute("PRAGMA integrity_check").fetchone()

        db_context.close()
        
        return check[0] == "ok"
        
    def initialise_db(self, db_context:Connection) -> Connection:
        cursor = db_context.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS sets (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        abbreviation TEXT,
        release_date TEXT,
        card_count INTEGER,
        sync_complete INTEGER
        )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        set_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        number TEXT,
        rarity TEXT,
        FOREIGN KEY (set_id) REFERENCES sets(id) ON DELETE CASCADE
        )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS card_variants (
        card_id INTEGER NOT NULL,
        variant TEXT NOT NULL,
        PRIMARY KEY (card_id, variant),
        FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
        )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS card_images (
        card_id INTEGER PRIMARY KEY,
        image_data BLOB,
        content_type TEXT NOT NULL,
        FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
        )""")

        db_context.commit()
        
        return db_context

    def reset_db(self, db_context:Connection):
        cursor = db_context.cursor()
        databases = ["card_images", "card_variants", "cards", "sets"]

        for table in databases:
            cursor.execute(f"""DROP TABLE IF EXISTS {table}""")

        db_context.commit()
        
        self.initialise_db(db_context)