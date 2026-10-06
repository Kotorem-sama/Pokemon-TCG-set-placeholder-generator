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
                if new_set.id == 0 and new_set.sync_complete == 9:
                    return database_sets

                if not self.set_operations.add_set(db_context, new_set):
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

        if updated_set.id == 0 and updated_set.sync_complete == 9:
            return None
        
        if not (self.set_operations.update_set(db_context, updated_set)):
            print("Failed to update the set data to the database.")
            return None

        return updated_set

    async def sync_image(self, db_context:Connection, image_url:str, card_id:int) -> bool:
        db_card_image = self.card_operations.get_image(db_context, card_id)
        if db_card_image == None:
            response = await self.pokemontcgapi.get_image(image_url)

            if not response["success"]:
                print("Failed to retreive image from card", response["error"])
                return False

            if response["data"] == None:
                print("Failed to retreive image from card")
                return False

            if not self.card_operations.save_image(db_context, card_id, response["data"]["image_data"], response["data"]["content_type"]):
                print("Failed to save image to database")
                return False

        return True

    async def sync_cards_in_set(self, db_context:Connection, set_id:int, db_set_cards:list[Card]) -> bool:
        api_response = await self.pokemontcgapi.get_cards(set_id, ((len(db_set_cards)) // 100) + 1)
        db_card_id = [item.id for item in db_set_cards]

        if not api_response["success"]:
            print(api_response["error"])
            return False
        
        for card in api_response['data']:
            if card["id"] not in db_card_id:
                new_card = Card.from_api_to_Card(card, set_id)

                if new_card.id == 0 and new_card.set_id == 0:
                    return False

                if not self.card_operations.add_card(db_context, new_card):
                    print("Failed to add card to database.")
                    return False

                if not await self.sync_image(db_context, card["image_url"], card["id"]):
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
            if not await self.sync_cards_in_set(db_context, set_id, db_set_cards):
                return None

        return db_set