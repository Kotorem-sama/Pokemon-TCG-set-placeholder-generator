class Set:
    def __init__(self, id:int, name:str, slug:str,
                 abbreviation:str | None, release_date:str | None,
                 card_count:int | None, last_synced_at:str | None, last_api_sync:str):
        self.id = id
        self.name = name
        self.slug = slug
        self.abbreviation = abbreviation
        self.release_date = release_date
        self.card_count = card_count
        self.last_synced_at = last_synced_at
        self.last_api_sync = last_api_sync

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

    def __repr__(self):
        return self.__str__()

    def get_dict(self) -> dict[str, int | str]:
        dictionary:dict[str, int | str] = {
            'id' : self.id,
            'name' : self.name,
            'slug' : self.slug,
            'abbreviation' : self.abbreviation if self.abbreviation is not None else "",
            'release_date' : self.release_date if self.release_date is not None else "",
            'card_count' : self.card_count if self.card_count is not None else 0,
            'last_synced_at' : self.last_synced_at if self.last_synced_at is not None else "",
            'last_api_sync' : self.last_api_sync
        }
        return dictionary

class Card:
    def __init__(self, id:int, set_id:int, name:str,
                 number:str | None, rarity:str | None,
                 card_variants:list[str] = []):
        self.id = id
        self.set_id = set_id
        self.name = name
        self.number = number
        self.rarity = rarity
        self.card_variants = card_variants

    def __str__(self):
        return f"{self.name} ({self.number})"

    def __repr__(self):
        return self.__str__()

    def get_dict(self) -> dict[str , int | str | list[str]]:
        dictionary:dict[str , int | str | list[str]] = {
            "id" : self.id,
            "set_id" : self.set_id,
            "name": self.name,
            "number": self.number if self.number is not None else "",
            "rarity": self.rarity if self.rarity is not None else "",
            "card_variants": self.card_variants
        }
        return dictionary