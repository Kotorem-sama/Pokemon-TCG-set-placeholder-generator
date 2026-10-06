from database.db_setup import DatabaseSetup as database
import pytest, sys, asyncio
from services.SyncService import SyncService
from initializer import startup
from database.db_operations import Card_operations

async def main():
    await tests()

    database_path = startup()
    if database_path is None:
        quit()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    # await SyncService().sync_sets(db_context)
    await SyncService().sync_set(db_context, 5500216)    

    db_context.close()

async def tests():
    test_result = pytest.main(["tests"])
    
    if test_result != 0:
        print("Tests failed.")
        sys.exit(test_result)

    print("All tests passed.")

if __name__ == "__main__":
    asyncio.run(main())