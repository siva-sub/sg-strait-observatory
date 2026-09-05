# Getting Started with strait

## What strait does

strait detects ships from satellite radar (Sentinel-1 SAR) and turns those detections into economic indicators for ports. It answers questions like:

- How many vessels are anchored at this port right now?
- Is port activity increasing or decreasing?
- Are specific anchorage zones (bunkering, container, bulk) getting busier?
- Which vessels are broadcasting AIS and which aren't?

The core insight: ships anchored at a port are a **stock** (a count at any moment). That stock correlates with trade statistics that are published weeks later. Satellite radar sees ships immediately — day, night, through clouds, anywhere on Earth — for free.

## Install

```bash
pip install strait-observatory
```

That's it. No satellite credentials needed for the built-in demo mode.

## Your first run (30 seconds, no credentials)

```python
import strait

# Define where and when you want to look
cutout = strait.Cutout(
    module="demo",              # synthetic data for testing
    x=slice(103.4, 104.6),     # longitude range (Singapore Strait)
    y=slice(1.0, 1.6),          # latitude range
    time=slice("2021-01", "2021-06"),
)

# Download/process scenes (generates synthetic data in demo mode)
cutout.prepare()

# Detect vessels
detections = cutout.detect(method="trimmed_cfar")

# See what you found
print(f"Found {len(detections)} vessels")
print(detections.head())
```

Output:
```
Found 202 vessels
   lon    lat  date  npix  peak_db                   geometry
0  103.71  1.04  202101    5     12.3  POINT (103.71 1.04)
1  103.45  1.08  202101    4      8.9  POINT (103.45 1.08)
...
```

Each detection has:
- `geometry` — where the vessel is (lon, lat)
- `date` — which scene it was detected in (YYYYMM)
- `npix` — how many pixels the vessel occupies (proxy for size)
- `peak_db` — radar brightness in decibels (proxy for reflectivity)

## Detecting with different presets

strait ships with three parameter presets, each optimized for a different use case:

```python
# Balanced (default) — good for economic indicators
# 72% AIS match rate, catches most real vessels
det = cutout.detect(preset="balanced")

# Precision — high-confidence detections only
# 84% AIS match rate, fewer false positives
det = cutout.detect(preset="precision")

# Recall — maximum coverage, catches everything
# 62% AIS match rate, some false positives
det = cutout.detect(preset="recall")
```

## Counting vessels by zone

Zones are named geographic areas (anchorage, port approach, etc.):

```python
# Use built-in Singapore Strait zones
zones = strait.Zones.singapore_strait()

# Or define your own
zones = strait.Zones.custom({
    "my_anchorage": (104.0, 1.24, 104.35, 1.40),  # lon_min, lat_min, lon_max, lat_max
    "port_area": (103.68, 1.20, 104.02, 1.34),
})

# Aggregate detections by zone and time
monthly = cutout.aggregate(detections, zones=zones)
print(monthly)
```

Output:
```
zone        eastern_opl  port_area  total
period
2021-01-01            7         3     53
2021-02-01            6         6     85
2021-03-01            5         4     64
```

## Using real satellite data

To work with real Sentinel-1 scenes, you need:
1. A directory of `.tif` files (float32, linear sigma0)
2. A land mask `.tif` file

```python
from strait.data.sentinel1 import create_cache_from_directory

# One-time: build a local cache from your scene directory
create_cache_from_directory(
    source_dir="path/to/your/scenes",     # directory with .tif files
    cache_dir="~/.strait",               # where to store the cache
    land_mask_path="path/to/land_mask.tif"
)

# Then use the cache
cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.55, 104.35),
    y=slice(1.05, 1.55),
    path="~/.strait"
)
cutout.prepare()  # loads from local cache
detections = cutout.detect()
```

For instructions on downloading Sentinel-1 data, see [Data Sources](data-sources.md).

## Validating against AIS

If you have AIS vessel positions (from AISStream.io, AISHub, or a CSV), you can check how well your SAR detections match:

```python
import json

# Load AIS data (any format with lat/lon keys)
with open("ais_positions.json") as f:
    ais_data = json.load(f)
vessels = ais_data["vessels"]  # list of {"lat": ..., "lon": ..., "name": ...}

# Match SAR detections to AIS vessels
result = cutout.validate(
    detections=detections,
    ais_vessels=vessels,
    threshold_m=500  # match within 500 meters
)
print(f"Precision: {result['precision']*100:.0f}%")
print(f"Recall: {result['recall']*100:.0f}%")
print(f"Matched: {result['matched_sar']}/{result['n_sar']} detections")
```

## Next steps

- [Data Sources](data-sources.md) — where to get Sentinel-1 scenes, AIS feeds, and land masks
- [Use Cases](use-cases.md) — five complete workflows with code
- [API Reference](api-reference.md) — every parameter explained
- [Interpreting Results](interpretation.md) — what the numbers mean
- [Economic Relevance](economic-relevance.md) — the Singapore case study
