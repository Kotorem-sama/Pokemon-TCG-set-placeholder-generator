from database.db_setup import DatabaseSetup as database
from database.db_operations import Set_operations
from classes import Set

db = database(r"C:\Users\ricky\Documents\Projects\Pokemon TCG set lister\data\pokemon_cards.db")
db_context = db.initialise_db(db.connect_db())

db.reset_db(db_context)

db_context.close()