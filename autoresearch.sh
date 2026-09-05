#!/usr/bin/env bash
# Reproducible discovery queries — Singapore geospatial showcase scouting loop.
# Usage: bash autoresearch.sh   (requires gh CLI, authed)
set -euo pipefail

outdir="notes/discovery"
mkdir -p "$outdir"

gh_search() {
  local name="$1"; shift
  echo "--- gh search: $name"
  gh search repos "$@" \
    --json fullName,stargazersCount,description,language,updatedAt \
    --limit 15 > "notes/discovery/gh_${name}.json" \
    && echo "saved notes/discovery/gh_${name}.json"
}

# Baseline: what already exists for Singapore
gh_search singapore_map    "singapore map" --sort stars
gh_search singapore_geo    "singapore geospatial" --sort stars
gh_search singapore_mrt    "singapore mrt" --sort stars

# International demos: travel time / isochrones (example-repo genre)
gh_search isochrone        "isochrone map" --sort stars
gh_search travel_time      "travel time map" --sort stars
gh_search commute_map      "commute map accessibility" --sort stars

# International demos: heavy viz tech
gh_search kepler_gl        --topic=kepler-gl --sort stars
gh_search deckgl           --topic=deckgl --sort stars
gh_search mapbox_gl        --topic=mapbox-gl --sort stars
gh_search leaflet_dash     "leaflet dashboard" --sort stars

# International demos: transit / GTFS / open data storytelling
gh_search gtfs_viz         "gtfs visualization" --sort stars
gh_search transit_viz      "transit visualization" --sort stars
gh_search otds             "open data dashboard city" --sort stars

# Earth observation / free satellite data demos (Copernicus, Landsat, GEE, STAC)
gh_search sentinel2        "sentinel-2" --sort stars
gh_search copernicus       "copernicus" --sort stars
gh_search landsat          "landsat" --sort stars
gh_search earth_engine     "google earth engine" --sort stars
gh_search uhi              "urban heat island" --sort stars
gh_search insar            "insar" --sort stars
gh_search stac             --topic=stac --sort stars
gh_search ship_detect      "ship detection sentinel" --sort stars
