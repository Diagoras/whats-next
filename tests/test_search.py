from whatsnext.models import Place
from whatsnext.search import search_places, search_notes, list_all_sources


def _sample_places() -> list[Place]:
    return [
        Place(
            name="Pepino's Spaghetti House",
            lat=47.6, lng=-122.3,
            source_list="Want to go",
            note="from alex on bluesky",
        ),
        Place(
            name="Saint Bread",
            lat=47.61, lng=-122.31,
            source_list="Favorite places",
            note="get the smash burger with an extra patty",
        ),
        Place(
            name="The Ink Drinker",
            lat=47.62, lng=-122.32,
            source_list="Favorite places",
            note="library with cocktails",
        ),
        Place(
            name="Herb & Bitter Public House",
            lat=47.63, lng=-122.33,
            source_list="Want to go",
            note="amaro!",
        ),
        Place(
            name="IL Bistro",
            lat=47.64, lng=-122.34,
            source_list="Want to go",
            note="amaro!",
        ),
    ]


def test_search_by_name():
    results = search_places(_sample_places(), "pepino")
    assert len(results) == 1
    assert results[0].name == "Pepino's Spaghetti House"


def test_search_by_note():
    results = search_places(_sample_places(), "amaro")
    assert len(results) == 2


def test_search_multiple_terms():
    results = search_places(_sample_places(), "smash burger")
    assert len(results) == 1
    assert results[0].name == "Saint Bread"


def test_search_with_list_filter():
    results = search_places(_sample_places(), "amaro", source_list="Want to go")
    assert len(results) == 2

    results = search_places(_sample_places(), "amaro", source_list="Favorite")
    assert len(results) == 0


def test_search_notes_only():
    results = search_notes(_sample_places(), "library")
    assert len(results) == 1
    assert results[0].name == "The Ink Drinker"


def test_search_notes_no_match_in_name():
    # "Bread" is in name but not in notes
    results = search_notes(_sample_places(), "bread")
    assert len(results) == 0


def test_relevance_name_first():
    results = search_places(_sample_places(), "bitter")
    assert results[0].name == "Herb & Bitter Public House"


def test_list_all_sources():
    sources = list_all_sources(_sample_places())
    assert "Favorite places" in sources
    assert "Want to go" in sources
