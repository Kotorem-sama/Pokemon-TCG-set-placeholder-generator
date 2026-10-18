from logging import getLogger

from backend.database.db_operations import DatabaseOperations
from backend.database.db_setup import Database
from backend.functions.folder_functions import (
    get_images_in_set_folder,
    remove_set_images,
)
from backend.services.document_generation_service import DocumentGeneration
from backend.services.image_generation_service import ImageGeneration
from backend.services.pokemon_tcg_api_service import PokemonTCGAPI
from backend.services.sync_service import SyncService


class Backend:
    def __init__(self, database: Database) -> None:
        self.database = DatabaseOperations(database)
        self.PokemonTCGAPI = PokemonTCGAPI()
        self.sync_service = SyncService(self.database, self.PokemonTCGAPI)
        self.image_generation_service = ImageGeneration(self.database)
        self.document_generation_service = DocumentGeneration()
        self.logger = getLogger(__name__)

    def get_years(self):
        return self.database.sets.get_release_date_years()

    def get_sets_in_year(self, year: int):
        return self.database.sets.get_by_year(year)

    def get_variants_in_set(self, set_id: int):
        return self.database.variants.get_in_set(set_id)

    def get_rarities_in_set(self, set_id: int):
        return self.database.cards.get_rarities_in_set(set_id)

    async def get_document(self, set_name: str, rarities: list[str], variants: list[str]):
        set_sync = await self.sync_service.sync_sets()

        current_set = self.database.sets.get_by_name(set_name)

        if not current_set:
            if set_sync:
                self.logger.warning(
                    "The inputted set name is not valid. Please try again with a different name."
                )
                return
            else:
                self.logger.warning(
                    "The set was not found in the database, but the set synchronisation has failed. Please try again later."
                )
                return

        current_set = await self.sync_service.sync_set(current_set.id)
        if current_set is None:
            return

        if not self.image_generation_service.generate_images_for_set(current_set.id, rarities, variants):
            remove_set_images(current_set.name)
            return

        image_paths = get_images_in_set_folder(current_set.name)
        if not image_paths:
            return

        self.document_generation_service.generate_pdf(image_paths, current_set.name)
