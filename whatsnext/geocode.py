import json
import os
import re
import time
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "whats-next/1.0 (personal-use)"
DEFAULT_BIAS_CITY = "Seattle, WA"

# Seattle center for Google Places location bias
SEATTLE_LAT = 47.6062
SEATTLE_LNG = -122.3321

GOOGLE_API_KEY_ENV = "GOOGLE_MAPS_API_KEY"
GOOGLE_TEXTSEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def geocode_place(name: str, near_city: str = DEFAULT_BIAS_CITY, cache: dict | None = None) -> tuple[float, float] | None:
    """Geocode a place name. Tries Nominatim first (free), falls back to Google Places API.

    Tries progressively simpler name variants to handle decorated names like
    "TAT'S DELI - Cheesesteaks, Subs & Catering" or "Portage Bay Cafe in Ballard".
    """
    cache_key = name.strip().lower()
    if cache is not None and cache_key in cache:
        coords = cache[cache_key]
        return (coords[0], coords[1]) if coords else None

    # Try Nominatim first (free)
    coords = _try_nominatim(name, near_city)

    # Fall back to Google Places API if available
    if coords is None and os.environ.get(GOOGLE_API_KEY_ENV):
        coords = _google_text_search(name)

    if cache is not None:
        cache[cache_key] = list(coords) if coords else None

    time.sleep(1)
    return coords


def _try_nominatim(name: str, near_city: str) -> tuple[float, float] | None:
    """Try Nominatim with progressively simpler name variants."""
    variants = _name_variants(name)
    for variant in variants:
        result = _nominatim_search(f"{variant}, {near_city}")
        if result:
            return (float(result[0]["lat"]), float(result[0]["lon"]))
        result = _nominatim_search(variant)
        if result:
            return (float(result[0]["lat"]), float(result[0]["lon"]))
        time.sleep(1)
    return None


def _google_text_search(name: str) -> tuple[float, float] | None:
    """Search Google Places API for a business by name."""
    api_key = os.environ.get(GOOGLE_API_KEY_ENV)
    if not api_key:
        return None

    body = json.dumps({
        "textQuery": name,
        "locationBias": {
            "circle": {
                "center": {"latitude": SEATTLE_LAT, "longitude": SEATTLE_LNG},
                "radius": 50000.0,  # 50km around Seattle
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
            "X-Goog-FieldMask": "places.location",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            places = data.get("places", [])
            if places:
                loc = places[0]["location"]
                return (loc["latitude"], loc["longitude"])
    except Exception:
        pass
    return None


def _name_variants(name: str) -> list[str]:
    """Generate progressively simpler name variants for geocoding."""
    variants = [name]

    # Strip common suffixes/qualifiers after delimiters
    for sep in [" - ", " – ", " at ", " in ", " on "]:
        if sep in name:
            variants.append(name.split(sep)[0].strip())

    # Strip parenthetical content
    stripped = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    if stripped != name:
        variants.append(stripped)

    # Strip location qualifiers like "SeaTac", "Capitol Hill", "Ballard" after last word
    # by taking just the first part before a dash or comma
    for sep in [",", "/"]:
        if sep in name:
            variants.append(name.split(sep)[0].strip())

    # Remove % and special chars that confuse geocoders
    cleaned = re.sub(r"[%&]", " ", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned != name:
        variants.append(cleaned)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for v in variants:
        if v.lower() not in seen and v:
            seen.add(v.lower())
            unique.append(v)
    return unique


def parse_location_input(location_str: str) -> tuple[float, float]:
    """Parse user-provided location into (lat, lng).

    Accepts:
      - Raw coords: "47.6062, -122.3321"
      - Address: "Pike Place Market, Seattle"
      - Google Maps URL with embedded coords
    """
    s = location_str.strip()

    # Try raw coords
    match = re.match(r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$", s)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    # Try Google Maps URL with @lat,lng
    match = re.search(r"@(-?\d+\.?\d+),(-?\d+\.?\d+)", s)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    # Try Google Maps URL with ?q=lat,lng
    match = re.search(r"[?&]q=(-?\d+\.?\d+),(-?\d+\.?\d+)", s)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    # Geocode as address
    result = _nominatim_search(s)
    if result:
        return (float(result[0]["lat"]), float(result[0]["lon"]))

    raise ValueError(f"Could not resolve location: {location_str}")


def load_geocode_cache(data_dir: str = "data") -> dict:
    path = os.path.join(data_dir, "geocode_cache.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_geocode_cache(cache: dict, data_dir: str = "data") -> None:
    path = os.path.join(data_dir, "geocode_cache.json")
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def _nominatim_search(query: str) -> list[dict] | None:
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
    url = f"{NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data if data else None
    except Exception:
        return None
