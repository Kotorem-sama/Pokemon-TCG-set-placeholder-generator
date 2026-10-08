from database.db_setup import DatabaseSetup as database
import pytest, asyncio, logging
from initializer import startup
from services.SyncService import SyncService

async def main():
    """Initialize the application, run tests and synchronize TCG sets."""

    database_path = startup()
    if database_path is None:
        quit()

    await tests()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    await SyncService().sync_sets(db_context)

    db_context.close()

async def tests():
    """Run the project's unit tests and stop the application on failure."""
    
    logger = logging.getLogger(__name__)
    logger.info("Executing unit tests...")

    test_result = pytest.main(["tests"])
    
    if test_result != 0:
        logger.error(f"Unit tests came back with an error: {test_result}")
        quit()

    logger.info("Tests have successfully been conducted!")


if __name__ == "__main__":
    asyncio.run(main())