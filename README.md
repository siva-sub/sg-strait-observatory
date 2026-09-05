# Singapore Strait Observatory

**Ships anchored off Singapore, counted from free satellite radar — and the count tracks the port's economy.**

**Live map:** https://siva-sub.github.io/sg-strait-observatory/

I count vessels at anchor in the Singapore Strait using Sentinel-1 SAR, which works at
night, sees through cloud, and costs nothing. Then I compare those counts with thirty
years of official monthly statistics published on data.gov.sg by Singapore's port and
statistics agencies.

The first result was a null. The first result was also wrong: my eastern anchorage
zone was drawn over Batam island, so I was correlating land with trade statistics.
When the box moved onto open water, the signal appeared.

## Headline result

A single satellite radar explains **48% of Singapore's bunker sales** — no weather
control needed, no trend-riding.

| Model | R² | What it means |
|---|---|---|
| bunker ~ eOPL (satellite only) | **0.478** | Radar alone explains 48% |
| bunker ~ eOPL + ERA5 wind | 0.495 | Weather adds almost nothing |
| bunker ~ eOPL + wind + tanker arrivals | **0.700** | Practical nowcasting model |

| eOPL ships vs | Levels (n=57) | YoY detrended (n=45) | MA3-YoY (n=43) |
|---|---|---|---|
| **Bunker sales** | **r = +0.73** | +0.46 | **r = +0.68** |
| Vessel arrivals | +0.64 | +0.37 | +0.46 |
| Container throughput (TEU) | +0.57 | +0.33 | +0.49 |
| **Tanker arrivals (mechanism)** | **+0.64** | **+0.53** | — |

All p ≤ 0.027. The tanker-specific link is the mechanism: anchored tankers ARE
bunkering operations. Wind control strengthens the signal (partial r = +0.70).
The rolling-24-month correlation never goes negative (median +0.52).

The link is strongest where the mechanism is: the eastern anchorage (open water
NE of Batam) tracks tanker arrivals at r = +0.53 detrended, while the western
anchorage and port zones show no type link at all. Zone choice is the entire game.

Counts over the whole strait show no detrended signal — because total-area counts
pick up wind-driven rough-sea false positives (r = +0.37 vs ERA5 wind). The eOPL
zone doesn't (r = +0.02 vs extreme wind). This is why the economic signal is clean.

## Pipeline

```
CDSE OData catalogue (862 overpass days, 2015–2026)
  → Sentinel Hub Process API (per-scene VV γ0 crops, ~13 MB each)
  → temporal-median land mask + trimmed CFAR (two-pass censored) + peak-splitting   [v4]
  → anchorage-zone counts per scene (coverage-gated ≥ 0.80)
  → monthly index (mean ± 95% CI) → join with official series → detrended econometrics
  → MapLibre map + charts (web/)
```

## How it went

The detector is at v4 (trimmed CFAR). It got there the slow way. v0 silently dropped dense anchored
queues, because a 600-pixel component cap discarded anything a queue merged into.
Some scenes covered 36% of the area and others 93%, and for a while the monthly
averages quietly mixed them. v2's background estimate was poisoned by a fill value,
and one January reported 11,471 ships. At one point the land and sea flags were inverted, and the detector
spent an afternoon hunting ships on Singapore Island. A `pkill` pattern that matched
its own shell made three commands vanish mid-run before anyone knew why. A
vision-model review of the maps caught the Batam zone error when the numbers would
not. The v4 upgrade (trimmed CFAR from the SAR literature) came after the 50-year
survey identified that ships in dense queues raise the local threshold and hide their
neighbors; trimming them out finds 159% more. The S2Coast-2023 land mask from Zenodo
replaced a temporal-median approximation that was drawing anchorage boxes over Batam
Island. Each of the failures was caught by a two-day smoke test, an A/B diagnostic,
or a fresh pair of eyes on an image. The full log, with the numbers each bug produced,
is in [`experiments/README.md`](experiments/README.md) and
[`CHANGELOG.md`](CHANGELOG.md).

I also caught my own artifact. When the first historical data points (2016-2018,
processed with the newer v4 detector) were added to the 2021+ data (processed with
v3.1), the "mega-ship consolidation" trend I had reported in the scouting phase
flipped direction. It was a detector-version mismatch, not a real economic signal.
The calibrated analysis is in `experiments/README.md` iteration 21.

## Repo layout

- `web/` — interactive map (MapLibre, month slider, corrected zones) + result charts
- `experiments/` — fetch, detect, aggregate, congestion, and detrend scripts, with results and QA images
- `outputs/` — deep-research dossier + provenance (dataset IDs, citations, risk register)
- `CHANGELOG.md`: the lab notebook, kept as it happened

## Reproduce

```bash
cp .env.example .env      # CDSE credentials (free account)
python3 -m venv .venv && .venv/bin/pip install numpy scipy rasterio requests pandas matplotlib
.venv/bin/python experiments/fetch_s1_monthly.py        # or fetch_detect_perscene.py for full history
.venv/bin/python experiments/fetch_official_stats.py
.venv/bin/python experiments/detect_vessels_v3.py
.venv/bin/python experiments/aggregate_perscene.py && .venv/bin/python experiments/detrend_analysis.py
```

## Data & credits

Copernicus Sentinel-1 (ESA, via CDSE OData and Sentinel Hub — free and open)
· VIIRS nighttime lights (EOG, Earth Observation Group)
· ERA5 wind (Copernicus Climate Data Store)
· S2Coast-2023 coastline (Zenodo, Duan et al. 2026)
· MPA and SingStat via data.gov.sg (Singapore Open Data Licence)
· Open-Meteo historical weather archive
· basemap CARTO / ©OpenStreetMap contributors.
Method lineage with citations is in `experiments/README.md`:
Cerdeiro et al. 2020 (IMF) for index design; Grover et al. 2018 for land-mask doctrine;
Kanjir et al. 2018 for the validation-first framing; El-Darymli et al. 2013 for CFAR
as standard; Georgoulias et al. 2020 and Batista et al. 2025 for per-ship NO₂ plumes;
Zhou et al. 2026 (arXiv 2509.22159) for the trimmed-CFAR optimization.

Personal portfolio project. Not affiliated with MPA, ESA, or any official body.
