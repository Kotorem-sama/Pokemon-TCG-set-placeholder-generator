from types import SimpleNamespace
from unittest.mock import Mock

from backend.models import Card, Set
from backend.services.image_generation_service import ImageGeneration


def test_generate_images_for_card_filters_variants_with_existing_image():
    variants = ["Normal", "Holofoil", "Reverse Holofoil"]
    database = SimpleNamespace(
        variants=SimpleNamespace(get_by_card_id=Mock(return_value=variants)),
        images=SimpleNamespace(
            get_by_card_id=Mock(return_value=(b"image", "image/png"))
        ),
    )
    image_generation = ImageGeneration(database)
    image_generation.image_processor = Mock(return_value=True)
    card = Card(1, 1, "Test Card", "001", "Common")

    result = image_generation.generate_images_for_card(
        card, "Test Set", ["Holofoil"]
    )

    assert result is True
    image_generation.image_processor.assert_called_once_with(
        (b"image", "image/png"), card, "Test Set", "Holofoil"
    )


def test_generate_images_for_card_filters_placeholder_variants():
    variants = ["Normal", "Holofoil", "Reverse Holofoil"]
    database = SimpleNamespace(
        variants=SimpleNamespace(get_by_card_id=Mock(return_value=variants)),
        images=SimpleNamespace(get_by_card_id=Mock(return_value=None)),
    )
    image_generation = ImageGeneration(database)
    image_generation.generate_placeholder = Mock(return_value=True)
    card = Card(1, 1, "Test Card", "001", "Common")

    result = image_generation.generate_images_for_card(
        card, "Test Set", ["Holofoil"]
    )

    assert result is True
    image_generation.generate_placeholder.assert_called_once_with(
        card, "Holofoil", "Test Set", 287, 400
    )


def test_generate_images_for_set_filters_rarities():
    common_card = Card(1, 1, "Common Card", "001", "Common")
    rare_card = Card(2, 1, "Rare Card", "002", "Rare")
    database = SimpleNamespace(
        sets=SimpleNamespace(
            get_by_id=Mock(
                return_value=Set(1, "Test Set", "test-set", None, None, 2, 0)
            )
        ),
        cards=SimpleNamespace(get_in_set=Mock(return_value=[common_card, rare_card])),
        variants=SimpleNamespace(),
        images=SimpleNamespace(),
    )
    image_generation = ImageGeneration(database)
    image_generation.generate_images_for_card = Mock(return_value=True)

    result = image_generation.generate_images_for_set(1, ["Rare"], ["Normal"])

    assert result is True
    image_generation.generate_images_for_card.assert_called_once_with(
        rare_card, "Test Set", ["Normal"]
    )
