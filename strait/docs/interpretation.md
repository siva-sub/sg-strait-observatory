# Interpreting Results

How to read strait's output and what the numbers actually mean.

## Detection output

Each detection is one vessel candidate:

| Field | Type | What it means | What to check |
|---|---|---|---|
| `geometry` | Point (lon, lat) | Where the vessel is | Should be within your bounding box |
| `date` | string (YYYYMM) | Which scene it was detected in | Should match your time range |
| `npix` | int | How many pixels the vessel occupies | Proxy for vessel size (≥3 = detectable) |
| `peak_db` | float | Radar brightness in dB | Brighter = larger/metallic vessel |

### What npix tells you

At ~37 m/pixel resolution:
- 3-5 px = small vessel (~110-185 m: tug, barge, fishing boat)
- 6-15 px = medium vessel (~220-550 m: feeder container, product tanker)
- 16-50 px = large vessel (590-1850 m: VLCC, ULCS, bulk carrier)

**Caveat:** Azimuth smearing (the radar side-view) can elongate vessels, making them appear larger than they are. Don't use npix alone for classification.

### What peak_db tells you

Typical radar brightness values (sigma0 in dB):

| Range (dB) | Likely target |
|---|---|
| < -15 | Sea surface (background) |
| -15 to -8 | Small vessel, wooden boat, calm-water artifact |
| -8 to 0 | Medium vessel (steel hull) |
| > 0 | Large vessel, metal structure, corner reflector |

## Zone aggregation output

The `aggregate()` function returns a pandas DataFrame:

```
zone        eastern_opl  port_core  western_opl  other  total
period
2021-01-01          85        120           71    114    390
2021-02-01          82        115           65    105    367
...
```

Each column is a zone you defined. The `total` column is all detections combined.

### Key lesson from our research: zone choice matters enormously

In the Singapore project:
- **Total-area counts showed NO economic signal** (detrended r ≈ 0)
- **Anchorage-zone counts showed strong signal** (detrended r = +0.46)

Why? Total counts include vessels in transit lanes, berthed at terminals, and in rough-sea areas where wind creates false positives. Anchorage-zone counts capture only vessels at anchor — the population that correlates with port activity.

**Rule of thumb:** Define zones around known anchorage areas (where ships wait), not the entire port. Use AIS data to find where vessels actually anchor.

## Preset selection

| Preset | k | Window | Min px | AIS match | Use when |
|---|---|---|---|---|---|
| balanced | 5.5 | 64 | 3 | 72% | General port monitoring, economic indicators |
| precision | 6.5 | 32 | 7 | 84% | Dark vessel detection, enforcement (high confidence) |
| recall | 4.0 | 64 | 3 | 62% | Census counting, change detection (maximum coverage) |

**The trade-off:** Higher precision means fewer detections but more confidence each one is real. Higher recall means more detections but more false positives (rough sea, wave crests, coastal reflections).

**How to choose:** If false positives are expensive (enforcement action, alert systems), use precision. If missing a vessel is expensive (congestion monitoring, census), use recall.

## AIS validation output

The `validate()` function returns:

```python
{
    "threshold_m": 500,       # matching radius used
    "n_sar": 371,             # total SAR detections
    "n_ais": 96,              # total AIS vessels
    "matched_sar": 38,        # SAR detections with AIS within threshold
    "matched_ais": 42,        # AIS vessels with SAR within threshold
    "precision": 0.10,        # matched_sar / n_sar
    "recall": 0.44,           # matched_ais / n_ais
    "unmatched_sar": 333,     # potential dark vessels or AIS coverage gaps
    "unmatched_ais": 54,      # AIS vessels SAR missed (too dim, too small)
}
```

### Reading precision and recall

**Low precision (many unmatched SAR):** Could mean:
- AIS receiver coverage gap (most common)
- False positives from rough sea, coastal reflections
- Small vessels without AIS (fishing boats, barges)
- Temporal mismatch (SAR from August, AIS from today)

**Low recall (many missed AIS vessels):** Could mean:
- Vessels too small or dim for the CFAR threshold
- Vessels berthed at terminals (hidden by port structures)
- Vessels in dense clusters (merged into single detections)
- The detection preset is too conservative

### Temporal mismatch is the biggest confound

SAR scenes are from specific dates. AIS captures are from right now. If there's a weeks-to-months gap:
- Anchored vessels may have departed and been replaced
- The spatial pattern is similar but individual vessels differ
- Expect precision/recall to be 10-30% lower than same-day matching

**Best practice:** For meaningful validation, capture AIS on the same day as (or within 1-2 days of) the SAR scene.

## Correlation analysis

When you correlate monthly anchorage counts with official statistics:

### Levels vs detrended

**Levels correlation** (raw values, no detrending):
- Captures the overall association
- Vulnerable to "two things going up over time" (trend contamination)
- Our result: r = +0.73 (looks strong, but could be spurious)

**Detrended correlation** (year-over-year differences):
- Removes long-term trends
- Tests whether *changes* in satellite counts predict *changes* in official stats
- Our result: r = +0.46 (weaker, but more trustworthy)

**Always report both.** If levels are high but detrended is near zero, the "correlation" may just be two upward trends.

### Statistical significance

With n=57 months (our sample):
- |r| > 0.26 is significant at p < 0.05
- |r| > 0.34 is significant at p < 0.01

With smaller samples (n < 30), you need |r| > 0.36 for p < 0.05.

**Be cautious with small samples.** Our out-of-sample nowcast (n=27) showed r = +0.31 — suggestive but not statistically significant (p = 0.115).

### What "R² = 0.478" actually means

R² = 0.478 means satellite data alone explains 47.8% of the variance in bunker sales. The remaining 52.2% is due to factors the satellite index doesn't capture:
- Bunker prices (demand elasticity)
- Vessel size differences (a large tanker delivers more fuel than a small one)
- Multi-visit bunkering (same vessel bunkers multiple times per month)
- Bunkering outside the monitored zone

**R² is not a quality score.** It's a measure of how much unique information the satellite index adds beyond what a constant (mean) would give you.

## Common pitfalls

1. **Using total-area counts instead of zone-specific counts.** Total counts mix transit traffic with anchored vessels and are contaminated by weather. Zone counts isolate the signal.

2. **Interpreting a high Pearson r as "the satellite predicts trade."** It means "satellite counts and trade stats move together." For prediction, you need out-of-sample testing against a baseline (see our negative result: persistence beats the satellite model).

3. **Assuming unmatched detections are "dark vessels."** Check AIS receiver coverage first. In our data, the biggest "dark vessel" signal was actually a receiver gap.

4. **Mixing detector versions.** Different CFAR parameters produce different scale counts. If you add scenes processed with different settings, your time series will have a discontinuity. Use consistent parameters throughout.

5. **Ignoring wind.** High wind creates brighter sea clutter, increasing false positives. Total-area counts are wind-sensitive (r = +0.37 with wind speed). Anchorage-zone counts should be less wind-sensitive — verify this for your port.
