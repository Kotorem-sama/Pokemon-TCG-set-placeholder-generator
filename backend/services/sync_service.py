from datetime import date, datetime, timedelta
from logging import getLogger
from typing import Any, cast
from zoneinfo import ZoneInfo

from backend.database.db_operations import Card, DatabaseOperations, Set
from backend.database.db_setup import Database
from backend.services.pokemon_tcg_api_service import PokemonTCGAPI


class SyncService:
    """Handles synchronising Pokémon TCG data between the API and database."""

    def __init__(
        self,
        db_op: DatabaseOperations,
        pokemonapi: PokemonTCGAPI,
    ) -> None:
        self.operations = db_op
        self.pokemontcgapi = pokemonapi
        self.logger = getLogger(__name__)

    async def sync_sets(self) -> list[Set]:
        """Synchronise all available Pokémon TCG sets with the database."""
        self.logger.info("Synchronising all Pokémon sets.")

        api_response = await self.pokemontcgapi.get_sets()
        database_sets = self.operations.sets.get_all()
        db_set_ids = [item.id for item in database_sets]

        if not api_response["success"]:
            return database_sets

        for api_set in api_response["data"]:
            if api_set["id"] not in db_set_ids:
                new_set = Set.from_api_to_Set(api_set)
                if new_set.id == 0 and new_set.sync_complete == 9:
                    return database_sets

                if not self.operations.sets.add(new_set.get_dict()):
                    return database_sets

                self.operations.database.context.commit()
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

        return self.operations.images.add(
            {
                "card_id": card_id,
                "image_data": response["data"]["image_data"],
                "content_type": response["data"]["content_type"],
            }
        )

    async def sync_card_variants(self, card_id: int, rarity: str) -> bool:
        """Synchronise all available variants for a card."""
        self.logger.info(f"Syncing all card variants '{card_id}'.")

        api_response = await self.pokemontcgapi.get_card_prices(card_id)

        variants: list[str] = []
        rarities = ["Uncommon", "Common", "Rare", "Promo"]

        if not api_response["success"]:
            return False

        if rarity not in rarities:
            return self.operations.variants.add(
                {"card_id": card_id, "variant": "Holofoil"}
            )

        data = api_response.get("data")
        if not isinstance(data, list) or not data:
            self.logger.warning("Invalid variant data for card '%s'", card_id)
            return False

        current_variant = ""

        variant_data = cast(
            list[dict[str, object]],
            api_response["data"],
        )

        if not isinstance(data[0], dict):
            self.logger.warning("Invalid variant data for card '%s'", card_id)
            return False

        for variant in variant_data:
            if not variant.get("printing"):
                current_variant = "Normal"
            else:
                current_variant = str(variant["printing"])

            if current_variant == "Foil":
                current_variant = "Holofoil"

            if current_variant in variants:
                continue

            variants.append(current_variant)

            if not self.operations.variants.add(
                {"card_id": card_id, "variant": current_variant}
            ):
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

    async def sync_cards_in_set(self, db_set: Set, within_sync_window: bool) -> bool:
        """Synchronise the cards, images and variants belonging to a set."""
        self.logger.info(f"Start synchronising the cards of set '{db_set.id}'.")

        cards_in_db = self.operations.cards.get_amount_in_set(db_set.id)

        start_page = (
            max(1, (cards_in_db - 2) // 100 + 1) if not within_sync_window else 1
        )
        api_response = await self.pokemontcgapi.get_cards(db_set.id, start_page)

        if not api_response["success"]:
            return False

        own_database = self.operations
        if within_sync_window:
            self.operations = DatabaseOperations(Database("pokemon_cards_temp"))
            self.operations.database.initialise_db()
            self.operations.database.reset_db()
            self.operations.sets.add(db_set.get_dict())

        for card in api_response["data"]:
            if not self.is_card(card):
                continue

            retry_count = 0
            success = False

            while retry_count < 3 and not success:
                if self.operations.cards.get_by_id(card["id"]) is None:
                    new_card = Card.from_api_to_Card(card, db_set.id)

                    if new_card.id == 0 and new_card.set_id == 0:
                        retry_count += 1
                        continue

                    if not self.operations.cards.add(new_card.get_dict()):
                        retry_count += 1
                        continue

                if not self.operations.images.get_by_card_id(card["id"]):
                    if not await self.sync_image(card["image_url"], card["id"]):
                        retry_count += 1
                        continue

                if not self.operations.variants.get_by_card_id(card["id"]):
                    if not await self.sync_card_variants(card["id"], card["rarity"]):
                        retry_count += 1
                        self.operations.database.context.rollback()
                        continue

                self.operations.database.context.commit()
                success = True

            if within_sync_window and not success:
                self.operations.database.delete_database()
                self.operations = own_database

            if not success:
                self.operations.database.context.rollback()
                return False

        if within_sync_window:
            own_database.cards.delete({"set_id": db_set.id})
            merge_success = own_database.database.merge_db(self.operations.database)
            self.operations.database.reset_db()
            self.operations = own_database
            
            if not merge_success:
                self.operations.database.context.rollback()
                return False

        self.logger.info(f"Finished synchronising cards of set '{db_set.id}'!")
        return True

    async def sync_set(self, set_id: int) -> Set | None:
        """Synchronise a complete set, including its cards, images and variants."""

        db_set = self.operations.sets.get_by_id(set_id)
        if db_set is None:
            self.logger.info(
                f"Unable to find set '{set_id}' in the database. Attempting to get set info."
            )

            db_set = await self.sync_set_info(set_id)

            if db_set is None:
                return None

            if not self.operations.sets.add(db_set.get_dict()):
                return None

        if db_set.card_count is None:
            db_set = await self.sync_set_info(set_id)

            if db_set == None:
                return None

            if not (self.operations.sets.update(db_set.get_dict())):
                return None

        within_sync_window = False

        if db_set.release_date is not None:
            release_date = date.fromisoformat(db_set.release_date) + timedelta(weeks=2)
            within_sync_window = (
                release_date > datetime.now(ZoneInfo("Europe/Amsterdam")).date()
            )

        # Recently released sets are refreshed to account for newly available card data.
        if db_set.sync_complete == 0 or within_sync_window:
            if not await self.sync_cards_in_set(db_set, within_sync_window):
                return None

        if not within_sync_window:
            db_set.sync_complete = 1
            if not self.operations.sets.update(db_set.get_dict()):
                return None

        self.logger.info(f"Successfully added set '{set_id}'!")
        return db_set
