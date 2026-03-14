from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


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
    opening_hours: list = field(default_factory=list)
    weekday_text: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Place":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def is_open_now(self, tz: str = "America/Los_Angeles") -> bool | None:
        """Check if place is currently open. Returns None if hours unknown."""
        if not self.opening_hours:
            return None
        now = datetime.now(ZoneInfo(tz))
        # API uses Sunday=0, Python weekday() uses Monday=0
        day = (now.weekday() + 1) % 7
        now_mins = now.hour * 60 + now.minute
        for period in self.opening_hours:
            if period["open"]["day"] == day:
                open_mins = period["open"]["hour"] * 60 + period["open"]["minute"]
                close = period.get("close")
                if not close:
                    return True  # 24 hours
                close_mins = close["hour"] * 60 + close["minute"]
                if close_mins == 0:
                    close_mins = 24 * 60  # midnight = end of day
                if open_mins <= now_mins < close_mins:
                    return True
        return False

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
