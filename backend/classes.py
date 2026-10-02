class Set:
    def __init__(self, id:int, name:str, slug:str,
                 abbreviation:str | None, release_date:str | None,
                 card_count:int | None, last_synced_at:str | None):
        self.id = id
        self.name = name
        self.slug = slug
        self.abbreviation = abbreviation
        self.release_date = release_date
        self.card_count = card_count
        self.last_synced_at = last_synced_at

class Card:
    def __init__(self, id:int, set_id:int, name:str,
                 number:str | None, rarity:str | None,
                 card_variants:list[str]):
        self.id = id
        self.set_id = set_id
        self.name = name
        self.number = number
        self.rarity = rarity
        self.card_variants = card_variants