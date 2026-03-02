import json
import os
import urllib.parse
import urllib.request

from shapely.geometry import shape, Point

from whatsnext.models import Place

ORS_API_KEY_ENV = "OPENROUTESERVICE_API_KEY"
ORS_ISOCHRONE_URL = "https://api.openrouteservice.org/v2/isochrones/{profile}"

GEOAPIFY_API_KEY_ENV = "GEOAPIFY_API_KEY"
GEOAPIFY_ISOLINE_URL = "https://api.geoapify.com/v1/isoline"

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
    """Get reachable area polygon. Uses Geoapify for transit, ORS for others."""
    if mode.lower() in TRANSIT_MODES:
        return _geoapify_isochrone(lat, lng, minutes)
    return _ors_isochrone(lat, lng, minutes, mode)


def _geoapify_isochrone(lat: float, lng: float, minutes: int):
    """Get transit isochrone from Geoapify Isoline API."""
    api_key = os.environ.get(GEOAPIFY_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Set {GEOAPIFY_API_KEY_ENV} for transit mode. "
            "Get a free key at https://myprojects.geoapify.com/"
        )

    params = urllib.parse.urlencode({
        "lat": lat,
        "lon": lng,
        "type": "time",
        "mode": "transit",
        "range": minutes * 60,
        "apiKey": api_key,
    })
    url = f"{GEOAPIFY_ISOLINE_URL}?{params}"

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        raise RuntimeError(f"Geoapify API error ({e.code}): {err_body}")

    features = data.get("features", [])
    if not features:
        raise RuntimeError("Geoapify returned no isochrone features")

    return shape(features[0]["geometry"])


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
