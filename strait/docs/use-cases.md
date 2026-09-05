# Use Cases

Five complete workflows showing what strait can do, with runnable code.

---

## Use Case 1: Port Activity Monitoring

**Who:** A trade analyst, port authority, or logistics company.
**Question:** Is port activity increasing or decreasing?

This is the primary use case — turning satellite detections into a monthly activity index.

```python
import strait

# Define the port area
cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.55, 104.35),   # Singapore Strait
    y=slice(1.05, 1.55),
    time=slice("2021-01", "2026-09"),
    path="~/.strait"           # local cache
)

# Download and process scenes
cutout.prepare()

# Detect vessels (balanced preset for economic indicators)
detections = cutout.detect(preset="balanced")

# Count by zone and month
zones = strait.Zones.singapore_strait()
monthly = cutout.aggregate(detections, zones=zones, freq="MS")

# The "total" column is your port activity index
print(monthly[["port_core", "eastern_opl", "total"]].describe())
```

**What you get:** A monthly time series of vessel counts per zone. The total is a proxy for overall port activity; individual zones track specific activities (container berths, bunkering anchorages, etc.).

**How to interpret it:**
- **Rising counts** = more vessels at anchor = increasing activity
- **Falling counts** = fewer vessels = decreasing activity or congestion clearing
- **Sudden spikes** = congestion (vessels waiting for berths) or seasonal peaks
- **Zone-specific changes** = shifts in trade patterns (e.g., more tankers = more fuel demand)

---

## Use Case 2: Anchorage Congestion Detection

**Who:** A shipping line, port operations team, or maritime insurer.
**Question:** Are anchorages getting congested? Should vessels divert?

```python
import strait

cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.55, 104.35),
    y=slice(1.05, 1.55),
    time=slice("2024-01", "2024-12"),
    path="~/.strait"
)
cutout.prepare()

# Use recall preset — catch every vessel, false positives less critical
detections = cutout.detect(preset="recall")

# Focus on the anchorage zones
zones = strait.Zones.singapore_strait()
monthly = cutout.aggregate(detections, zones=zones)

# Detect congestion: compare to rolling baseline
baseline = monthly["eastern_opl"].rolling(3).mean().shift(1)
current = monthly["eastern_opl"]
congestion_ratio = current / baseline

# Flag months with >20% above baseline
alerts = congestion_ratio[congestion_ratio > 1.2]
print(f"Congestion alert months: {list(alerts.index)}")
```

**What you get:** Months where anchorage occupancy exceeds a rolling baseline. A ratio >1.2 means 20% more vessels than the recent average.

**Important caveat from our research:** During the H1-2024 Singapore congestion episode (which made global news), monthly anchorage counts did NOT spike. The congestion was in **waiting time**, not in vessel count. Count-based metrics capture volume, not delay. For true congestion measurement, you need vessel-level dwell time (see Use Case 4).

---

## Use Case 3: Dark Vessel Detection

**Who:** A maritime authority, fisheries enforcement, or sanctions monitoring team.
**Question:** Which SAR detections don't match any AIS-broadcasting vessel?

```python
import strait
import json

cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.55, 104.35),
    y=slice(1.05, 1.55),
    time=slice("2024-01", "2024-03"),
    path="~/.strait"
)
cutout.prepare()

# Use precision preset — we want high-confidence detections only
# (84% AIS match rate means most detections are real vessels)
detections = cutout.detect(preset="precision")

# Load AIS positions (from AISStream.io or AISHub)
with open("ais_snapshot.json") as f:
    ais_data = json.load(f)
ais_vessels = [v for v in ais_data["vessels"] if v.get("lat")]

# Match SAR detections to AIS
result = cutout.validate(
    detections=detections,
    ais_vessels=ais_vessels,
    threshold_m=2000  # 2km threshold for "matched"
)

print(f"SAR detections: {result['n_sar']}")
print(f"Matched to AIS: {result['matched_sar']} ({result['precision']*100:.0f}%)")
print(f"Unmatched (dark vessels): {result['unmatched_sar']}")
```

**What you get:** The count of SAR detections with no AIS vessel within the matching radius. These are potential dark vessels — ships with AIS turned off, fishing vessels without transponders, or vessels in AIS receiver coverage gaps.

**Important nuance:** "Unmatched" doesn't mean "illegal." It means "SAR sees something AIS doesn't." In our Singapore data:
- The eastern anchorage had **zero** AIS vessels from one receiver network
- But a different receiver network showed **4,240** vessels there
- The "dark vessels" were actually just an AIS receiver coverage gap

**Before concluding "dark vessel," check:** Is the area within AIS receiver range? Are there known coverage gaps? Could the detection be a fixed structure (platform, aquaculture)?

---

## Use Case 4: Bunkering Activity Estimation

**Who:** A fuel trader, bunker supplier, or energy analyst.
**Question:** How much bunkering (ship-to-ship fuel transfer) is happening?

This is the most economically validated use case — our research showed satellite-derived anchorage counts explain 48% of Singapore's bunker sales variance.

```python
import strait
import pandas as pd
from scipy import stats

cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.55, 104.35),
    y=slice(1.05, 1.55),
    time=slice("2021-01", "2026-09"),
    path="~/.strait"
)
cutout.prepare()
detections = cutout.detect(preset="balanced")

# Focus on the tanker anchorage (bunkering zone)
zones = strait.Zones.singapore_strait()
monthly = cutout.aggregate(detections, zones=zones)

# Load official bunker sales
bunker = pd.read_csv("bunker_sales.csv", index_col=0, parse_dates=True)

# Correlate satellite index with bunker sales
merged = monthly.join(bunker, how="inner")
r, p = stats.pearsonr(merged["eastern_opl"], merged["bunker_sales"])
print(f"eOPL anchorage vs bunker sales: r={r:+.2f} (p={p:.4f})")

# Build a simple nowcasting model
import numpy as np
X = np.column_stack([np.ones(len(merged)), merged["eastern_opl"]])
beta = np.linalg.lstsq(X, merged["bunker_sales"], rcond=None)[0]
predicted = X @ beta
r_squared = 1 - np.sum((merged["bunker_sales"] - predicted)**2) / \
               np.sum((merged["bunker_sales"] - merged["bunker_sales"].mean())**2)
print(f"Satellite-only model R² = {r_squared:.3f}")
```

**What you get:** A correlation coefficient and an R² showing how much of the bunker sales variance is explained by satellite-detected anchorage occupancy alone.

**Our validated results (Singapore, 2021-2026, n=57 months):**

| Metric | Value |
|---|---|
| Pearson r (levels) | +0.73 |
| Detrended r (YoY) | +0.46 |
| R² (satellite-only model) | 0.478 |
| R² (with official tanker arrivals) | 0.700 |
| Partial r (controlling for wind) | +0.696 |

**Key insight:** The signal comes specifically from the **tanker anchorage zone**, not from total vessel counts. Zone choice is critical.

---

## Use Case 5: Research and Time Series Analysis

**Who:** An academic researcher or econometrician.
**Question:** Build a reproducible vessel-presence time series for econometric modeling.

```python
import strait
import pandas as pd
import numpy as np
from scipy import stats

cutout = strait.Cutout(
    module="sentinel1",
    x=slice(103.55, 104.35),
    y=slice(1.05, 1.55),
    time=slice("2021-01", "2026-09"),
    path="~/.strait"
)
cutout.prepare()
detections = cutout.detect(preset="balanced")
zones = strait.Zones.singapore_strait()
monthly = cutout.aggregate(detections, zones=zones)

# ── Detrended correlation (removes trend contamination) ──
# Year-over-year log differences
dl = np.log(monthly[["eastern_opl", "total"]].clip(lower=1e-6)).diff(12).dropna()

# Correlate detrended satellite with detrended official data
official_dl = np.log(official_monthly.clip(lower=1e-6)).diff(12).dropna()
merged = dl.join(official_dl, how="inner")

for sat_col in ["eastern_opl", "total"]:
    for off_col in ["bunker_sales", "container_throughput"]:
        r, p = stats.pearsonr(merged[sat_col], merged[off_col])
        print(f"  {sat_col} vs {off_col}: r={r:+.2f} (p={p:.3f})")

# ── Rolling window stability ──
window = 24  # months
for i in range(len(monthly) - window):
    w = monthly.iloc[i:i+window]
    r = stats.pearsonr(w["eastern_opl"], w["bunker_sales"])[0]
    print(f"  Window {monthly.index[i]} to {monthly.index[i+window-1]}: r={r:+.2f}")

# ── Weather robustness (partial correlation) ──
wind = pd.read_csv("wind_monthly.csv", index_col=0)
d = monthly[["eastern_opl", "bunker_sales"]].join(wind).dropna()
r_xy = np.corrcoef(d["eastern_opl"], d["bunker_sales"])[0,1]
r_xw = np.corrcoef(d["eastern_opl"], d["wind"])[0,1]
r_yw = np.corrcoef(d["wind"], d["bunker_sales"])[0,1]
partial = (r_xy - r_xw * r_yw) / np.sqrt((1 - r_xw**2) * (1 - r_yw**2))
print(f"  Partial r (controlling for wind): {partial:+.3f}")
```

**What you get:** A complete econometric analysis with detrended correlations, rolling window stability checks, and weather-robustness tests. This is the workflow used in our paper.

**Reproducibility:** The entire pipeline (download → detect → aggregate → analyze) is scripted and version-controlled. The strait package on PyPI ensures the same detection code runs on any machine.
