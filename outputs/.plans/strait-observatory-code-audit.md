# Audit Plan: strait-observatory-code-audit

**Date:** 2026-09-06
**Auditor:** Feynman (lead) + researcher/verifier subagents
**Slug:** `strait-observatory-code-audit`

## Audit targets

| What | Where |
|---|---|
| Paper draft (v2, 453 lines) | `papers/singapore-strait-observatory.md` |
| Python package (`strait` v0.2.0) | `strait/` (local), https://github.com/siva-sub/strait-observatory, https://pypi.org/project/strait-observatory/0.2.0/ |
| Experiment scripts (pipeline of record) | `experiments/*.py` |
| Result artifacts | `experiments/results/*.csv`, `experiments/results/*.json` |
| Autoresearch ledger | `autoresearch.jsonl` (30+ iterations) |

## Claim inventory to check (paper → code)

### A. Detector claims
1. "Two-pass CA-CFAR detector (v3.1)" — verify implementation in `experiments/detect_vessels_v3.py` is actually two-pass CA-CFAR; check guard/cell window sizes claimed vs coded defaults
2. "Trimmed CFAR (v4) … +159% detections" — verify `detect_vessels_v4.py` implements trimmed-mean background; check the +159% number's provenance
3. "72-point parameter grid … 3 presets (balanced 72% / precision 84% / recall 62%)" — check `experiments/results/parameter_optimization.csv` row count and best-cell values; check preset values shipped in `strait/strait/detect/`
4. Land masking: S2Coast-2023 claim; check what the code actually uses

### B. Data claims
5. "248 accepted scenes (2016–2026, 237 in 2021–2026)" — check `experiments/results/perscene_counts.csv` row count and date span
6. eOPL zone polygon — check `strait/strait/zones.py` coordinates match the paper's described zone
7. Sampling gaps (26 missing months, 4 gap windows) — re-derive from perscene_join.csv

### C. Statistics claims
8. r=+0.73 / ρ=+0.74 / n=57; ≥2021 subsample r=+0.72 n=52 — recompute from `perscene_join.csv`
9. R²=0.478 satellite-only; 0.700 with arrivals — check join + regression code
10. Detrended r=+0.46; partial r=+0.696 (ERA5 wind); tanker r=+0.53 — check `detrend_analysis.py` and weather join
11. Rolling: 34 windows, median 0.52, range 0.26–0.71, 13 below r=0.404 — recompute
12. Dwell: median 24.9h, P25/P75 10.6/77.6, 22,851 tanker-hours — check `experiments/results/ais_dwell_times.csv`

### D. AIS validation claims
13. "4,240 unique vessels in October 2023; 77% tankers" — check AIS historical data + counting script
14. "84.2% precision … 2,145 anchored AIS vessels" — check matching script + in-sample caveat

### E. Negative results
15. OOS nowcast RMSE 0.104 vs persistence 0.120 — check the nowcast script
16. H1-2024 no spike — check `congestion_2024.py`
17. Mega-ship retraction — check ledger iterations

### F. Package claims
18. "v0.2.0, 36 tests, CI on 3.10–3.12" — run the tests; check `pyproject.toml`, `.github/workflows/ci.yml`
19. "7,203 detections matching iteration 20 exactly" — check local-cache test
20. "Five-line API modeled on atlite" — check README example runs

### G. Reproduction risks
21. Credentials/API deps; CDSE quota blockers; gitignored data paths
22. Any numbers in the paper with no code path at all

## Method

1. Feynman: claim inventory (this plan), repo map, paper claim extraction
2. `researcher` subagent: claim-vs-code comparison for A–D (detector, data, stats)
3. `researcher` subagent 2: claim-vs-code comparison for E–G (negatives, package, repro)
4. Feynman: run the package tests directly (36-test claim), recompute headline stats from CSVs
5. `verifier` subagent: verify external URLs (PyPI, GitHub repo, data sources cited), confirm audit findings trace to code lines
6. Write exactly one artifact: `outputs/strait-observatory-code-audit.md`

## Output contract

One canonical audit artifact with: verdict per claim (MATCH / MISMATCH / UNSUPPORTED / BLOCKED), severity, code path or artifact evidence, reproduction risks, and a Sources section.
