import os
from flask import Flask, render_template, request, jsonify

from whatsnext.ingest import load_cache
from whatsnext.search import search_places, search_notes, list_all_sources
from whatsnext.travel import filter_by_travel_time, filter_and_search

app = Flask(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "data")
_places = None


def get_places():
    global _places
    if _places is None:
        _places = load_cache(DATA_DIR) or []
    return _places


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/lists")
def api_lists():
    places = get_places()
    sources = {}
    for p in places:
        for s in p.source_list.split(", "):
            sources[s] = sources.get(s, 0) + 1
    return jsonify(sorted(sources.items(), key=lambda x: -x[1]))


@app.route("/api/search")
def api_search():
    places = get_places()
    q = request.args.get("q", "")
    source = request.args.get("list")
    results = search_places(places, q, source_list=source)
    return jsonify([p.to_dict() for p in results[:50]])


@app.route("/api/search-notes")
def api_search_notes():
    places = get_places()
    q = request.args.get("q", "")
    results = search_notes(places, q)
    return jsonify([p.to_dict() for p in results[:50]])


@app.route("/api/nearby")
def api_nearby():
    places = get_places()
    try:
        lat = float(request.args["lat"])
        lng = float(request.args["lng"])
    except (KeyError, ValueError):
        return jsonify({"error": "lat and lng are required"}), 400

    minutes = int(request.args.get("minutes", 15))
    mode = request.args.get("mode", "walk")
    q = request.args.get("q")
    source = request.args.get("list")

    try:
        if q:
            results = filter_and_search(
                places, q, lat, lng, minutes, mode, source_list=source,
            )
        else:
            results = filter_by_travel_time(places, lat, lng, minutes, mode)
            if source:
                results = [p for p in results if source.lower() in p.source_list.lower()]
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify([p.to_dict() for p in results[:50]])
