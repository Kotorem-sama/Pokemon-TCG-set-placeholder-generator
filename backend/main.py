from database.db_setup import DatabaseSetup as database
import pytest
import sys

def main():
    test_result = pytest.main(["tests"])

    if test_result != 0:
        print("Tests failed. Application will not start.")
        sys.exit(test_result)

    print("All tests passed. Starting application...")

    db = database(r"C:\Users\ricky\Documents\Projects\Pokemon TCG set lister\backend\data\pokemon_cards.db")
    db_context = db.initialise_db(db.connect_db())

    db.reset_db(db_context)

    db_context.close()


if __name__ == "__main__":
    main()