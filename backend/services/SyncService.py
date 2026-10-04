from api.pokemon_tcg_api import PokemonTCGAPI
from database.db_operations import Set_operations, Card_operations, Set, Connection, Card

class SyncService:

    def __init__(self) -> None:
        self.set_operations = Set_operations()
        self.pokemontcgapi = PokemonTCGAPI()
        self.card_operations = Card_operations()

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

                add_attempt = self.set_operations.add_set(db_context, new_set)

                if not add_attempt:
                    print("Failed to add set to database")
                    return database_sets
                
                database_sets.append(new_set)

        return database_sets

    async def sync_set_info(self, db_context:Connection, set_id:int) -> Set | None:
        api_response = await self.pokemontcgapi.get_set(set_id)
        if not api_response["success"]:
            print(api_response["error"])
            return None

        updated_set = Set.from_api_to_Set(api_response["data"])
        if not (self.set_operations.update_set(db_context, updated_set)):
            print("Failed to update the set data to the database.")
            return None

        return updated_set

    async def sync_cards_in_set(self, db_context:Connection, set_id:int, difference:int, db_set_cards:list[Card]) -> bool:
        api_response = await self.pokemontcgapi.get_cards(set_id, (difference + 100) // 100)
        db_card_ids = [item.id for item in db_set_cards]

        if not api_response["success"]:
            print(api_response["error"])
            return False
        for card in api_response['data']:
            if card["id"] not in db_card_ids:
                new_card = Card.from_api_to_Card(card)
                add_attempt = self.card_operations.add_card(db_context, new_card)

                if not add_attempt:
                    print("Failed to add card to database.")
                    return False

        return True

    async def sync_set(self, db_context:Connection, set_id:int) -> Set | None:
        db_set = self.set_operations.get_set_by_id(db_context, set_id)
        if db_set is None:
            print("Unable to find set in the database.")
            return None

        if db_set.card_count == None:
            db_set = await self.sync_set_info(db_context, set_id)
            if db_set == None:
                return None

        assert db_set.card_count is not None
        db_set_cards = self.card_operations.get_cards_by_set(db_context, set_id)
        difference = db_set.card_count - len(db_set_cards)
        
        if difference > 0:
            if not await self.sync_cards_in_set(db_context, set_id, difference, db_set_cards):
                print("Failed to get cards in set")
                return None

        