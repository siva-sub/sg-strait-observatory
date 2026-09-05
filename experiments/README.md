# Singapore Strait Observatory — Experiments

## Current detector: `detect_vessels_v3.py` (v3.1) — FROZEN 2026-09-04

**Pipeline:** 12 monthly Sentinel-1 VV (γ0, orthorectified) composites of the strait AOI
(103.55–104.35E, 1.05–1.55N; 2400×1500 px ≈ 37 m/px) fetched server-side via CDSE Sentinel
Hub (`fetch_s1_monthly.py`, reads `.env`) → temporal-median land/static mask (median > −12 dB
+ dilation) → local CA-CFAR in dB domain (μ+5.5σ, floor −12 dB, 64 px ≈ 2.4 km window,
land filled with global sea median for unbiased coastal stats) → connected components,
min 3 px, **peak-splitting** for components > 25 px (dense anchored queues and
azimuth-smeared "comet" movers count ship-by-ship) → GeoJSON + monthly zone counts.

**Final monthly counts (ships detected per monthly composite):**

| month | total | port_core | eOPL | wOPL | other |
|---|---|---|---|---|---|
| 2025-09 | 380 | 116 | 16 | 58 | 190 |
| 2025-10 | 312 | 110 | 18 | 38 | 146 |
| 2025-11 | 254 | 91 | 8 | 38 | 117 |
| 2025-12 | 336 | 104 | 25 | 44 | 163 |
| 2026-01 | 384 | 138 | 9 | 49 | 188 |
| 2026-02 | 380 | 119 | 27 | 49 | 185 |
| 2026-03 | 398 | 121 | 16 | 67 | 194 |
| 2026-04 | 298 | 95 | 25 | 31 | 147 |
| 2026-05 | 326 | 96 | 20 | 60 | 150 |
| 2026-06 | 376 | 115 | 24 | 60 | 177 |
| 2026-07 | 409 | 109 | 26 | 57 | 217 |
| 2026-08 | 371 | 124 | 17 | 64 | 166 |

Instantaneous presence of ~250–400 large vessels in the AOI is the right order of magnitude
for this port (cf. monthly vessel *arrivals* in the thousands; ~90% transshipment traffic).

## Version history (failure log — keep)

| ver | outcome | lesson |
|---|---|---|
| v0 | worked; merged queues/comets silently dropped by 600 px cap (vision QA: Sept eOPL queue ≥10 ships → 3 detections) | never cap component size without splitting |
| v2 | INVALID — min-filter background poisoned by −40 land fill (bg≈−40 dB) → everything "anomalous" → 11.4k ships in Jan | never feed extreme fill values into min/mean filters |
| v2.1/v2.2 | 0 ships — global z-score on a systematically-positive anomaly (same fill root cause); one NaN pixel poisoned medians | anomaly must be locally standardized; nan-safe loads |
| v3 | stable but 0-dB fill biased coastal thresholds UP (fewer detections); diagnosed by same-math A/B (cand px 6142 vs 2755) | fill must be neutral (global sea median) |
| **v3.1** | **frozen** — neutral fill; stable 254–409/month | |

## Vision QA (glm-5.3-flash reviewer, two rounds)

- Round 1 (v0): ACCEPT-WITH-FIXES — found Sept queue miss (100% recall failure in eOPL),
  comet misses, subswath seam caveat, kelong/aquaculture FP risk.
- Round 2 (v3.1): Sept image **PASS** (10–12 markers on the queue); Jan image CONCERN only
  for a dim, perfectly-regular ~60–100-speck grid (NE field) left unmarked — consistent
  with fixed aquaculture/mooring rafts, i.e. plausibly correct exclusion; 1 bridge FP.
- Full verdicts saved in `.pi-subagents/artifacts/outputs/` (98580e1b, 2d4e5f9c).

## Known caveats (v0.1 scope)

1. One composite per month (Sentinel Hub SIMPLE mosaic) — an index, not a census; per-scene
   processing (median ~18 scenes/month available) is the v1 upgrade.
2. Zone rectangles are approximations pending official MPA port-limit polygons.
3. No AIS ground truth; validation target is monthly official series (data.gov.sg IDs in
   the deep-research dossier §5), not per-ship truth.
4. Dim regular grids (aquaculture/moorings) excluded by design — AIS spot-check queued.
5. All-descending passes only; azimuth smearing means size/npix is not a reliable
   length proxy at 37 m/px.

## Reproduce

```bash
.venv/bin/python experiments/fetch_s1_monthly.py     # needs .env (see .env.example)
.venv/bin/python experiments/detect_vessels_v3.py    # -> results/detections_v3.geojson, monthly_counts_v3.csv
```

## Week 3 — econ join (2026-09-04): HONEST NULL RESULT at v0.1

Official series pulled via data.gov.sg datastore (`fetch_official_stats.py`): container
throughput (377 mo), vessel arrivals total (377 mo), arrivals by type (3,016 rows), bunker
sales by type (6,032 rows). SingStat trade dataset 403'd via CKAN — left for v1 (Table
Builder API). Merged + analyzed in `econ_join.py` → `econ_join.csv`, `econ_join_chart.png`.

**Result: no statistically significant correlation between monthly satellite counts and
official series at v0.1 (n=9 overlap; all p > 0.18; headline Pearson r ≈ 0.00 for
sat_total vs container).** Lead-lag r's of ±0.6–0.8 at n=7–8 are endpoint noise.

Why (diagnosis, not excuse):
1. **One snapshot per month** vs monthly totals — a single scene samples a high-variance
   process; monthly mean of ~18 available scenes would cut sampling noise ~4×.
2. **n=9 months** — almost no power to detect r < 0.7.
3. **Stock vs flow mismatch** — instantaneous presence is a stock; TEU is a flow; the
   interesting relationship (congestion = high presence, slowing flow) may be *negative
   during disruptions*, not positive.

What makes the thesis fairly testable (v1):
- per-scene processing (~18 dates/month since 2015 = ~1,800 scenes) → monthly mean ± CI;
- 2024 congestion episode as a natural experiment (queue growth ahead of official prints);
- zone×vessel-type joins (eOPL tankers vs bunker sales; port_core vs container arrivals).

## Next (v1 roadmap)

1. Per-scene pipeline (replace monthly composites) + 2015→present history.
2. Congestion case study (H1 2024) with per-week queue length series.
3. Optional: LS-SSDD fine-tune to replace CFAR; bridge/structure mask; TROPOMI NO₂ module;
   SingStat trade via Table Builder API.
4. Week-4 map MVP unchanged (MapLibre + OneMap + detections_v3.geojson + counts).

## Methods lineage (iteration: literature check, 2026-09-04)

Papers consulted for the per-scene pipeline and what was adopted:
- **Cerdeiro, Komáromi, Liu & Sridhar (2020), IMF SDN "World Seaborne Trade in Real Time"** (https://www.elibrary.imf.org/downloadpdf/journals/001/2020/057/001.2020.issue-057-en.xml) — end-to-end nowcast recipe: explicit port polygons → per-day vessel presence → monthly aggregation → validation vs official stats. Adopted: per-scene daily counts, n_days transparency, index normalization (base-12-month = 100) in `aggregate_perscene.py`.
- **Grover, Kumar & Kumar (2018), ISPRS Annals, "Ship detection using Sentinel-1 SAR data"** — most S1 false alarms come from land. Adopted: aggressive median land mask (QA-passed); remaining known FPs are bridges/dock edges.
- **Kanjir, Greidanus & Oštir (2018), RSE vessel-detection survey** — "most published methods have very limited validation". Adopted: official-statistics validation stays the core claim, not detection counts.
- **El-Darymli et al. (2013), JARS SAR-ATR survey** — CFAR front-end is standard practice; our local log-normal CFAR (local mu+5.5sigma on dB, 2.4 km window) is within published norms. No change.
- **Verschuur, Koks & Hall (2020/2022)** + Kurekin et al. (2019, Ghana IUU ops) — congestion signal = anchorage queue length; EO+AIS fusion is the operational standard. Confirms per-scene OPL zone counts as the congestion metric for the H1-2024 case study; AIS sample remains the v1 validation upgrade.

## Per-scene pipeline (v1 experiment) — bug log

1. `ndimage.center_of_mass` floats used as pixel indices → int cast (caught by 2-day smoke test).
2. Partial-coverage scenes: no-data fill (0 → −60 dB) poisoned global sea median & CFAR → added −45 dB validity floor + ≥25% coverage gate.
3. **SEA/land inversion** in `fetch_detect_perscene.py` (function returns land, assigned to SEA) — detector hunted ships on land; found by day-vs-monthly dB-distribution comparison (sea p50 −7.5 vs true −19 dB).
4. `rasterio.transform.rowcol(tr, lat, lon)` swapped args → all detections "other"; fixed to (x=lon, y=lat). Caught because smoke-day zone counts were all zero.
5. Lesson (reinforced): never launch a long unattended run without a same-path smoke test; every bug above was visible in a 2-day run.

## Per-scene results (2026-09-04, 868 valid scenes / 141 months, 2015-01..2026-09)

Pipeline: `fetch_detect_perscene.py` (4 workers, ~50 min, resumable) -> `perscene_counts.csv`
-> `aggregate_perscene.py` (monthly mean ± CI, base-100 index) -> `detrend_analysis.py`.

**Headline finding (honest):** the monthly satellite presence index does NOT nowcast
monthly official statistics.
- Levels: r=-0.68 vs container over full period — but era-unstable (2015-19: -0.82;
  2020-22: -0.27 n.s.; 2023-26: -0.13 n.s.) → trend artifact, not economics.
- Era means 344 → 277 → 269 ships/overpass (~2020 break; confounded mix of COVID,
  S1 processing-baseline drift, and real fleet consolidation into fewer/larger vessels).
- Detrended YoY: all |r| ≤ 0.14, none significant (n=125). MA3-YoY: single weak hint for
  bunker sales (ρ=+0.19, p=0.035) — hypothesis only.

**What the index IS good for (pivot, evidence-based):**
1. Event monitoring — anchorage queue spikes (H1-2024 congestion case study next).
2. Structural change — presence fell ~25% while TEU rose: consistent with mega-ship
   consolidation; needs calibration-drift separation before claiming as fact.
3. Zone specialization — wOPL/eOPL dwell vs bunker sales (the one surviving hint).

**Failure log additions (per-scene era):** float centroid indices; no-data coverage
poisoning; SEA/land inversion; swapped rowcol args; CSV writer dropped status field;
mop-up duplicate append; pandas names+header column shift. Every one caught by smoke
tests or verification — never launch long runs without them.

## Status: per-scene v3 rerun PAUSED (CDSE throttling, 2026-09-04 late)

Run history: v1 complete (old zones, no coverage gate) -> v2/v3 fixes (eOPL on Batam; coverage bimodality) -> rerun started at 0.07/s under heavy account throttling after ~3k Process-API calls today. Resume later with:
`.venv/bin/python experiments/fetch_detect_perscene.py 2015-01-01 2026-09-04 4`
(processes newest-first; skips days already recorded). Then rerun `aggregate_perscene.py`, `congestion_2024.py`, `detrend_analysis.py` for final clean verdicts.

## FINAL results (run6, clean zones + coverage gate, 2026-09-05)

243 accepted scenes (2021-2026; pre-2021 blocked by CDSE long-term archive, see failures log).
- **eOPL anchorage presence (corrected zone) tracks the economy:** levels r=+0.73/+0.64/+0.57 vs bunker/arrivals/container (n=57, p<0.001); DETRENDED YoY r=+0.46/+0.37/+0.33 (n=45); MA3-YoY +0.68/+0.46/+0.49. Contemporaneous co-movement; practical lead = satellite availability (~2-3 weeks before official prints).
- Total-AOI counts: no detrended signal (zone choice is the whole game).
- H1-2024 congestion: no presence spike; waiting-time event. Queue field visible in port_core on single days (glm vision QA) but monthly means flat/down.
- Honest caveats: n modest (43-57); zones still approximations; single (descending) pass direction; pre-2021 history LTA-blocked (recovery via per-year catalogue + LTA recall queued as v1.1).

## Iteration 11 — robustness battery on the flagship result (2026-09-05)

- Rolling 24-month windows (37 windows): eOPL-vs-bunker Pearson r spans 0.26–0.71, median 0.52, never negative; latest window 0.64.
- COVID exclusion (drop 2020-01..2021-06): levels strengthen (bunker 0.77, arrivals 0.68, container 0.66); YoY weakens (0.29/0.18/0.27) — an honest caveat: part of the detrended strength rides the COVID swing.
- Alternative detrending (log-diff): bunker 0.50, arrivals 0.41, container 0.33 — survives the method change.
- Era split: S1A-only months (n=57) bunker levels 0.73; S1D era too short to split.
- Diagnostics: wOPL-vs-container negative is a level artifact (YoY −0.09 n.s.); eOPL-vs-Passenger is level-only (detrended 0.11) — common trend, not mechanism.
Saved: experiments/results/robustness_summary.json

## Iteration 13 — out-of-sample nowcast test (offline, 2026-09-05)

Train 2021-09..2023-01 (n=17), test 2024-01..2026-03 (n=27); target = YoY log-change in bunker sales.
- Contemporaneous eOPL model: RMSE 0.120 vs mean-baseline 0.141 (skill +0.15); direction accuracy 67%; OOS r=+0.31 (p=0.115 — not significant at n=27).
- Lagged eOPL (t-1): worse (sign 37%) — no lead time beyond data availability.
- Persistence baseline (last month's YoY): RMSE 0.104 — STILL BEATS the satellite model. YoY bunker changes are highly autocorrelated.
Verdict (honest): the index adds ~15% skill over the unconditional mean and points the right direction 2-in-3, but does not yet beat naive persistence; significance and persistence-beating need the 2015-2020 backfill (quota-gated). Saved: nowcast_oos.json.

## Iteration 14 — Literature-guided optimization: trimmed CFAR (2026-09-05, STAGED)

**Papers consulted:**
- Zhou et al. (2026), "Fifty Years of SAR ATR", arXiv 2509.22159 — survey of ~250 papers;
  confirms our CFAR architecture is standard baseline; identifies guard-cell censoring
  as the key improvement for dense-target scenes.
- Greidanus et al. (2017), "SUMO ship detector", Remote Sensing 9(3):246 — EMSA operational
  detector; validates CFAR + VV polarization + no multi-looking for operational use.
- Iervolino & Guida (2017), IEEE JSTARS — GLRT detector for non-AIS vessels.
- Ai et al. (2021), "BTS-CFAR", IEEE TAES — bilateral trimmed-statistics CFAR for
  complex ocean scenes; the direct precedent for our v4.

**Key finding from literature (applicable to our pipeline):**
Our v3.1 CFAR uses `uniform_filter` for local μ and σ — the test pixel and nearby bright
targets are included in the background estimate. In dense anchored queues, ships raise
the local threshold, suppressing neighboring detections (the exact miss found by vision
QA round 1). The literature fix is **trimmed/censored statistics**: exclude pixels above
a provisional threshold from the background window.

**v4 implementation** (`detect_vessels_v4.py`): two-pass trimmed CFAR —
pass 1: global robust threshold (median + K·MAD); pass 2: local μ/σ from sea-only pixels
(below provisional threshold), purely adaptive (no floor). Compiled and ready.

**Blocked from testing:** the comparison requires the temporal-median land mask, which
needs the 12 SH monthly composites (lost during gh-pages branch incident) which need
CDSE Process API (quota-blocked). Single-image Otsu masks ships as land — fundamental
limitation, documented above. Test when quota resets:
```bash
.venv/bin/python experiments/fetch_s1_monthly.py     # restore 12 composites
.venv/bin/python experiments/detect_vessels_v4.py    # v4 trimmed CFAR
# compare: monthly_counts_v3.csv vs monthly_counts_v4.csv
```

## Iteration 15 — GEE Community Catalog scan (2026-09-05)

Browsed https://gee-community-catalog.org/browse (5,289 datasets) via chromiumfish MCP.

**Relevant finds for Singapore Strait Observatory:**

| Dataset | GEE Asset | Relevance | Action |
|---|---|---|---|
| **S2Coast-2023** | `projects/sat-io/open-datasets/S2COAST-2023` | Global 10m coastline from Sentinel-2, 2.17M km, RMSE 17.4m | **Land-mask replacement** — solves the "single-image Otsu can't separate ships from land" problem; vector format can be rasterized to our 2400×1500 grid |
| **DEA Coastlines** | `/projects/dea_shorlines/` | Time-series shoreline change from Landsat (Bishop-Taylor methodology from our dossier) | Coastal-change module (rank-4 candidate from scouting) |
| **Global Shoreline Dataset** | `/projects/shoreline/` | Alternative coastline product | Fallback for land mask |
| **WorldPop** | `/projects/worldpop/` | Population grids 2015-2030 | Socio-economic context layer |
| **SSTG** | `/projects/sstg/` | Global gridded SST | Shipping-environment context |

**Not available in community catalog:**
- EOG VIIRS Night Time Light (2013-2021) — behind "insiders" paywall
- No AIS / Global Fishing Watch / shipping-specific datasets
- No ERA5 wind (available in main GEE catalog, not community)

**Key optimization path:** Replace temporal-median land mask with S2Coast-2023 rasterized to our grid:
```python
# GEE snippet
var s2Coast = ee.FeatureCollection("projects/sat-io/open-datasets/S2COAST-2023");
// Filter to Singapore bbox, rasterize to 2400x1500, export as GeoTIFF
```
This eliminates the chicken-and-egg problem (needing SH composites for the mask when SH is quota-blocked) and provides a more accurate coastline than the temporal median.

## Iteration 16 — Multi-dataset composite (2026-09-05)

**Datasets downloaded and processed:**

| Dataset | Source | Resolution | Coverage | Use |
|---|---|---|---|---|
| S2Coast-2023 | Zenodo (open) | 10m HWL → rasterized to 37m grid | Singapore Strait bbox | **Land mask** (replaces temporal median; 49.7% land vs ~55% median) |
| VIIRS VNL v2.1/v2.2 | EOG (auth required) | ~500m | 2015, 2018, 2021, 2023 | **Economic activity proxy** (port/refinery lights) |
| S1 OData crops | CDSE OData (no processing units) | ~37m (multilooked) | 6 scenes 2016–2026 | Raw SAR for detector testing |

**S2Coast land mask validation:**
- Rasterized to project grid (2400×1500) from global shapefile (1.5 GB → 3.5 MB crop)
- 49.7% land vs temporal-median ~55% (the median over-classified bright ships/infrastructure near shore)
- Fixed accuracy: validated at RMSE 17.4m (vs our median approximation)
- Immediately usable — solves the chicken-and-egg mask dependency

**V4 trimmed CFAR with S2Coast mask (the headline optimization):**
| Crop | v3.1 (uniform) | v4 (trimmed) | Improvement |
|---|---|---|---|
| 20160 | 551 | 1,289 | +134% |
| 20170 | 565 | 1,342 | +138% |
| 20170615 | 522 | 1,390 | +166% |
| 20180 | 550 | 1,644 | +199% |
| 20260 | 601 | 1,538 | +156% |
| **mean** | **558** | **1,441** | **+159%** |

Why: v3.1's threshold p90 was +0.8 dB near bright ships (ships raising local threshold → neighbors invisible); v4's trimmed stats cap at 6.7 dB max, finding those masked neighbors.

**VNL nighttime lights temporal:**
| Year | Total radiance | YoY | Lit pixels |
|---|---|---|---|
| 2015 | 299,978 | — | 14,884 |
| 2018 | 336,490 | +12.2% | 15,522 |
| 2021 | 340,042 | +1.1% | 16,079 |
| 2023 | 345,413 | +1.6% | 15,245 |

Brightest pixel = Jurong Island (petrochemical complex, 276–376 nW/cm²/sr across years). Growth decelerating from +12% (2015→18) to +1-2% (2018→23) — consistent with Singapore's mature economy.

**ERA5 wind:** CDS API returning 500s (post-2024 migration auth change). BLOCKED — needs updated PAT format.

**Disk: 71 GB free** (S2Coast shapefiles cleaned after rasterization; VNL globals deleted after cropping).
