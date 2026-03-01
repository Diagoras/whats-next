import csv
import json
import glob
import os
import sys

from whatsnext.models import Place
from whatsnext.geocode import geocode_place, load_geocode_cache, save_geocode_cache

CACHE_FILE = "places_cache.json"


def ingest_all(data_dir: str = "data") -> list[Place]:
    """Parse all Takeout files, geocode, deduplicate, and cache."""
    places: list[Place] = []

    # Parse GeoJSON files (labeled places)
    for path in glob.glob(os.path.join(data_dir, "*.json")):
        basename = os.path.basename(path)
        if basename in ("places_cache.json", "geocode_cache.json"):
            continue
        places.extend(parse_geojson(path))

    # Parse CSV files (saved lists)
    for path in glob.glob(os.path.join(data_dir, "*.csv")):
        places.extend(parse_csv(path))

    # Deduplicate by Google Maps URL
    places = _deduplicate(places)

    # Geocode places missing coordinates
    geo_cache = load_geocode_cache(data_dir)
    needs_geocoding = [p for p in places if p.lat == 0.0 and p.lng == 0.0]
    if needs_geocoding:
        print(f"Geocoding {len(needs_geocoding)} places...", file=sys.stderr)
        for i, place in enumerate(needs_geocoding):
            coords = geocode_place(place.name, cache=geo_cache)
            if coords:
                place.lat, place.lng = coords
            else:
                print(f"  Warning: could not geocode '{place.name}'", file=sys.stderr)
            if (i + 1) % 50 == 0:
                print(f"  ...{i + 1}/{len(needs_geocoding)}", file=sys.stderr)
                save_geocode_cache(geo_cache, data_dir)
        save_geocode_cache(geo_cache, data_dir)

    # Filter out places we couldn't geocode
    geocoded = [p for p in places if p.lat != 0.0 or p.lng != 0.0]
    skipped = len(places) - len(geocoded)
    if skipped:
        print(f"Skipped {skipped} places that could not be geocoded.", file=sys.stderr)

    save_cache(geocoded, data_dir)
    return geocoded


def parse_geojson(filepath: str) -> list[Place]:
    """Parse a GeoJSON file (Labeled places, Saved Places)."""
    with open(filepath) as f:
        data = json.load(f)

    source = os.path.splitext(os.path.basename(filepath))[0]
    places = []

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])

        name = props.get("name") or props.get("Title") or ""
        if not name:
            continue

        # GeoJSON coordinates are [lng, lat]
        lng, lat = float(coords[0]), float(coords[1])

        places.append(Place(
            name=name,
            lat=lat,
            lng=lng,
            source_list=source,
            address=props.get("address", ""),
            google_maps_url=props.get("Google Maps URL", ""),
        ))

    return places


def parse_csv(filepath: str) -> list[Place]:
    """Parse a Takeout CSV file (Title, Note, URL, Tags, Comment)."""
    source = os.path.splitext(os.path.basename(filepath))[0]
    places = []

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("Title") or "").strip()
            if not title:
                continue

            places.append(Place(
                name=title,
                lat=0.0,
                lng=0.0,
                source_list=source,
                google_maps_url=(row.get("URL") or "").strip(),
                note=(row.get("Note") or "").strip(),
                tags=(row.get("Tags") or "").strip(),
                comment=(row.get("Comment") or "").strip(),
            ))

    return places


def load_cache(data_dir: str = "data") -> list[Place] | None:
    path = os.path.join(data_dir, CACHE_FILE)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    return [Place.from_dict(d) for d in data]


def save_cache(places: list[Place], data_dir: str = "data") -> None:
    path = os.path.join(data_dir, CACHE_FILE)
    with open(path, "w") as f:
        json.dump([p.to_dict() for p in places], f, indent=2)


def _deduplicate(places: list[Place]) -> list[Place]:
    """Deduplicate by Google Maps URL, merging notes from different lists."""
    seen: dict[str, Place] = {}
    no_url: list[Place] = []

    for p in places:
        if not p.google_maps_url:
            no_url.append(p)
            continue

        if p.google_maps_url in seen:
            existing = seen[p.google_maps_url]
            # Merge: keep the richer record, combine source lists
            if p.note and p.note not in existing.note:
                existing.note = f"{existing.note}; {p.note}".strip("; ")
            if p.source_list not in existing.source_list:
                existing.source_list = f"{existing.source_list}, {p.source_list}"
            # Prefer record with coordinates
            if existing.lat == 0.0 and p.lat != 0.0:
                existing.lat, existing.lng = p.lat, p.lng
            if not existing.address and p.address:
                existing.address = p.address
        else:
            seen[p.google_maps_url] = p

    return list(seen.values()) + no_url
