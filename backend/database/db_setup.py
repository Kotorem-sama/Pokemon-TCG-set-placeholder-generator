from logging import getLogger
from sqlite3 import Connection, Row, connect


class DatabaseSetup:
    """Handles SQLite database connections, initialization and maintenance."""

    def __init__(self, database_path: str):
        """Initialize the database setup with the database file path."""
        self.database_path = database_path
        self.logger = getLogger(__name__)

    def connect_db(self) -> Connection:
        """Create and configure a connection to the SQLite database."""
        conn = connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = Row
        return conn

    def integrity_check(self):
        """Check the integrity of the SQLite database."""
        self.logger.info("Starting a database integrity check.")

        db_context = self.connect_db()
        cursor = db_context.cursor()

        check = cursor.execute("PRAGMA integrity_check").fetchone()
        db_context.close()

        if str(check[0]).lower() != "ok":
            self.logger.error(f"The integrity check came back negative: {check[0]}")
        else:
            self.logger.info("The integrity check has succeeded.")

        return str(check[0]).lower() == "ok"

    def initialise_db(self, db_context: Connection) -> Connection:
        """Create the database tables if they do not already exist."""
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

    def reset_db(self, db_context: Connection, databases: list[str] | None = None):
        """Drop the selected database tables and recreate the database structure."""
        cursor = db_context.cursor()
        if databases is None:
            databases = ["card_images", "card_variants", "cards", "sets"]

        for table in databases:
            cursor.execute(f"""DROP TABLE IF EXISTS {table}""")

        db_context.commit()

        self.initialise_db(db_context)
