from logging import getLogger
from pathlib import Path
from sqlite3 import Connection, Row, connect


class Database:
    """Handles SQLite database connections, initialization and maintenance."""

    def __init__(self, database_name: str):
        """Initialize the database setup with the database file path."""
        self.database_path = Path(__file__).resolve().parent / f"{database_name}.db"
        self.logger = getLogger(__name__)
        self.context = self.__connect_db()

    def delete_database(self):
        """Ensure the database connection is closed when the object is deleted. Then the database file is removed."""
        self.close_db()
        self.database_path.unlink(missing_ok=True)

    def close_db(self):
        """Close the connection to the SQLite database."""
        if self.context:
            self.context.close()

    def __connect_db(self) -> Connection:
        """Create and configure a connection to the SQLite database."""
        conn = connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = Row
        return conn

    def integrity_check(self):
        """Check the integrity of the SQLite database."""
        self.logger.info("Starting a database integrity check.")

        cursor = self.context.cursor()

        check = cursor.execute("PRAGMA integrity_check").fetchone()
        cursor.close()

        if str(check[0]).lower() != "ok":
            self.logger.error(f"The integrity check came back negative: {check[0]}")
        else:
            self.logger.info("The integrity check has succeeded.")

        return str(check[0]).lower() == "ok"

    def initialise_db(self):
        """Create the database tables if they do not already exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        cursor = self.context.cursor()

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

        self.context.commit()

    def reset_db(self, databases: list[str] | None = None):
        """Drop the selected database tables and recreate the database structure."""
        cursor = self.context.cursor()
        if databases is None:
            databases = ["card_images", "card_variants", "cards", "sets"]

        for table in databases:
            cursor.execute(f"""DELETE FROM {table}""")

        self.context.commit()

    def merge_db(self, source_db: Database):
        """Merge the contents of another database into the current database."""
        self.logger.info(
            f"Merging database '{source_db.database_path}' into '{self.database_path}'."
        )

        source_cursor = source_db.context.cursor()
        target_cursor = self.context.cursor()

        for table in ["sets", "cards", "card_variants", "card_images"]:
            rows = source_cursor.execute(f"SELECT * FROM {table}").fetchall()
            for row in rows:
                columns = ", ".join(row.keys())
                placeholders = ", ".join("?" for _ in row.keys())
                values = tuple(row)
                target_cursor.execute(
                    f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})",
                    values,
                )

        self.context.commit()
