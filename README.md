# Singapore Strait Observatory

**Ships at anchor off Singapore, counted from free satellite radar — and they track the port's economy.**

Sentinel-1 SAR vessel detections in the Singapore Strait (night- and cloud-proof), joined to 30 years of
official monthly statistics (MPA / SingStat, open data). Built end-to-end from scratch: CDSE catalogue →
server-side processing → CFAR detector (7 documented failures deep) → econometric validation with honest
detrending.

## Headline result

Anchorage presence in the **eastern OPL** (open water NE of Batam) co-moves with Singapore's official
statistics — robust to detrending (not just trend-riding):

| eOPL ships vs | Levels (n=57) | YoY detrended (n=45) | MA3-YoY (n=43) |
|---|---|---|---|
| **Bunker sales** | **r = +0.73** | +0.46 | **r = +0.68** |
| Vessel arrivals | +0.64 | +0.37 | +0.46 |
| Container throughput (TEU) | +0.57 | +0.33 | +0.49 |

All p ≤ 0.027. Honest caveats: contemporaneous co-movement (no lead-time claim beyond satellite data
arriving ~2–3 weeks before official prints); zone rectangles are approximations; single (descending)
pass direction; pre-2021 archive partially blocked (CDSE long-term archive).

**Nulls reported, not hidden:** total-AOI counts show *no* detrended signal (zone choice is the whole
game), and the famous **H1-2024 congestion episode shows no anchorage-count spike** in any zone — with
official container-vessel arrivals equally flat, it was a waiting-time event, invisible to count series.

## Pipeline

```
CDSE OData catalogue (862 overpass days, 2015–2026)
  → Sentinel Hub Process API (per-scene VV γ0 crops, ~13 MB each)
  → temporal-median land mask + local CFAR (μ+5.5σ on dB) + peak-splitting   [detector v3.1]
  → anchorage-zone counts per scene (coverage-gated ≥ 0.80)
  → monthly index (mean ± 95% CI) → join with official series → detrended econometrics
  → MapLibre map + charts (web/)
```

## The honest arc (why this repo is worth reading)

The detector went through **seven documented failures**, each caught by a smoke test, an A/B diagnostic,
or a vision-model review — land/sea mask inversion, fill-value poisoning, float pixel indices, a zone
rectangle sitting on Batam island, coverage bimodality (36% vs 93%), a CSV schema drift, and a
self-matching `pkill`. Full failure log: [`experiments/README.md`](experiments/README.md) and
[`CHANGELOG.md`](CHANGELOG.md). The first "null result" verdict was produced by a bad zone; the final
positive result only appeared after the fix. Science-arc, not demo-ware.

## Repo layout

- `web/` — interactive map (MapLibre, month slider, corrected zones) + result charts
- `experiments/` — fetch/detect/aggregate/congestion/detrend scripts, results, QA images, README
- `outputs/` — deep-research dossier + provenance (dataset IDs, citations, risk register)
- `CHANGELOG.md` — full session lab notebook

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

Copernicus Sentinel-1 (ESA, via Copernicus Data Space Ecosystem — free/open) · MPA & SingStat via
data.gov.sg (Singapore Open Data Licence) · basemap CARTO/©OpenStreetMap · method lineage documented in
`experiments/README.md` (IMF/Cerdeiro et al. 2020 index design; Grover et al. 2018; Kanjir et al. 2018;
Georgoulias et al. 2020; Batista et al. 2025).

*Personal portfolio project — not affiliated with MPA, ESA, or any official body.*
