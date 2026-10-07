from database.db_setup import DatabaseSetup as database
import pytest, sys, asyncio
from services.SyncService import SyncService
from initializer import startup
from database.db_operations import Set_operations, Card_operations

async def main():
    # await tests()

    database_path = startup()
    if database_path is None:
        quit()

    db = database(database_path)
    db_context = db.initialise_db(db.connect_db())

    # await SyncService().sync_sets(db_context)

    for set in ["Ascended heroes"]:
        set_to_download = Set_operations().get_set_by_name(db_context, set)
        if not set_to_download:
            continue

        await SyncService().sync_set(db_context, set_to_download.id)    

    db_context.close()

async def tests():
    test_result = pytest.main(["tests"])
    
    if test_result != 0:
        print("Tests failed.")
        sys.exit(test_result)

    print("All tests passed.")

if __name__ == "__main__":
    asyncio.run(main())