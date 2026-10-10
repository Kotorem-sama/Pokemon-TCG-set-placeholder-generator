from datetime import date, datetime, timedelta
from logging import getLogger
from typing import Any
from zoneinfo import ZoneInfo

from api.pokemon_tcg_api import PokemonTCGAPI
from database.db_operations import (
    Card,
    Card_operations,
    Set,
    Set_operations,
)


class SyncService:
    """Handles synchronising Pokémon TCG data between the API and database."""

    def __init__(
        self,
        set_op: Set_operations,
        pokemonapi: PokemonTCGAPI,
        card_op: Card_operations,
    ) -> None:
        self.set_operations = set_op
        self.pokemontcgapi = pokemonapi
        self.card_operations = card_op
        self.logger = getLogger(__name__)

    async def sync_sets(self) -> list[Set]:
        """Synchronise all available Pokémon TCG sets with the database."""
        self.logger.info("Synchronising all Pokémon sets.")

        api_response = await self.pokemontcgapi.get_sets()
        database_sets = self.set_operations.get_all_sets()
        db_set_ids = [item.id for item in database_sets]

        if not api_response["success"]:
            return database_sets

        for api_set in api_response["data"]:
            if api_set["id"] not in db_set_ids:
                new_set = Set.from_api_to_Set(api_set)
                if new_set.id == 0 and new_set.sync_complete == 9:
                    return database_sets

                if not self.set_operations.add_set(new_set):
                    return database_sets

                database_sets.append(new_set)

        self.logger.info("Syncing Pokémon sets complete!")
        return database_sets

    async def sync_set_info(self, set_id: int) -> Set | None:
        """Synchronise the information of a specific set."""
        self.logger.info(f"Syncing the information of set '{set_id}'.")

        api_response = await self.pokemontcgapi.get_set(set_id)
        if not api_response["success"]:
            return None

        updated_set = Set.from_api_to_Set(api_response["data"])

        if updated_set.id == 0 and updated_set.sync_complete == 9:
            return None
        
        return updated_set

    async def sync_image(self, image_url: str, card_id: int) -> bool:
        """Download and store a card image in the database."""
        response = await self.pokemontcgapi.get_image(image_url)

        if not response["success"]:
            return False

        if response["data"] is None:
            return False

        return self.card_operations.save_image(
            card_id,
            response["data"]["image_data"],
            response["data"]["content_type"],
        )

    async def sync_card_variants(self, card_id: int, rarity: str) -> bool:
        """Synchronise all available variants for a card."""
        self.logger.info(f"Syncing all card variants '{card_id}'.")

        api_response = await self.pokemontcgapi.get_card_prices(card_id)

        variants: list[str] = []
        rarities = [
            "Uncommon",
            "Common",
            "Rare",
            "Promo"
        ]

        if not api_response["success"]:
            return False

        if rarity not in rarities:
            if not self.card_operations.add_variant(card_id, "Holofoil"):
                # Remove any variants already added if the synchronisation fails.
                self.card_operations.delete_variants(card_id)
                return False
            return True

        if api_response["data"].get("printing") is None:
            api_response["data"]["printing"] = "Normal"

        for variant in api_response["data"]:
            current_variant = variant["printing"]

            if current_variant == "Foil":
                current_variant = "Holofoil"

            if current_variant in variants:
                continue

            variants.append(current_variant)

            if not self.card_operations.add_variant(card_id, current_variant):
                # Remove any variants already added if the synchronisation fails.
                self.card_operations.delete_variants(card_id)
                return False

        self.logger.info(
            f"Successfully synchronised all card variants of card '{card_id}'."
        )
        return True

    def is_card(self, card: dict[str, Any]) -> bool:
        """Determine whether API data represents a Pokémon card."""
        if card["product_type"] != "Cards":
            return False

        if card["rarity"] == "Code Card":
            return False

        custom_attributes = card.get("custom_attributes", {})

        if card["rarity"] is not None:
            return True

        if custom_attributes.get("cardType"):
            return True

        return bool(custom_attributes.get("cardTypeB"))

    async def sync_cards_in_set(
        self,
        set_id: int,
    ) -> bool:
        """Synchronise the cards, images and variants belonging to a set."""
        self.logger.info(f"Start synchronising the cards of set '{set_id}'.")

        cards_in_db = self.card_operations.get_cards_amount(set_id)

        start_page = max(1, (cards_in_db - 2) // 100 + 1)
        api_response = await self.pokemontcgapi.get_cards(set_id, start_page)

        if not api_response["success"]:
            return False

        for card in api_response["data"]:
            if not self.is_card(card):
                continue

            if self.card_operations.get_card_by_id(card["id"]) is None:
                new_card = Card.from_api_to_Card(card, set_id)

                if new_card.id == 0 and new_card.set_id == 0:
                    return False

                if not self.card_operations.add_card(new_card):
                    return False

            if not self.card_operations.get_image(card["id"]):
                if not await self.sync_image(card["image_url"], card["id"]):
                    return False

            if not self.card_operations.get_variants(card["id"]):
                if not await self.sync_card_variants(card["id"], card["rarity"]):
                    return False

        self.logger.info(f"Finished synchronising cards of set '{set_id}'!")
        return True

    async def sync_set(self, set_id: int) -> Set | None:
        """Synchronise a complete set, including its cards, images and variants."""

        db_set = self.set_operations.get_set_by_id(set_id)
        if db_set is None:
            self.logger.info(
                f"Unable to find set '{set_id}' in the database. Attempting to get set info."
            )

            db_set = await self.sync_set_info(set_id)

            if db_set is None:
                return None
            
            self.set_operations.add_set(db_set)

        if db_set.card_count is None:
            db_set = await self.sync_set_info(set_id)

            if db_set == None:
                return None

            if not (self.set_operations.update_set(db_set)):
                return None

        within_sync_window = True

        if db_set.release_date is not None:
            release_date = date.fromisoformat(db_set.release_date) + timedelta(weeks=2)
            within_sync_window = (
                release_date > datetime.now(ZoneInfo("Europe/Amsterdam")).date()
            )

        if within_sync_window:
            if not self.set_operations.delete_set(set_id):
                return None
            
            db_set.sync_complete = 0
            if not self.set_operations.add_set(db_set):
                return None

        # Recently released sets are refreshed to account for newly available card data.
        if db_set.sync_complete == 0 or within_sync_window:
            if not await self.sync_cards_in_set(set_id):
                return None

        db_set.sync_complete = 1
        if not self.set_operations.update_set(db_set):
            return None

        self.logger.info(f"Successfully added set '{set_id}'!")
        return db_set
