from database.db_setup import DatabaseSetup as database
from sqlite3 import Connection

db = database(r"C:\Users\ricky\Documents\Projects\Pokemon TCG set lister\data\pokemon_cards.db")
db_context:Connection = db.connect_db()
db.initialise_db(db_context)
db_context.close()