from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Place:
    name: str
    lat: float
    lng: float
    source_list: str
    google_maps_url: str = ""
    address: str = ""
    note: str = ""
    tags: str = ""
    comment: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Place":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def matches(self, query: str) -> bool:
        q = query.lower()
        return q in self._searchable_text()

    def matches_notes(self, query: str) -> bool:
        q = query.lower()
        return q in f"{self.note} {self.comment}".lower()

    def _searchable_text(self) -> str:
        return f"{self.name} {self.address} {self.note} {self.tags} {self.comment}".lower()

    def relevance_score(self, query: str) -> int:
        """Lower score = higher relevance."""
        q = query.lower()
        if q in self.name.lower():
            return 0
        if q in self.tags.lower():
            return 1
        if q in f"{self.note} {self.comment}".lower():
            return 2
        if q in self.address.lower():
            return 3
        return 4
