# Draft Plan: singapore-strait-observatory

## Slug
`singapore-strait-observatory`

## Proposed Title
Sentinel-1 Anchorage Presence as a Leading Economic Indicator: Evidence from the Singapore Strait

## Sections

### 1. Abstract
- One-paragraph summary: SAR-derived anchorage counts track bunker sales at r=+0.73 (Spearman), survive detrending, validated against AIS
- Key number: R²=0.478 for satellite-only model

### 2. Problem Statement
- Official trade statistics lag by 2-4 weeks
- AIS has receiver coverage gaps
- Existing satellite-trade work (IMF/World Bank) uses AIS, not raw SAR detection
- Gap: no open-source, reproducible pipeline for SAR-based port activity nowcasting

### 3. Related Work
- IMF/World Bank trade-from-space (Arslanalp et al. 2021; Cerdeiro et al. 2020)
- SAR vessel detection literature (El-Darymli et al. 2013; Zhou et al. 2026 survey)
- SAR-AIS fusion for dark vessel detection (Rodger & Guida 2020; Galdelli et al. 2021)
- Bunkering statistics from AIS (Feng et al. 2020)
- ERA5 wind as covariate (atlite inspiration)

### 4. Method
- Trimmed CFAR detector (two-pass censored statistics)
- S2Coast-2023 land mask (Zenodo)
- Sentinel-1 via CDSE (Sentinel Hub + OData)
- Zone-based aggregation
- AIS validation (live + historical)
- Multi-sensor fusion (SAR + VIIRS + ERA5)
- Include: architecture diagram (Mermaid), parameter optimization table

### 5. Evidence
- Headline: R²=0.478 (satellite-only), 0.700 (with official tanker arrivals)
- Detrended: r=+0.46 (YoY), +0.68 (MA3-YoY)
- Tanker mechanism: r=+0.53 detrended
- Weather robustness: partial r=+0.696 controlling for ERA5 wind
- Rolling 24-month: median +0.52, never negative
- AIS validation: 84% precision preset, 72% balanced preset
- Historical AIS: eOPL confirmed as tanker anchorage (77% tankers, 4,240 vessels)
- Congestion H1-2024: honest negative (waiting-time, not count)
- Parameter grid search: 72 combinations tested
- Include: comparison table, correlation matrix, preset table

### 6. Limitations
- Temporal coverage: 2021-2026 for high-quality data; 2016-2018 sparse
- Single pass direction (descending only)
- Zone rectangles approximate (port-limit polygons unavailable)
- Detector version mismatch between v3.1/v4 (documented in iteration 21)
- OOS nowcast does not beat persistence baseline
- Single port — generalization not tested

### 7. Conclusion
- Satellite radar is a viable, free, real-time port activity indicator
- Zone choice is critical (eOPL vs total-AOI)
- The `strait` package makes this reproducible
- Future: multi-port validation, TROPOMI emissions, per-vessel tracking

## Source Material
- experiments/README.md (all 28 iterations)
- experiments/results/perscene_counts.csv (248 scenes, 11 years)
- experiments/results/parameter_optimization.csv (72 grid points)
- experiments/results/ais_snapshot_5min.json (live AIS capture)
- experiments/data/ais_historical/anon_data/Singapore_anonymized.csv (610K records)
- outputs/singapore-strait-observatory-deepresearch.md (dossier)
- outputs/singapore-strait-observatory-deepresearch.provenance.md
- CHANGELOG.md (full lab notebook)
- strait/ package (published on PyPI)

## Verification Log
| Claim | Source | Status |
|---|---|---|
| R²=0.478 satellite-only | iteration 19 analysis output | verified |
| r=+0.73 eOPL-bunker | iterations 10-11 | verified |
| r=+0.53 tanker detrended | iteration 10 | verified |
| 84% AIS precision | iteration 28 grid search | verified |
| 4,240 eOPL vessels (Oct 2023) | iteration 25 Mendeley AIS | verified |
| 77% tankers in eOPL | iteration 25 | verified |
| +159% trimmed CFAR improvement | iteration 16 | verified |
| H1-2024 no spike | iteration 8 (congestion_2024.py) | verified |
| OOS nowcast: persistence wins | iteration 13 | verified |
| Mega-ship hypothesis disproven | iteration 21 (self-correction) | verified |

## Provenance Notes
- All correlations computed from perscene_counts.csv + official data
- AIS data from AISStream.io (live) and Mendeley (historical)
- ERA5 from Copernicus CDS
- VNL from EOG (Earth Observation Group)
- S2Coast from Zenodo
- No fabricated results; all numbers trace to logged iterations
