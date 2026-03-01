# whats-next: Personal Saved Places Search Tool

A tool for searching through Google Maps saved places and finding places
reachable within a given travel time. The user is based in Seattle, does
not have a car, and primarily walks, bikes, takes transit, or uses Uber.

## Setup

Dependencies are installed automatically via the SessionStart hook.
The `OPENROUTESERVICE_API_KEY` environment variable must be set in the
Claude Code environment configuration for proximity queries.

## Data

Takeout export files go in `data/`. Run `uv run python main.py ingest`
to parse them and build the cache (also runs automatically on session start).

## Commands

### Search places by name, cuisine, category, or any keyword:
```
uv run python main.py search "italian"
uv run python main.py search "coffee" --list "Favorite places"
uv run python main.py search "amaro"
```

### Search within the user's personal notes:
```
uv run python main.py search-notes "birthday"
uv run python main.py search-notes "callie"
```

### Find places reachable within a travel time:
```
uv run python main.py nearby "Capitol Hill, Seattle" --minutes 10 --mode walk
uv run python main.py nearby "47.6062, -122.3321" --minutes 15 --mode walk
uv run python main.py nearby "downtown Seattle" --minutes 20 --mode uber --query "ramen"
```

### Show available lists:
```
uv run python main.py lists
```

## Handling User Requests

- **"Find me Italian restaurants"** -> `search "italian"`
- **"What did Callie recommend?"** -> `search-notes "callie"`
- **"What's near me?"** -> Ask for their location, then `nearby "<location>" --minutes 15 --mode walk`
- **"Where can I walk to for dinner?"** -> Ask for location, then `nearby "<location>" --minutes 15 --mode walk --query "restaurant"`
- **"Show me my Want to go list"** -> `search "" --list "Want to go"` (or just `lists` first)
- **"10-minute Uber from downtown"** -> `nearby "downtown Seattle" --minutes 10 --mode uber`

## Travel Modes
- `walk` — Walking (default)
- `bike` — Bicycling
- `drive` / `uber` / `transit` — Driving (proxy for Uber; ORS has no transit routing)

## Notes
- Always include the Google Maps URL in results so the user can open directions.
- If no results found, suggest broadening the search or increasing travel time.
- This searches the user's personal saved places only, not all of Google Maps.
- The `--mode uber`/`transit` use driving-car as approximation. Mention this if relevant.
