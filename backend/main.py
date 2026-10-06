from database.db_setup import DatabaseSetup as database
import pytest, sys, asyncio
from services.SyncService import SyncService
from initializer import startup

async def main():
    database_path = startup()
    test_result = pytest.main(["tests"])

    if test_result != 0:
        print("Tests failed. Application will not start.")
        sys.exit(test_result)

    print("All tests passed. Starting application...")

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    # await SyncService().sync_sets(db_context)
    # await SyncService().sync_set(db_context, 5500181)

    db_context.close()

if __name__ == "__main__":
    asyncio.run(main())