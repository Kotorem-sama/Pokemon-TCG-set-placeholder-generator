from logging import getLogger
from pathlib import Path
from sqlite3 import Connection, Row, connect
from sqlite3 import Error as sqlite3Error


class Database:
    """Manage a SQLite database file, its connection, and its contents."""

    def __init__(self, database_name: str):
        """Open or create a database file in this module's directory.

        The connection is configured with row objects and foreign-key
        enforcement enabled.

        Args:
            database_name: Database filename without the ``.db`` extension.
        """
        self.database_path = Path(__file__).resolve().parent / f"{database_name}.db"
        self.logger = getLogger(__name__)
        self.context = self.__connect_db()

    def delete_database(self):
        """Close the connection and permanently remove this database file.

        Use only when the database is disposable, such as a temporary staging
        database. This operation deletes the file; it is not automatic cleanup.
        """
        self.close_db()
        self.database_path.unlink(missing_ok=True)

    def close_db(self):
        """Close the database connection without deleting the database file."""
        if self.context:
            self.context.close()

    def __connect_db(self) -> Connection:
        """Open the database and configure its connection.

        Returns:
            A connection with foreign-key enforcement enabled and rows returned
            as ``sqlite3.Row`` objects.
        """
        conn = connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = Row
        return conn

    def integrity_check(self) -> bool:
        """Run SQLite's integrity check.

        Returns:
            True if SQLite reports ``ok``, otherwise False.

        Raises:
            sqlite3.Error: If the integrity-check query fails.
        """
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
        """Create the application tables if they do not already exist.

        This creates the sets, cards, card variants, and card images tables,
        including their foreign-key constraints. It does not clear existing
        rows or migrate an existing schema.
        """
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        cursor = self.context.cursor()

        try:
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
        finally:
            cursor.close()

    def reset_db(self, databases: list[str] | None = None):
        """Delete rows from the selected tables and commit the changes.

        Args:
            databases: Tables to clear. Defaults to all application tables.
                Only the known table names are accepted.

        Raises:
            ValueError: If any requested table name is not allowed.
            sqlite3.Error: If clearing or committing the changes fails.
        """
        cursor = self.context.cursor()

        standard_databases = ["card_images", "card_variants", "cards", "sets"]

        if databases is None:
            databases = standard_databases

        if any(table not in standard_databases for table in databases):
            raise ValueError("Invalid table name(s) provided.")

        try:
            for table in databases:
                cursor.execute(f"""DELETE FROM {table}""")

            self.context.commit()
        finally:
            cursor.close()

    def merge_db(self, source_db: "Database") -> bool:
        """Copy card, variant, and image rows from another database.

        The destination must already contain the parent set rows required by
        the cards' foreign keys. The source's ``sets`` table is not copied.

        Args:
            source_db: Database whose card-related rows will be copied.

        Returns:
            True if all rows were copied and committed; False if a SQLite
            error caused the destination transaction to be rolled back.
        """
        self.logger.info(
            f"Merging database '{source_db.database_path}' into '{self.database_path}'."
        )

        source_cursor = source_db.context.cursor()
        target_cursor = self.context.cursor()

        try:
            for table in ["cards", "card_variants", "card_images"]:
                rows = source_cursor.execute(f"SELECT * FROM {table}").fetchall()
                for row in rows:
                    columns = ", ".join(row.keys())
                    placeholders = ", ".join("?" for _ in row)
                    values = tuple(row)
                    target_cursor.execute(
                        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                        values,
                    )
            self.context.commit()
            return True
        except sqlite3Error as error:
            self.context.rollback()
            self.logger.error(f"Failed to merge database: {error}")
            return False
        finally:
            source_cursor.close()
            target_cursor.close()
