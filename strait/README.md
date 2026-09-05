# strait — satellite vessel detection & port activity monitoring

A Python package for detecting vessels from Sentinel-1 SAR imagery and
measuring port activity from satellite data — any port, any time.

## The one thing

```python
import strait

cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.4, 104.6),
    y=slice(1.0, 1.6),
    time=slice("2021-01", "2026-09"),
)
cutout.prepare()  # download + process scenes
detections = cutout.detect()  # CFAR vessel detection
monthly = cutout.aggregate(detections, zones={"eastern": (104.0, 1.24, 104.35, 1.40)})
```

That gives you monthly vessel counts per zone from free satellite radar.

## Why this exists

Ports publish trade statistics with a 2-4 week lag. Satellite radar
sees ships at anchor immediately, day or night, cloud or clear.
This package turns that satellite data into economic indicators.

It was built for the Singapore Strait Observatory project, where
radar-derived anchorage presence explains 48% of bunker sales variance
(R²=0.478, detrended, weather-robust, validated against AIS).

## Install

```bash
pip install strait-observatory
```

## What it does

| Layer | What | Output |
|---|---|---|
| `Cutout` | Spatial/temporal subset + data source abstraction | xarray Dataset |
| `detect()` | Vessel detection (trimmed CFAR) | GeoDataFrame of detections |
| `aggregate()` | Zone × time aggregation | Monthly/weekly/daily counts |
| `AIS` | Validation against live/historical AIS | Precision/recall metrics |
| `Stats` | Join with official trade statistics | Correlation results |

## Data sources

| Source | What | Auth |
|---|---|---|
| Copernicus Sentinel-1 | SAR radar imagery | Free CDSE account |
| AISStream.io | Live vessel AIS | Free API key |
| AISHub.net | Community AIS | Free membership |
| Mendeley (historical) | Port AIS datasets | Open download |
| S2Coast-2023 | 10m coastline (land mask) | Zenodo, open |

## Quick start

```bash
pip install strait-observatory
export CDSE_USER=your@email
export CDSE_PASSWORD=your_password
```

```python
import strait

# 1. Define your area and time
cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.4, 104.6),  # longitude
    y=slice(1.0, 1.6),      # latitude
    time=slice("2021-01", "2026-09"),
)

# 2. Download and process (first time takes ~1h for 5 years)
cutout.prepare()

# 3. Detect vessels
detections = cutout.detect(method="trimmed_cfar")

# 4. Define anchorage zones (or use built-in Singapore zones)
zones = strait.Zones.singapore_strait()
monthly = cutout.aggregate(detections, zones, freq="MS")

# 5. Validate against AIS (optional)
ais = strait.AIS(source="aisstream", api_key="...")
match = ais.match(detections, threshold_m=500)

# 6. Correlate with official statistics (optional)
stats = strait.Stats.from_datagov_sg()
results = stats.correlate(monthly, target="bunker_sales")
```

## Architecture (inspired by [atlite](https://github.com/PyPSA/atlite))

```
strait/
├── __init__.py          # exports Cutout, detect, aggregate, AIS, Stats
├── cutout.py            # Cutout class (spatial/temporal abstraction)
├── detect/
│   ├── __init__.py      # detect() dispatcher
│   ├── cfar.py          # classic CFAR (v3.1)
│   ├── trimmed_cfar.py  # trimmed CFAR (v4, from SAR literature)
│   └── land_mask.py     # coastline-based land mask
├── data/
│   ├── __init__.py      # data source registry
│   ├── sentinel1.py     # Sentinel-1 via CDSE (Sentinel Hub + OData)
│   ├── ais.py           # AIS from multiple sources
│   └── official.py      # Official statistics (data.gov.sg, etc.)
├── aggregate.py         # zone × time aggregation
├── validate.py          # SAR-AIS matching, precision/recall
├── stats.py             # econometric correlation
└── zones.py             # built-in zone definitions
```

## Built-in zones

```python
# Singapore Strait (from the observatory project)
zones = strait.Zones.singapore_strait()

# Define your own
zones = strait.Zones({
    "my_anchorage": (104.0, 1.24, 104.35, 1.40),  # lon_min, lat_min, lon_max, lat_max
    "port_area": (103.68, 1.20, 104.02, 1.34),
})
```

## License

MIT

## Citation

If you use this in research, cite the Singapore Strait Observatory:

```
@software{strait_observatory_2026,
  title = {strait: satellite vessel detection and port activity monitoring},
  author = {Sivasubramanian, S.},
  year = {2026},
  url = {https://github.com/siva-sub/strait}
}
```
