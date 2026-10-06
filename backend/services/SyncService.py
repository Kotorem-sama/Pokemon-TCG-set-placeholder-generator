from api.pokemon_tcg_api import PokemonTCGAPI
from database.db_operations import Set_operations, Card_operations, Set, Connection, Card
from datetime import date, timedelta

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

    async def sync_card_variants(self, db_context:Connection, card_id:int) -> bool:
        api_response = await self.pokemontcgapi.get_card_prices(card_id)

        if not api_response["success"]:
            print(api_response["error"])
            return False

        for variant in api_response["data"]:
            if not self.card_operations.add_variant(db_context, card_id, variant["printing"]):
                print("Failed to add card variant to database.")
                return False

        return True

    async def sync_cards_in_set(self, db_context:Connection, set_id:int, db_set_cards:list[Card], refresh_existing_cards: bool) -> bool:
        start_page = 1 if refresh_existing_cards else ((len(db_set_cards) - 5) // 100) + 1
        start_page = start_page if start_page > 0 else 1

        api_response = await self.pokemontcgapi.get_cards(set_id, start_page)
        db_card_id = [item.id for item in db_set_cards]

        print(api_response)

        if not api_response["success"]:
            print(api_response["error"])
            return False
        
        for card in api_response['data']:
            if refresh_existing_cards and card["id"] in db_card_id:
                if not self.card_operations.delete_card_and_properties(db_context, card["id"]):
                    return False

                db_card_id.remove(card["id"])

            if card["id"] not in db_card_id:
                new_card = Card.from_api_to_Card(card, set_id)

                if new_card.id == 0 and new_card.set_id == 0:
                    return False

                if not self.card_operations.add_card(db_context, new_card):
                    print("Failed to add card to database.")
                    return False

            if not self.card_operations.get_image(db_context, card["id"]):
                if not await self.sync_image(db_context, card["image_url"], card["id"]):
                    return False
                
            if not self.card_operations.get_variants(db_context, card["id"]):
                if not await self.sync_card_variants(db_context, card["id"]):
                    return False

        return True

    async def sync_set(self, db_context:Connection, set_id:int) -> Set | None:
        db_set = self.set_operations.get_set_by_id(db_context, set_id)
        if db_set is None:
            print("Unable to find set in the database.")
            return None

        if db_set.card_count is None:
            db_set = await self.sync_set_info(db_context, set_id)
            if db_set == None:
                return None

        assert db_set.card_count is not None
        db_set_cards = self.card_operations.get_cards_by_set(db_context, set_id)

        within_sync_window = True

        if db_set.release_date is not None:
            two_weeks_from_today  = date.today() + timedelta(weeks=2)
            release_date = date.fromisoformat(db_set.release_date)
            within_sync_window = release_date < two_weeks_from_today
        
        if db_set.sync_complete == 0 or within_sync_window :
            if not await self.sync_cards_in_set(db_context, set_id, db_set_cards, within_sync_window):
                return None
        
        db_set.sync_complete = 1
        if not self.set_operations.update_set(db_context, db_set):
            print("Failed to finish updating a set to the database.")
            return None

        return db_set