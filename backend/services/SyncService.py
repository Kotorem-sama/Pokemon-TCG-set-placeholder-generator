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
                new_set = Set(
                    api_set["id"],
                    api_set["name"],
                    api_set["slug"],
                    api_set["abbreviation"],
                    api_set["release_date"],
                    api_set["card_count"],
                    0)
                
                self.set_operations.add_set(db_context, new_set)
                database_sets.append(new_set)

        return database_sets