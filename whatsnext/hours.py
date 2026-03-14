"""Fetch and cache opening hours from Google Places API."""

import json
import os
import sys
import time
import urllib.request

GOOGLE_API_KEY_ENV = "GOOGLE_MAPS_API_KEY"
GOOGLE_TEXTSEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
CACHE_FILE = "hours_cache.json"

# Seattle center for location bias
SEATTLE_LAT = 47.6062
SEATTLE_LNG = -122.3321


def load_hours_cache(data_dir: str = "data") -> dict:
    path = os.path.join(data_dir, CACHE_FILE)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_hours_cache(cache: dict, data_dir: str = "data") -> None:
    path = os.path.join(data_dir, CACHE_FILE)
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def fetch_all_hours(places, data_dir: str = "data") -> dict:
    """Fetch opening hours for all places, using cache."""
    api_key = os.environ.get(GOOGLE_API_KEY_ENV)
    if not api_key:
        return {}

    cache = load_hours_cache(data_dir)
    to_fetch = [p for p in places if p.name not in cache]

    if not to_fetch:
        return cache

    print(f"Fetching opening hours for {len(to_fetch)} places...", file=sys.stderr)
    for i, place in enumerate(to_fetch):
        hours = _fetch_hours(place.name, api_key)
        cache[place.name] = hours
        time.sleep(0.1)  # Light rate limiting

        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(to_fetch)}", file=sys.stderr)
            save_hours_cache(cache, data_dir)

    save_hours_cache(cache, data_dir)
    return cache


def _fetch_hours(name: str, api_key: str) -> dict | None:
    """Fetch opening hours for a single place via Text Search."""
    body = json.dumps({
        "textQuery": name,
        "locationBias": {
            "circle": {
                "center": {"latitude": SEATTLE_LAT, "longitude": SEATTLE_LNG},
                "radius": 50000.0,
            }
        },
        "maxResultCount": 1,
    }).encode()

    req = urllib.request.Request(
        GOOGLE_TEXTSEARCH_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.regularOpeningHours",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            places = data.get("places", [])
            if places and "regularOpeningHours" in places[0]:
                hours = places[0]["regularOpeningHours"]
                return {
                    "periods": hours.get("periods", []),
                    "weekday_text": hours.get("weekdayDescriptions", []),
                }
    except Exception:
        pass
    return None
