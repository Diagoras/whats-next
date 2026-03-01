from whatsnext.models import Place


def search_places(
    places: list[Place],
    query: str,
    source_list: str | None = None,
) -> list[Place]:
    """Search places by keyword. All query terms must match (AND logic)."""
    if source_list:
        places = [p for p in places if source_list.lower() in p.source_list.lower()]

    terms = query.lower().split()
    if not terms:
        return sorted(places, key=lambda p: p.name.lower())

    results = []
    for p in places:
        text = p._searchable_text()
        if all(t in text for t in terms):
            results.append(p)

    results.sort(key=lambda p: p.relevance_score(terms[0]))
    return results


def search_notes(places: list[Place], query: str) -> list[Place]:
    """Search only within note and comment fields."""
    terms = query.lower().split()
    if not terms:
        return []

    results = []
    for p in places:
        note_text = f"{p.note} {p.comment}".lower()
        if all(t in note_text for t in terms):
            results.append(p)

    return results


def list_all_sources(places: list[Place]) -> list[str]:
    """Return unique source list names, sorted."""
    sources: dict[str, int] = {}
    for p in places:
        # Handle merged source lists like "Favorite places, charlotte"
        for s in p.source_list.split(", "):
            sources[s] = sources.get(s, 0) + 1
    return sorted(sources.keys())


def list_places_by_source(places: list[Place], source: str) -> list[Place]:
    """Return all places from a given list."""
    return [p for p in places if source.lower() in p.source_list.lower()]
