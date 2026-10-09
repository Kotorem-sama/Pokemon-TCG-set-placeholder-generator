import datetime
import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from api.pokemon_tcg_api import PokemonTCGAPI
from database.db_operations import (
    Card,
    Card_operations,
    Connection,
    Set,
    Set_operations,
)


class SyncService:
    """Handles synchronising Pokémon TCG data between the API and database."""

    def __init__(self) -> None:
        self.set_operations = Set_operations()
        self.pokemontcgapi = PokemonTCGAPI()
        self.card_operations = Card_operations()

    async def sync_sets(self, db_context: Connection) -> list[Set]:
        """Synchronise all available Pokémon TCG sets with the database."""
        logger = logging.getLogger(__name__)
        logger.info("Synchronising all Pokémon sets.")

        api_response = await self.pokemontcgapi.get_sets()
        database_sets = self.set_operations.get_all_sets(db_context)
        db_set_ids = [item.id for item in database_sets]

        if not api_response["success"]:
            return database_sets

        for api_set in api_response["data"]:
            if api_set["id"] not in db_set_ids:
                new_set = Set.from_api_to_Set(api_set)
                if new_set.id == 0 and new_set.sync_complete == 9:
                    return database_sets

                if not self.set_operations.add_set(db_context, new_set):
                    return database_sets

                database_sets.append(new_set)

        logger.info("Syncing Pokémon sets complete!")
        return database_sets

    async def sync_set_info(self, db_context: Connection, set_id: int) -> Set | None:
        """Synchronise the information of a specific set."""
        logger = logging.getLogger(__name__)
        logger.info(f"Syncing the information of set '{set_id}'.")

        api_response = await self.pokemontcgapi.get_set(set_id)
        if not api_response["success"]:
            return None

        updated_set = Set.from_api_to_Set(api_response["data"])

        if updated_set.id == 0 and updated_set.sync_complete == 9:
            return None

        if not (self.set_operations.update_set(db_context, updated_set)):
            return None

        logger.info(f"Syncing information of set '{set_id}' complete!")
        return updated_set

    async def sync_image(
        self, db_context: Connection, image_url: str, card_id: int
    ) -> bool:
        """Download and store a card image in the database."""
        response = await self.pokemontcgapi.get_image(image_url)

        if not response["success"]:
            return False

        if response["data"] is None:
            return False

        return self.card_operations.save_image(
            db_context,
            card_id,
            response["data"]["image_data"],
            response["data"]["content_type"],
        )

    async def sync_card_variants(
        self, db_context: Connection, card_id: int, rarity: str
    ) -> bool:
        """Synchronise all available variants for a card."""
        logger = logging.getLogger(__name__)
        logger.info(f"Syncing all card variants '{card_id}'.")

        api_response = await self.pokemontcgapi.get_card_prices(card_id)

        variants: list[str] = []
        rarities = [
            "Double Rare",
            "Illustration Rare",
            "Mega Attack Rare",
            "Mega Hyper Rare",
            "Promo",
            "Special Illustration Rare",
            "Ultra Rare",
            "Futuristic Rare",
            "RBG Rare",
        ]

        if not api_response["success"]:
            return False

        if rarity in rarities:
            if not self.card_operations.add_variant(db_context, card_id, "Holofoil"):
                # Remove any variants already added if the synchronisation fails.
                self.card_operations.delete_variants(db_context, card_id)
                return False
            return True

        for variant in api_response["data"]:
            current_variant = variant["printing"]

            if current_variant == "Foil":
                current_variant = "Holofoil"

            if current_variant in variants:
                continue

            variants.append(current_variant)

            if not self.card_operations.add_variant(
                db_context, card_id, current_variant
            ):
                # Remove any variants already added if the synchronisation fails.
                self.card_operations.delete_variants(db_context, card_id)
                return False

        logger.info(f"Successfully synchronised all card variants of card '{card_id}'.")
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
        db_context: Connection,
        set_id: int,
        db_set_cards: list[Card],
        refresh_existing_cards: bool,
    ) -> bool:
        """Synchronise the cards, images and variants belonging to a set."""
        logger = logging.getLogger(__name__)
        logger.info(f"Start synchronising the cards of set '{set_id}'.")

        start_page = (
            1 if refresh_existing_cards else ((len(db_set_cards) - 5) // 100) + 1
        )
        start_page = start_page if start_page > 0 else 1

        api_response = await self.pokemontcgapi.get_cards(set_id, start_page)
        db_card_id = [item.id for item in db_set_cards]

        if not api_response["success"]:
            return False

        for card in api_response["data"]:
            if not self.is_card(card):
                continue

            if refresh_existing_cards and card["id"] in db_card_id:
                if not self.card_operations.delete_card_and_properties(
                    db_context, card["id"]
                ):
                    return False

                db_card_id.remove(card["id"])

            if card["id"] not in db_card_id:
                new_card = Card.from_api_to_Card(card, set_id)

                if new_card.id == 0 and new_card.set_id == 0:
                    return False

                if not self.card_operations.add_card(db_context, new_card):
                    return False

            if not self.card_operations.get_image(db_context, card["id"]):
                if not await self.sync_image(db_context, card["image_url"], card["id"]):
                    return False

            variants = self.card_operations.get_variants(db_context, card["id"])

            if not variants:
                if not await self.sync_card_variants(
                    db_context, card["id"], card["rarity"]
                ):
                    return False

        logger.info(f"Finished synchronising cards of set '{set_id}'!")
        return True

    async def sync_set(self, db_context: Connection, set_id: int) -> Set | None:
        """Synchronise a complete set, including its cards, images and variants."""
        logger = logging.getLogger(__name__)

        db_set = self.set_operations.get_set_by_id(db_context, set_id)
        if db_set is None:
            logger.info(
                f"Unable to find set '{set_id}' in the database. Attempting to get set info."
            )

            db_set = await self.sync_set_info(db_context, set_id)

            if db_set is None:
                return None

        if db_set.card_count is None:
            db_set = await self.sync_set_info(db_context, set_id)

            if db_set == None:
                return None

        db_set_cards = self.card_operations.get_cards_by_set(db_context, set_id)

        within_sync_window = True

        if db_set.release_date is not None:
            release_date = date.fromisoformat(db_set.release_date) + timedelta(weeks=2)
            within_sync_window = (
                release_date > datetime.now(ZoneInfo("Europe/Amsterdam")).date()
            )

        # Recently released sets are refreshed to account for newly available card data.
        if db_set.sync_complete == 0 or within_sync_window:
            if not await self.sync_cards_in_set(
                db_context, set_id, db_set_cards, within_sync_window
            ):
                return None

        db_set.sync_complete = 1
        if not self.set_operations.update_set(db_context, db_set):
            return None

        logger.info(f"Successfully added set '{set_id}'!")
        return db_set
