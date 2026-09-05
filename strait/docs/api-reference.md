# API Reference

## `strait.Cutout`

The main class. Defines where, when, and from which source to get satellite data.

### Constructor

```python
strait.Cutout(
    module="demo",              # "demo" (synthetic) or "sentinel1" (real data)
    x=slice(103.4, 104.6),     # longitude range
    y=slice(1.0, 1.6),          # latitude range
    time=slice("2021-01", "2026-09"),  # time range
    path="~/.strait",           # cache directory (optional)
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `module` | str | `"demo"` | Data source. `"demo"` = synthetic scenes (no download). `"sentinel1"` = real Sentinel-1 (loads from local cache or CDSE) |
| `x` | slice | `slice(103.4, 104.6)` | Longitude range. `x.start` = west, `x.stop` = east |
| `y` | slice | `slice(1.0, 1.6)` | Latitude range. `y.start` = south, `y.stop` = north |
| `time` | slice | `slice("2021-01", "2021-03")` | Time range. Uses pandas-parseable strings |
| `path` | str | `"~/.strait"` | Cache directory. Created if it doesn't exist |
| `**kwargs` | | | Passed to data source modules |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `bounds` | tuple | `(lon_min, lat_min, lon_max, lat_max)` |
| `bbox` | tuple | Alias for `bounds` |
| `module` | str | Data source name |

### Methods

#### `cutout.prepare(overwrite=False, n_scenes=6)`

Downloads and processes satellite scenes. This is the expensive step.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `overwrite` | bool | `False` | Re-download even if cached |
| `n_scenes` | int | `6` | Number of scenes (demo mode only) |

For `module="sentinel1"`, this tries the local cache first (fast, no credentials). Falls back to CDSE download if no cache exists.

#### `cutout.detect(method="trimmed_cfar", preset="balanced", **kwargs)`

Detects vessels in prepared scenes.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | str | `"trimmed_cfar"` | Detection algorithm: `"trimmed_cfar"` (v4) or `"cfar"` (v3.1) |
| `preset` | str | `"balanced"` | Parameter preset: `"balanced"`, `"precision"`, or `"recall"` |
| `k` | float | from preset | CFAR multiplier (higher = fewer detections) |
| `window` | int | from preset | Background window in pixels |
| `min_pixels` | int | from preset | Minimum vessel size in pixels |

**Returns:** `geopandas.GeoDataFrame` with columns:
- `geometry` — Point (lon, lat)
- `date` — scene date (YYYYMM)
- `npix` — vessel size in pixels
- `peak_db` — radar brightness in dB

#### `cutout.aggregate(detections=None, zones=None, freq="MS")`

Aggregates detections by zone and time period.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `detections` | GeoDataFrame | `None` (uses `self._detections`) | Output from `detect()` |
| `zones` | dict | `None` | `{"name": (lon_min, lat_min, lon_max, lat_max)}` |
| `freq` | str | `"MS"` | Pandas frequency: `"MS"` (monthly), `"W"` (weekly), `"D"` (daily) |

**Returns:** `pandas.DataFrame` indexed by period, one column per zone plus `total`.

#### `cutout.validate(detections=None, ais_vessels=None, threshold_m=500)`

Matches SAR detections to AIS vessels.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `detections` | GeoDataFrame | `None` | Output from `detect()` |
| `ais_vessels` | list | `None` | List of dicts with `lat` and `lon` keys |
| `threshold_m` | float | `500` | Maximum distance for a match (meters) |

**Returns:** dict with keys:
- `n_sar`, `n_ais` — input counts
- `matched_sar`, `matched_ais` — matched counts
- `precision` — matched_sar / n_sar (fraction of SAR that's real)
- `recall` — matched_ais / n_ais (fraction of AIS that's detected)
- `unmatched_sar`, `unmatched_ais` — unmatched counts

---

## `strait.Zones`

Container for zone definitions. Each zone is a bounding box `(lon_min, lat_min, lon_max, lat_max)`.

### Static methods

#### `Zones.singapore_strait()`

Returns zones validated against AIS for the Singapore Strait:

```python
{
    "port_core": (103.68, 1.20, 104.02, 1.34),    # main port area
    "eastern_opl": (104.00, 1.24, 104.35, 1.40),   # tanker anchorage (bunkering)
    "western_opl": (103.58, 1.10, 103.78, 1.32),   # western approaches
}
```

#### `Zones.rotterdam()`

Returns zones for the Port of Rotterdam approach.

#### `Zones.custom(zones)`

Define your own zones:

```python
zones = Zones.custom({
    "my_zone": (104.0, 1.24, 104.35, 1.40),
    "another": (103.68, 1.20, 104.02, 1.34),
})
```

---

## `strait.detect_vessels()`

Standalone detection function (bypasses Cutout for direct use).

```python
strait.detect_vessels(
    scenes,           # list of ndarray (float32, linear sigma0)
    dates,            # list of str (YYYYMM)
    land_mask,        # ndarray (bool: True=land)
    method="trimmed_cfar",
    bounds=None,      # (lon_min, lat_min, lon_max, lat_max)
    shape=(1500, 2400),
    k=5.5,
    window=64,
    min_pixels=3,
)
```

**Returns:** GeoDataFrame of vessel detections.

---

## `strait.PRESETS`

Parameter presets optimized via AIS ground-truth grid search (72 combinations, 2,145 vessels).

```python
PRESETS = {
    "balanced": {
        "k": 5.5, "window": 64, "min_pixels": 3,
        "description": "Economic indicators — 72% AIS match, F1=0.69",
    },
    "precision": {
        "k": 6.5, "window": 32, "min_pixels": 7,
        "description": "Dark vessel / enforcement — 84% AIS match",
    },
    "recall": {
        "k": 4.0, "window": 64, "min_pixels": 3,
        "description": "Census — maximum detections, 62% AIS match",
    },
}
```

---

## `strait.AISMatch`

Validates SAR detections against AIS vessel positions.

```python
matcher = AISMatch()
matcher._vessels = [{"lat": 1.25, "lon": 103.90, "name": "TEST"}, ...]
result = matcher.match(detections, threshold_m=500)
```

---

## Detection algorithms

### Trimmed CFAR (v4, recommended)

Two-pass censored statistics. Pass 1 computes a provisional threshold from robust global statistics. Pass 2 recomputes the local background excluding pixels above the provisional threshold. This prevents ships from masking their neighbors.

$$t_0 = \mathrm{median}(W) + K \cdot \mathrm{MAD}(W)$$
$$B = \{x \in W : x < t_0\}$$
$$T = \tilde{\mu}_B + k \cdot \tilde{\sigma}_B$$

Finds ~159% more vessels than classic CFAR in dense scenes.

### Classic CFAR (v3.1)

Local mean + k×sigma threshold in dB domain. Standard baseline from the SAR literature.

$$T = \max(\mu_B + k \cdot \sigma_B, -12 \text{ dB})$$

---

## Data source modules

### `strait.data.sentinel1.create_cache_from_directory()`

Builds a local cache from a directory of .tif scenes.

```python
from strait.data.sentinel1 import create_cache_from_directory

create_cache_from_directory(
    source_dir="path/to/scenes",       # .tif files
    cache_dir="~/.strait",             # where to store
    land_mask_path="path/to/mask.tif"  # optional
)
```

### `strait.data.sentinel1.load_local_scenes()`

Loads scenes from a local cache.

```python
from strait.data.sentinel1 import load_local_scenes

scenes, dates, land_mask = load_local_scenes(
    cache_dir="~/.strait",
    bounds=(103.55, 1.05, 104.35, 1.55),
    shape=(1500, 2400),
)
```
