from database.db_setup import DatabaseSetup as database

db = database(r"C:\Users\ricky\Documents\Projects\Pokemon TCG set lister\data\pokemon_cards.db")
db_context = db.initialise_db(db.connect_db())

db.reset_db(db_context)

db_context.close()