import json
from unittest.mock import patch

from shapely.geometry import Polygon

from whatsnext.models import Place
from whatsnext.travel import filter_by_travel_time


# A simple square polygon around central Seattle (~47.6, -122.33)
MOCK_POLYGON = Polygon([
    (-122.35, 47.59),
    (-122.31, 47.59),
    (-122.31, 47.63),
    (-122.35, 47.63),
    (-122.35, 47.59),
])


def _sample_places() -> list[Place]:
    return [
        Place(name="Inside 1", lat=47.61, lng=-122.33, source_list="test"),
        Place(name="Inside 2", lat=47.60, lng=-122.32, source_list="test"),
        Place(name="Outside", lat=47.70, lng=-122.40, source_list="test"),
        Place(name="No coords", lat=0.0, lng=0.0, source_list="test"),
    ]


@patch("whatsnext.travel.get_isochrone_polygon")
def test_filter_by_travel_time(mock_iso):
    mock_iso.return_value = MOCK_POLYGON

    results = filter_by_travel_time(
        _sample_places(),
        origin_lat=47.61,
        origin_lng=-122.33,
        minutes=10,
        mode="walk",
    )

    assert len(results) == 2
    names = {p.name for p in results}
    assert "Inside 1" in names
    assert "Inside 2" in names
    assert "Outside" not in names
    assert "No coords" not in names


@patch("whatsnext.travel.get_isochrone_polygon")
def test_filter_empty_results(mock_iso):
    # Polygon far from all places
    mock_iso.return_value = Polygon([
        (0, 0), (1, 0), (1, 1), (0, 1), (0, 0),
    ])

    results = filter_by_travel_time(
        _sample_places(),
        origin_lat=0.5,
        origin_lng=0.5,
        minutes=10,
        mode="walk",
    )

    assert len(results) == 0
