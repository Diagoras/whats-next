import json
from unittest.mock import patch, MagicMock

from whatsnext.geocode import parse_location_input, geocode_place


def test_parse_raw_coords():
    lat, lng = parse_location_input("47.6062, -122.3321")
    assert abs(lat - 47.6062) < 0.001
    assert abs(lng - (-122.3321)) < 0.001


def test_parse_raw_coords_no_space():
    lat, lng = parse_location_input("47.6062,-122.3321")
    assert abs(lat - 47.6062) < 0.001


def test_parse_google_maps_url_at():
    lat, lng = parse_location_input(
        "https://www.google.com/maps/place/Pike+Place/@47.6097,-122.3425,17z"
    )
    assert abs(lat - 47.6097) < 0.001
    assert abs(lng - (-122.3425)) < 0.001


def test_parse_google_maps_url_q():
    lat, lng = parse_location_input(
        "https://maps.google.com/?q=47.6062,-122.3321"
    )
    assert abs(lat - 47.6062) < 0.001


@patch("whatsnext.geocode._nominatim_search")
def test_parse_address(mock_search):
    mock_search.return_value = [{"lat": "47.6097", "lon": "-122.3425"}]
    lat, lng = parse_location_input("Pike Place Market, Seattle")
    assert abs(lat - 47.6097) < 0.001
    mock_search.assert_called_once_with("Pike Place Market, Seattle")


@patch("whatsnext.geocode._nominatim_search")
def test_parse_address_not_found(mock_search):
    mock_search.return_value = None
    try:
        parse_location_input("nonexistent place xyz")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


@patch("whatsnext.geocode.time.sleep")  # Don't actually sleep in tests
@patch("whatsnext.geocode._nominatim_search")
def test_geocode_place_uses_cache(mock_search, mock_sleep):
    cache = {"pike place market": [47.6097, -122.3425]}
    result = geocode_place("Pike Place Market", cache=cache)
    assert result == (47.6097, -122.3425)
    mock_search.assert_not_called()


@patch("whatsnext.geocode.time.sleep")
@patch("whatsnext.geocode._nominatim_search")
def test_geocode_place_caches_result(mock_search, mock_sleep):
    mock_search.return_value = [{"lat": "47.6097", "lon": "-122.3425"}]
    cache = {}
    result = geocode_place("Pike Place", cache=cache)
    assert result == (47.6097, -122.3425)
    assert "pike place" in cache


@patch("whatsnext.geocode.time.sleep")
@patch("whatsnext.geocode._nominatim_search")
def test_geocode_place_caches_none(mock_search, mock_sleep):
    mock_search.return_value = None
    cache = {}
    result = geocode_place("xyznonexistent", cache=cache)
    assert result is None
    assert cache["xyznonexistent"] is None
