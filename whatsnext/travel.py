import json
import os
import urllib.request
from datetime import datetime, timezone

from shapely.geometry import shape, Point, Polygon, MultiPolygon

from whatsnext.models import Place

ORS_API_KEY_ENV = "OPENROUTESERVICE_API_KEY"
ORS_ISOCHRONE_URL = "https://api.openrouteservice.org/v2/isochrones/{profile}"

TRAVELTIME_APP_ID_ENV = "TRAVELTIME_APP_ID"
TRAVELTIME_API_KEY_ENV = "TRAVELTIME_API_KEY"
TRAVELTIME_URL = "https://api.traveltimeapp.com/v4/time-map"

ORS_MODES = {
    "walk": "foot-walking",
    "walking": "foot-walking",
    "foot": "foot-walking",
    "bike": "cycling-regular",
    "cycling": "cycling-regular",
    "bicycle": "cycling-regular",
    "drive": "driving-car",
    "driving": "driving-car",
    "car": "driving-car",
    "uber": "driving-car",
}

TRANSIT_MODES = {"transit", "public_transport", "bus", "train"}


def get_isochrone_polygon(
    lat: float,
    lng: float,
    minutes: int,
    mode: str = "walk",
):
    """Get reachable area polygon. Uses TravelTime for transit, ORS for others."""
    if mode.lower() in TRANSIT_MODES:
        return _traveltime_isochrone(lat, lng, minutes)
    return _ors_isochrone(lat, lng, minutes, mode)


def _traveltime_isochrone(lat: float, lng: float, minutes: int):
    """Get transit isochrone from TravelTime API."""
    app_id = os.environ.get(TRAVELTIME_APP_ID_ENV)
    api_key = os.environ.get(TRAVELTIME_API_KEY_ENV)
    if not app_id or not api_key:
        raise ValueError(
            f"Set {TRAVELTIME_APP_ID_ENV} and {TRAVELTIME_API_KEY_ENV} for transit mode. "
            "Get free keys at https://traveltime.com/"
        )

    body = json.dumps({
        "departure_searches": [{
            "id": "nearby",
            "coords": {"lat": lat, "lng": lng},
            "departure_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "travel_time": minutes * 60,
            "transportation": {"type": "public_transport"},
        }],
    }).encode()

    req = urllib.request.Request(
        TRAVELTIME_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Application-Id": app_id,
            "X-Api-Key": api_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        raise RuntimeError(f"TravelTime API error ({e.code}): {err_body}")

    results = data.get("results", [])
    if not results or not results[0].get("shapes"):
        raise RuntimeError("TravelTime returned no isochrone shapes")

    polygons = []
    for s in results[0]["shapes"]:
        shell = [(p["lng"], p["lat"]) for p in s["shell"]]
        holes = [[(p["lng"], p["lat"]) for p in h] for h in s.get("holes", [])]
        polygons.append(Polygon(shell, holes))

    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)


def _ors_isochrone(lat: float, lng: float, minutes: int, mode: str):
    """Get isochrone from OpenRouteService."""
    api_key = os.environ.get(ORS_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Set the {ORS_API_KEY_ENV} environment variable. "
            "Get a free key at https://openrouteservice.org/dev/#/signup"
        )

    profile = ORS_MODES.get(mode.lower())
    if not profile:
        valid = sorted(set(ORS_MODES.keys()) | TRANSIT_MODES)
        raise ValueError(f"Unknown travel mode '{mode}'. Use: {', '.join(valid)}")

    url = ORS_ISOCHRONE_URL.format(profile=profile)
    body = json.dumps({
        "locations": [[lng, lat]],
        "range": [minutes * 60],
        "range_type": "time",
    }).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"OpenRouteService API error ({e.code}): {body}")

    features = data.get("features", [])
    if not features:
        raise RuntimeError("OpenRouteService returned no isochrone features")

    return shape(features[0]["geometry"])


def filter_by_travel_time(
    places: list[Place],
    origin_lat: float,
    origin_lng: float,
    minutes: int,
    mode: str = "walk",
) -> list[Place]:
    """Return places reachable within the given travel time."""
    polygon = get_isochrone_polygon(origin_lat, origin_lng, minutes, mode)

    reachable = []
    for p in places:
        if p.lat == 0.0 and p.lng == 0.0:
            continue
        if polygon.contains(Point(p.lng, p.lat)):  # Shapely uses (x=lng, y=lat)
            reachable.append(p)

    return reachable


def filter_and_search(
    places: list[Place],
    query: str,
    origin_lat: float,
    origin_lng: float,
    minutes: int,
    mode: str = "walk",
    source_list: str | None = None,
) -> list[Place]:
    """Search first, then filter by travel time."""
    from whatsnext.search import search_places

    matched = search_places(places, query, source_list=source_list)
    return filter_by_travel_time(matched, origin_lat, origin_lng, minutes, mode)
