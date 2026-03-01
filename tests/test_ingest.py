import csv
import json
import os
import tempfile

from whatsnext.ingest import parse_geojson, parse_csv, _deduplicate
from whatsnext.models import Place


def test_parse_geojson():
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-122.33, 47.61]},
                "properties": {"name": "Home", "address": "123 Main St"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-122.34, 47.60]},
                "properties": {"name": "Work", "address": "456 5th Ave"},
            },
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        places = parse_geojson(path)
        assert len(places) == 2
        assert places[0].name == "Home"
        assert places[0].lat == 47.61
        assert places[0].lng == -122.33
        assert places[0].address == "123 Main St"
    finally:
        os.unlink(path)


def test_parse_geojson_skips_nameless():
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {},
            },
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        places = parse_geojson(path)
        assert len(places) == 0
    finally:
        os.unlink(path)


def test_parse_csv():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Note", "URL", "Tags", "Comment"])
        writer.writerow(["", "", "", "", ""])  # empty row, should be skipped
        writer.writerow([
            "Pike Place",
            "Callie recommended",
            "https://www.google.com/maps/place/Pike+Place",
            "",
            "",
        ])
        writer.writerow([
            "Glo's",
            "great eggs",
            "https://www.google.com/maps/place/Glos",
            "",
            "",
        ])
        path = f.name

    try:
        places = parse_csv(path)
        assert len(places) == 2
        assert places[0].name == "Pike Place"
        assert places[0].note == "Callie recommended"
        assert places[0].lat == 0.0  # No coords from CSV
        assert places[1].name == "Glo's"
    finally:
        os.unlink(path)


def test_deduplicate_merges_notes():
    p1 = Place(
        name="Roma Roma",
        lat=0.0, lng=0.0,
        source_list="Want to go",
        google_maps_url="https://maps.google.com/roma",
        note="new",
    )
    p2 = Place(
        name="Roma Roma",
        lat=47.6, lng=-122.3,
        source_list="charlotte",
        google_maps_url="https://maps.google.com/roma",
        note="Charlotte likes it",
    )

    result = _deduplicate([p1, p2])
    assert len(result) == 1
    assert "new" in result[0].note
    assert "Charlotte likes it" in result[0].note
    assert "charlotte" in result[0].source_list
    # Should take coords from the one that has them
    assert result[0].lat == 47.6


def test_deduplicate_no_url():
    p1 = Place(name="Random", lat=1.0, lng=2.0, source_list="test", google_maps_url="")
    p2 = Place(name="Random", lat=1.0, lng=2.0, source_list="test", google_maps_url="")

    result = _deduplicate([p1, p2])
    # Both kept since we can't dedup without URL
    assert len(result) == 2
