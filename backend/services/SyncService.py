from classes import Set
from api.pokemon_tcg_api import PokemonTCGAPI
from database.db_operations import Set_operations
from sqlite3 import Connection

class SyncService:

    def __init__(self) -> None:
        self.set_operations = Set_operations()
        self.pokemontcgapi = PokemonTCGAPI()

    async def sync_sets(self, db_context: Connection) -> list[Set]:
        api_response = await self.pokemontcgapi.get_sets()
        database_sets = self.set_operations.get_all_sets(db_context)
        db_set_ids = [item.id for item in database_sets]

        if not api_response["success"]:
            print(api_response["error"])
            return database_sets

        for api_set in api_response["data"]:
            if api_set["id"] not in db_set_ids:
                new_set = Set.from_api_to_Set(api_set)

                self.set_operations.add_set(db_context, new_set)
                database_sets.append(new_set)

        return database_sets

    async def get_set(self, db_context:Connection, set_id:int) -> Set | None:
        database_sets = self.set_operations.get_set_by_id(db_context, set_id)
        if database_sets is None:
            print("Unable to find set in the database.")
            return None

        if database_sets.abbreviation != "":
            return database_sets

        api_response = await self.pokemontcgapi.get_set(set_id)
        if not api_response["success"]:
            print(api_response["error"])
            return database_sets

        print(api_response)
        updated_set = Set.from_api_to_Set(api_response["data"])
        if not (self.set_operations.update_set(db_context, updated_set)):
            print("Failed to update the set data to the database.")
            return database_sets

        return updated_set