import json
import os
import urllib.request

from shapely.geometry import shape, Point

from whatsnext.models import Place

ORS_API_KEY_ENV = "OPENROUTESERVICE_API_KEY"
ORS_ISOCHRONE_URL = "https://api.openrouteservice.org/v2/isochrones/{profile}"

TRAVEL_MODES = {
    "walk": "foot-walking",
    "walking": "foot-walking",
    "foot": "foot-walking",
    "bike": "cycling-regular",
    "cycling": "cycling-regular",
    "bicycle": "cycling-regular",
    "drive": "driving-car",
    "driving": "driving-car",
    "car": "driving-car",
    "transit": "driving-car",
    "uber": "driving-car",
}


def get_isochrone_polygon(
    lat: float,
    lng: float,
    minutes: int,
    mode: str = "walk",
):
    """Get reachable area polygon from OpenRouteService."""
    api_key = os.environ.get(ORS_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Set the {ORS_API_KEY_ENV} environment variable. "
            "Get a free key at https://openrouteservice.org/dev/#/signup"
        )

    profile = TRAVEL_MODES.get(mode.lower())
    if not profile:
        raise ValueError(f"Unknown travel mode '{mode}'. Use: {', '.join(sorted(set(TRAVEL_MODES.values())))}")

    url = ORS_ISOCHRONE_URL.format(profile=profile)
    body = json.dumps({
        "locations": [[lng, lat]],  # ORS uses [lng, lat]
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
