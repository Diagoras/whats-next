# whats-next: Personal Saved Places Search Tool

A tool for searching through Google Maps saved places and finding places
reachable within a given travel time. The user is based in Seattle, does
not have a car, and primarily walks, bikes, takes transit, or uses Uber.

## Setup

Dependencies and data are loaded automatically via the SessionStart hook.

### Required environment variables (set in Claude Code web environment config):
- `OPENROUTESERVICE_API_KEY` — free key from https://openrouteservice.org/dev/#/signup
- `TAKEOUT_URL` — direct download URL for your Google Takeout .tgz/.zip
  (e.g., a private GitHub Gist raw URL or any file host)

### How to get your data:
1. Go to https://takeout.google.com
2. Click "Deselect all", then check only **"Saved"** (NOT "Maps")
3. Export and download the .tgz file
4. Upload it somewhere with a direct download link (private GitHub Gist
   works well — create a gist, upload the .tgz, use the raw URL)
5. Set that URL as `TAKEOUT_URL` in your environment

### What happens on session start:
1. `uv sync` installs dependencies
2. `scripts/load_data.sh` downloads and extracts your Takeout data (if not already present)
3. `main.py ingest` parses the data and geocodes places (~16 min on first run, cached after)

## Data

Takeout export files go in `data/`. To manually re-ingest: `uv run python main.py ingest`

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
