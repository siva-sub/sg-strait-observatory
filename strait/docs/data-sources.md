# Data Sources

strait works with four types of data. Here's where to get each one, how to prepare it, and what it costs.

## 1. Sentinel-1 SAR imagery (the primary input)

Sentinel-1 is a radar satellite operated by the European Space Agency. It images the entire Earth every 6-12 days, works through clouds and at night, and the data is **completely free**.

### What you need
- **Product type:** IW GRD (Interferometric Wide swath, Ground Range Detected)
- **Polarization:** VV (vertical transmit, vertical receive — best for ship detection)
- **Format:** GeoTIFF after calibration (strait expects float32, linear sigma0)

### Where to get it

**Copernicus Data Space Ecosystem (CDSE)** — the main archive

1. Create a free account at [dataspace.copernicus.eu](https://dataspace.copernicus.eu)
2. Search for scenes over your area of interest in the [Copernicus Browser](https://browser.dataspace.copernicus.eu)
3. Download via the OData API or Sentinel Hub Process API

**Via the API (for automated pipelines):**

```python
# Set credentials
export CDSE_USER=your@email
export CDSE_PASSWORD=your_password

# Search for scenes
import requests

# Get auth token
r = requests.post(
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    data={"grant_type": "password", "username": CDSE_USER, "password": CDSE_PASSWORD,
          "client_id": "cdse-public"}
)
token = r.json()["access_token"]

# Search catalogue (Singapore Strait example)
poly = "POLYGON((103.55 1.05, 104.35 1.05, 104.35 1.55, 103.55 1.55, 103.55 1.05))"
params = {"$filter": f"Collection/Name eq 'SENTINEL-1' and contains(Name,'_IW_GRDH_1S') and OData.CSC.Intersects(area=geography'SRID=4326;{poly}')"}
r = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
                 params=params, timeout=60)
```

### Preparing scenes for strait

Sentinel-1 downloads come as ZIP files containing raw DN (digital number) values. You need to:

1. **Calibrate** to sigma0 (radar cross-section): `sigma0 = (DN / calibration_lut)^2`
2. **Convert to linear** (not dB): keep float32, values typically 0.001 to 10.0
3. **Apply land mask** (see below) to exclude land pixels
4. **Save as GeoTIFF** with the correct spatial reference

The [observatory project](https://github.com/siva-sub/sg-strait-observatory) includes scripts for this: `experiments/download_product.py` and `experiments/safe_to_crop.py`.

### Quota considerations

CDSE has two access methods with separate quotas:
- **Sentinel Hub Process API:** uses "processing units" (monthly allocation, resets monthly)
- **OData download:** uses bandwidth quota (separate from processing units)

If one is exhausted, the other may still work.

---

## 2. Land mask (coastline)

A land mask tells the detector which pixels are sea vs. land. Without it, the detector finds buildings and infrastructure, not ships.

### Recommended: S2Coast-2023

A global 10-meter coastline dataset derived from Sentinel-2, validated to RMSE 17.4m.

- **Download:** [Zenodo](https://zenodo.org/records/17092775) (file: `S2Coast2023_ERSIShapeFile_vector.zip`, 1.5 GB)
- **License:** Open (cite Duan et al. 2026)
- **Coverage:** Global

### Preparing for strait

```python
import geopandas as gpd
from rasterio.features import rasterize
from rasterio.transform import from_bounds
import numpy as np

# Load the shapefile
gdf = gpd.read_file("S2Coast-2023_Polygon_fishnet.shp")

# Filter to your area
from shapely.geometry import box
your_bbox = box(103.55, 1.05, 104.35, 1.55)  # adjust for your port
region = gdf[gdf.intersects(your_bbox)]

# Rasterize to your grid size
shape = (1500, 2400)  # rows, cols
bounds = (103.55, 1.05, 104.35, 1.55)
transform = from_bounds(*bounds, shape[1], shape[0])

land_mask = rasterize(
    [(geom, 1) for geom in region.geometry],
    out_shape=shape, transform=transform,
    fill=0, dtype="uint8", all_touched=True
).astype(bool)

# Save
import rasterio
with rasterio.open("land_mask.tif", "w", driver="GTiff",
                   height=shape[0], width=shape[1], count=1, dtype="uint8",
                   crs="EPSG:4326", transform=transform) as dst:
    dst.write(land_mask.astype("uint8"), 1)
```

### Alternative: temporal median

If you have 12+ scenes of the same area, you can build a land mask from the temporal median (land is static, ships move):

```python
median = np.median(stack_of_scenes, axis=0)  # in dB
land_mask = median > -12  # threshold in dB
```

This is what the Singapore project used before switching to S2Coast.

---

## 3. AIS vessel positions (for validation)

AIS (Automatic Identification System) is a VHF radio transponder system on ships. It gives you vessel identity, position, speed, type, and destination. Use it to validate your SAR detections.

### Free sources

**AISStream.io** — live WebSocket feed
- Free API key at [aisstream.io](https://aisstream.io) (GitHub sign-in)
- Real-time positions via WebSocket
- Covers areas with shore-based receivers
- Rate limit: 3 connections per account

```python
import asyncio, json, websockets

async def capture():
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
        await ws.send(json.dumps({
            "APIKey": "your_key",
            "BoundingBoxes": [[[1.6, 103.4], [1.0, 104.5]]],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
        }))
        async for msg in ws:
            data = json.loads(msg)
            if data["MessageType"] == "PositionReport":
                print(data["MetaData"]["ShipName"],
                      data["Message"]["PositionReport"]["Latitude"],
                      data["Message"]["PositionReport"]["Longitude"])

asyncio.run(capture())
```

**AISHub.net** — community REST API
- Free membership at [aishub.net](https://www.aishub.net)
- Query by bounding box, returns JSON/CSV
- Rate limit: 1 request per minute

```
https://data.aishub.net/ws.php?username=USER&format=1&output=json&latmin=1.0&latmax=1.6&lonmin=103.4&lonmax=104.5
```

**Historical datasets** (for backtesting)
- [Mendeley: AIS from 11 ports](https://data.mendeley.com/datasets/r37vwd493d/1) — Singapore, Antwerp, Busan, Rotterdam, LA, Southampton, and more (October 2023, free download)
- Your national maritime authority may provide historical AIS

### Important caveat: AIS coverage gaps

AIS depends on shore-based receivers (VHF radio, ~30-50 km range). Areas far from receivers have poor coverage. In our Singapore data:
- The AISStream.io live feed showed **zero** vessels in the eastern anchorage
- A historical dataset showed **4,240** vessels in the same area

SAR doesn't have this limitation — it sees everything from orbit. This is the core value proposition.

---

## 4. Official statistics (for economic correlation)

To correlate satellite detections with economic activity, you need official trade statistics.

### Singapore (data.gov.sg)

All free via the [CKAN API](https://data.gov.sg/api):

| Dataset | Resource ID | What it measures |
|---|---|---|
| Container Throughput Monthly | `d_da030f7028200d19ffcbe4a2d71af39c` | TEU (twenty-foot equivalent units) |
| Vessel Arrivals Total | `d_d48c5a038904f6da3c603cd854b6c191` | Ship calls (>75 GT) |
| Vessel Arrivals by Type | `d_8f264219109e61fffa87ac64dd5a9a65` | By type (tanker, container, bulk) |
| Bunker Sales Monthly | `d_4f5abbf4486bf8e52bbed3be56dde562` | Fuel sold (tonnes) |
| Merchandise Trade Monthly | `d_c41b1f16d0847996b1dcfd2ded0b2d91` | Total trade value |

```python
import requests

# Download bunker sales data
r = requests.get("https://data.gov.sg/api/action/datastore_search",
                 params={"resource_id": "d_4f5abbf4486bf8e52bbed3be56dde562",
                         "limit": 500})
data = r.json()["result"]["records"]
```

### Other ports

Most major ports publish monthly statistics:
- **Rotterdam:** [Port of Rotterdam statistics](https://www.portofrotterdam.com/en/port-facts-and-figures)
- **Shanghai:** [SIPG statistics](http://www.portshanghai.com.cn)
- **Busan:** [BPA statistics](https://www.busanpa.com)
- **EU ports:** [Eurostat maritime transport](https://ec.europa.eu/eurostat/web/transport/database)

---

## 5. Weather covariates (optional)

Wind speed affects SAR sea clutter (rough sea = more noise). Controlling for it strengthens your economic analysis.

**ERA5 (Copernicus Climate Data Store)**
- Monthly mean wind at 10m, global, 0.25° grid
- Free at [cds.climate.copernicus.eu](https://cds.climate.copernicus.eu)
- Requires free registration

**Open-Meteo (no registration needed)**
- Historical weather archive
- Daily wind speed maxima
- Free at [open-meteo.com](https://open-meteo.com)

```python
import requests

r = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
    "latitude": 1.25, "longitude": 103.95,
    "start_date": "2021-01-01", "end_date": "2026-08-31",
    "daily": "wind_speed_10m_max",
    "timezone": "Asia/Singapore"
})
```

---

## Putting it all together

A typical project setup:

```
my_project/
├── cache/               # strait local cache
│   ├── scenes/          # calibrated .tif scenes
│   │   ├── s1_202101.tif
│   │   ├── s1_202102.tif
│   │   └── ...
│   ├── land_mask.tif    # S2Coast rasterized
│   └── manifest.json
├── data/
│   ├── ais_snapshot.json       # live AIS capture
│   ├── official_stats.csv      # trade statistics
│   └── wind_monthly.csv       # weather covariate
└── analysis.ipynb              # your analysis notebook
```
