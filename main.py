#!/usr/bin/env python3
"""whats-next: Search your saved places and find what's reachable."""

import argparse
import sys

from whatsnext.ingest import ingest_all, load_cache
from whatsnext.search import search_places, search_notes, list_all_sources
from whatsnext.travel import filter_by_travel_time, filter_and_search
from whatsnext.geocode import parse_location_input
from whatsnext.models import Place


def cmd_ingest(args):
    places = ingest_all(args.data_dir)
    print(f"Ingested {len(places)} places.")
    sources: dict[str, int] = {}
    for p in places:
        for s in p.source_list.split(", "):
            sources[s] = sources.get(s, 0) + 1
    for s in sorted(sources):
        print(f"  {s}: {sources[s]} places")


def cmd_search(args):
    places = _load(args.data_dir)
    results = search_places(places, args.query, source_list=args.list)
    _print_results(results)


def cmd_search_notes(args):
    places = _load(args.data_dir)
    results = search_notes(places, args.query)
    _print_results(results)


def cmd_nearby(args):
    places = _load(args.data_dir)
    origin_lat, origin_lng = parse_location_input(args.location)

    if args.query:
        results = filter_and_search(
            places, args.query, origin_lat, origin_lng,
            args.minutes, args.mode, source_list=args.list,
        )
    else:
        results = filter_by_travel_time(
            places, origin_lat, origin_lng, args.minutes, args.mode,
        )
        if args.list:
            results = [p for p in results if args.list.lower() in p.source_list.lower()]

    _print_results(results)


def cmd_lists(args):
    places = _load(args.data_dir)
    sources: dict[str, int] = {}
    for p in places:
        for s in p.source_list.split(", "):
            sources[s] = sources.get(s, 0) + 1
    for s in sorted(sources):
        print(f"  {s}: {sources[s]} places")


def _load(data_dir: str) -> list[Place]:
    places = load_cache(data_dir)
    if places is None:
        print("No cache found. Run 'python main.py ingest' first.", file=sys.stderr)
        sys.exit(1)
    return places


def _print_results(results: list[Place]):
    if not results:
        print("No places found.")
        return
    print(f"Found {len(results)} place(s):\n")
    for i, p in enumerate(results, 1):
        print(f"{i}. {p.name}")
        if p.address:
            print(f"   Address: {p.address}")
        if p.note:
            print(f"   Note: {p.note}")
        if p.tags:
            print(f"   Tags: {p.tags}")
        if p.comment:
            print(f"   Comment: {p.comment}")
        print(f"   List: {p.source_list}")
        if p.google_maps_url:
            print(f"   Maps: {p.google_maps_url}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Search your saved places")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Parse Takeout files and build cache")

    p_search = sub.add_parser("search", help="Search places by keyword")
    p_search.add_argument("query", help="Search terms")
    p_search.add_argument("--list", help="Filter to a specific list")

    p_notes = sub.add_parser("search-notes", help="Search within notes")
    p_notes.add_argument("query", help="Search terms")

    p_nearby = sub.add_parser("nearby", help="Find reachable places")
    p_nearby.add_argument("location", help="Your location (address, coords, or Maps URL)")
    p_nearby.add_argument("--minutes", type=int, default=15, help="Travel time budget (default: 15)")
    p_nearby.add_argument("--mode", default="walk", help="Travel mode: walk, bike, drive/uber")
    p_nearby.add_argument("--query", help="Optional search filter")
    p_nearby.add_argument("--list", help="Filter to a specific list")

    sub.add_parser("lists", help="Show available lists")

    args = parser.parse_args()
    commands = {
        "ingest": cmd_ingest,
        "search": cmd_search,
        "search-notes": cmd_search_notes,
        "nearby": cmd_nearby,
        "lists": cmd_lists,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
