#!/bin/bash
# Downloads and extracts Takeout data into data/ if not already present.
#
# Set TAKEOUT_URL in your Claude Code web environment to a direct download
# link for your Takeout .tgz/.zip (e.g., a private GitHub Gist raw URL,
# Google Drive direct link, or any file host).

set -e

DATA_DIR="${CLAUDE_PROJECT_DIR:-.}/data"
CACHE_FILE="$DATA_DIR/places_cache.json"

# Skip if data is already loaded
csv_count=$(find "$DATA_DIR" -name "*.csv" 2>/dev/null | wc -l)
if [ "$csv_count" -gt 0 ] && [ -f "$CACHE_FILE" ]; then
    exit 0
fi

# Skip if no URL configured
if [ -z "$TAKEOUT_URL" ]; then
    echo "No TAKEOUT_URL set — skipping data download." >&2
    echo "Set TAKEOUT_URL in your Claude Code environment to auto-load data." >&2
    exit 0
fi

echo "Downloading Takeout data..." >&2
TMPFILE=$(mktemp)

# Download
curl -fsSL "$TAKEOUT_URL" -o "$TMPFILE"

# Detect format and extract
MIME=$(file --mime-type -b "$TMPFILE")
case "$MIME" in
    application/gzip|application/x-gzip|application/x-tar)
        tar xzf "$TMPFILE" -C "$DATA_DIR" --strip-components=2 2>/dev/null \
            || tar xzf "$TMPFILE" -C "$DATA_DIR" 2>/dev/null
        ;;
    application/zip)
        TMP_EXTRACT=$(mktemp -d)
        unzip -q "$TMPFILE" -d "$TMP_EXTRACT"
        # Find the Saved/ directory and copy CSVs
        find "$TMP_EXTRACT" -name "*.csv" -exec cp {} "$DATA_DIR/" \;
        find "$TMP_EXTRACT" -name "*.json" -exec cp {} "$DATA_DIR/" \;
        rm -rf "$TMP_EXTRACT"
        ;;
    *)
        echo "Unknown file format: $MIME" >&2
        rm "$TMPFILE"
        exit 1
        ;;
esac

rm "$TMPFILE"

csv_count=$(find "$DATA_DIR" -name "*.csv" 2>/dev/null | wc -l)
echo "Loaded $csv_count data files into $DATA_DIR" >&2
