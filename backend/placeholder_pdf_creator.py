from logging import getLogger
from sqlite3 import Connection

from api.pokemon_tcg_api import PokemonTCGAPI
from database.db_operations import Card_operations, Set_operations
from services.document_generation_service import DocumentGeneration
from services.image_generation_service import ImageGeneration
from services.image_utils import ImageUtils
from services.sync_service import SyncService


class SetToPDF:
    def __init__(self, db_context: Connection) -> None:
        self.set_operations = Set_operations(db_context)
        self.card_operations = Card_operations(db_context)
        self.PokemonTCGAPI = PokemonTCGAPI()
        self.sync_service = SyncService(
            self.set_operations, self.PokemonTCGAPI, self.card_operations
        )
        self.image_generation_service = ImageGeneration(
            self.card_operations, self.set_operations
        )
        self.document_generation_service = DocumentGeneration()
        self.image_utils = ImageUtils()
        self.logger = getLogger(__name__)

    async def get_document(self, set_name: str):
        current_set = self.set_operations.get_set_by_name(set_name)
        if not current_set:
            self.logger.warning(
                "The inputted set_name was not recognised. Please try again with a different name."
            )
            return

        current_set = await self.sync_service.sync_set(current_set.id)
        if current_set is None:
            return

        if not self.image_generation_service.generate_images_for_set(current_set.id):
            return

        image_paths = self.image_utils.get_images_in_set_folder(current_set.name)
        if not image_paths:
            return

        self.document_generation_service.generate_pdf(image_paths, current_set.name)
