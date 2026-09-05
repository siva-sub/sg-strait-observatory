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

Anchorage presence in the eastern outer port limit (open water northeast of Batam)
co-moves with Singapore's official statistics, and the relationship survives
detrending, which is the test that matters: it is not two trends moving together.

| eOPL ships vs | Levels (n=57) | YoY detrended (n=45) | MA3-YoY (n=43) |
|---|---|---|---|
| **Bunker sales** | **r = +0.73** | +0.46 | **r = +0.68** |
| Vessel arrivals | +0.64 | +0.37 | +0.46 |
| Container throughput (TEU) | +0.57 | +0.33 | +0.49 |

All p ≤ 0.027. The lead-lag profile peaks at zero lag, so I make no leads-by-a-month
claim; the practical edge is that satellite scenes exist 2–3 weeks before
the official prints. The link is strongest where the mechanism is: against tanker
arrivals specifically it reaches r = +0.53 detrended (p < 0.001), while the western
anchorage and port zones show no type link at all. Anchored tankers are bunkering
operations. Zone rectangles are approximations pending official port-limit
polygons. Only descending passes cover this area. The pre-2021 archive is partially
blocked by Copernicus long-term-archive retrieval.

Counts over the whole strait show no detrended signal. Where you put the box is the
entire game. And the H1-2024 congestion episode, the one that made global headlines,
shows **no anchorage-count spike in any zone**: official container-vessel arrivals
were equally flat (1,087–1,274 per month). It was a waiting-time event, and
count-based series cannot see it from either side.

## Pipeline

```
CDSE OData catalogue (862 overpass days, 2015–2026)
  → Sentinel Hub Process API (per-scene VV γ0 crops, ~13 MB each)
  → temporal-median land mask + local CFAR (μ+5.5σ on dB) + peak-splitting   [detector v3.1]
  → anchorage-zone counts per scene (coverage-gated ≥ 0.80)
  → monthly index (mean ± 95% CI) → join with official series → detrended econometrics
  → MapLibre map + charts (web/)
```

## How it went

The detector is at v3.1. It got there the slow way. v0 silently dropped dense anchored
queues, because a 600-pixel component cap discarded anything a queue merged into.
Some scenes covered 36% of the area and others 93%, and for a while the monthly
averages quietly mixed them. v2's background estimate was poisoned by a fill value,
and one January reported 11,471 ships. At one point the land and sea flags were inverted, and the detector
spent an afternoon hunting ships on Singapore Island. A `pkill` pattern that matched
its own shell made three commands vanish mid-run before anyone knew why. A
vision-model review of the maps caught the Batam zone error when the numbers would
not. Each of the seven
failures was caught by a two-day smoke test, an A/B diagnostic, or a fresh pair of
eyes on an image. The full log, with the numbers each bug produced, is in
[`experiments/README.md`](experiments/README.md) and
[`CHANGELOG.md`](CHANGELOG.md).

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

Copernicus Sentinel-1 (ESA, via the Copernicus Data Space Ecosystem, free and open)
· MPA and SingStat via data.gov.sg (Singapore Open Data Licence) · basemap CARTO /
©OpenStreetMap contributors. Method lineage, with citations, is documented in
`experiments/README.md`: index design follows Cerdeiro et al. 2020 (IMF); land-mask
false-alarm doctrine from Grover et al. 2018; the validation-first framing responds
to Kanjir et al. 2018; CFAR as standard front-end per El-Darymli et al. 2013; per-ship
NO₂ plumes from Georgoulias et al. 2020 and the maritime-emissions review by Batista
et al. 2025.

Personal portfolio project. Not affiliated with MPA, ESA, or any official body.
