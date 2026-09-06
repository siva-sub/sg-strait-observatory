# Audit: strait-observatory paper vs codebase

**Date:** 2026-09-06
**Target:** `papers/singapore-strait-observatory.md` (v2 draft, 453 lines) audited against the `strait/` package (v0.2.0, PyPI + GitHub) and the `experiments/` pipeline
**Method:** 2 researcher subagents (claim-vs-code, independent recomputation from raw artifacts), 1 verifier subagent (re-verification of the 8 highest-severity findings + external URL checks), lead spot-checks. 25 claims checked; statistics recomputed from CSVs; detector re-executed; test suite re-run.
**Verdicts:** MATCH (13) · PARTIAL (6) · MISMATCH (2) · UNSUPPORTED (1) · blocked/unresolvable sub-claims (3)

## Executive summary

The paper's headline statistics are real and reproduce **exactly** from committed artifacts (r=+0.7269, ρ=+0.7378, n=57; rolling windows; dwell times; 84.2% grid optimum; 36 passing tests; 7,203-detection package validation). But the audit found **five publication-blocking defects**, all in how the pipeline is *described*, not in the underlying numbers: a wrong method attribution in the abstract, a sample-mixing error in the headline R², unreproducible AIS headline numbers, two cited artifacts that do not exist, and v4-detector rows contaminating the scene counts. Every defect has a mechanical fix.

---

## Blocking findings (fix before submission)

### B1. Abstract mislabels the detector — `papers/…md:9` vs code · **MISMATCH** · High

The abstract says "A **two-pass CA-CFAR detector (v3.1**…)" that produced the headline series. The code and the paper's own methods section say otherwise:

- `experiments/detect_vessels_v3.py:25,49-52` — v3.1 is **single-pass**: one `uniform_filter` local mean/σ, threshold `max(μ + 5.5σ, −12 dB)`. No guard cells, no censoring.
- `experiments/detect_vessels_v4.py:33-55` — the **two-pass** design (Pass 1 provisional `median + K·MAD`; Pass 2 background from sea-only pixels below the provisional threshold) is **v4**.
- The paper's §3.4 (lines 101–107, 109–121) describes both correctly — the abstract contradicts its own methods section.

This is the same class of error the audit's earlier round caught and fixed for "CA-CFAR v3.1; trimmed v4 evaluated separately" — the fix left the stray "two-pass" on v3.1. **Fix:** abstract → "a local-threshold CFAR detector (v3.1; a two-pass trimmed variant, v4, is evaluated separately)".

### B2. Headline R² mixes samples — abstract + Table 8 · **PARTIAL** · High

Paper: "satellite-only in-sample regression explains **R² = 0.478**". Recomputation:

| Sample | n | r | r² |
|---|---|---|---|
| Headline sample (bunker non-null, 2019-05..2026-03) | 57 | 0.7269 | **0.5283** |
| Wind-joined subsample (ERA5 ends 2025-12) | 54 | 0.6910 | **0.4775** |

0.478 = 0.691² on the n=54 wind-joined subsample (§4.4's own "+0.691"), presented as the satellite-only R² beside the n=57 r=+0.73 in the same abstract. Direction is conservative (the undisclosed full-sample value is *higher*), but the abstract quotes r from one sample and R² from another. Table 8's other entries (0.495 / 0.700 / 0.305 / 0.284) were not recomputed and likely inherit the same mixed base. **Fix:** restate all fusion-table R² on one declared sample.

### B3. AIS headline numbers do not reproduce — abstract + §4 · **PARTIAL** · High

Paper: "4,240 unique vessels in October 2023; 77% of anchored reports are tankers" (also 41,138 reports; 22,578 type-80 = 55%). Independent recomputation from the raw Mendeley CSV (`experiments/data/ais_historical/anon_data/Singapore_anonymized.csv`, 609,975 rows), eOPL box 104.00–104.35 E / 1.24–1.40 N (`strait/strait/zones.py:16`):

| Quantity | Recomputed | Paper | Δ |
|---|---|---|---|
| Unique MMSI | **4,414** | 4,240 | −3.9% |
| Anchored reports (NavigationalStatus==1) | **42,617** | 41,138 | −3.5% |
| Tanker share of anchored reports | **70.0%** (71.8% at speed<0.5 kn) | 77% | −6–7 pp |
| Type-80 share | **49.2%** | 55% | −6 pp |

No filter definition tested reaches the paper's numbers, and **no script in the repo computes them** (grep: zero hits; the figures exist only in `autoresearch.jsonl:22` iter 25 and README prose). The qualitative conclusion (tanker-dominated anchorage) survives; the magnitudes do not. **Fix:** commit the analysis script or restate as "≈4.4K unique vessels; 70–72% tankers (definition-dependent)".

### B4. Two cited artifacts do not exist — Appendix B · **UNSUPPORTED** · High

- `papers/…md:439` cites `results/robustness_summary.json` (rolling-window table provenance) — **absent** from disk and git.
- `papers/…md:440` cites `nowcast_oos.json` (OOS RMSEs 0.104/0.120/0.141) — **absent**; `CHANGELOG.md:103` claims it was saved, but `find` and `git ls-files` both return nothing.
- **No script in the repo computes the OOS RMSEs or the robustness battery** (repo-wide grep: only docstring mentions). The abstract's negative result ("RMSE 0.104 vs 0.120") is ledger-consistent prose with zero executable provenance — in a paper whose selling point is honest negatives. **Fix:** regenerate both artifacts with committed scripts, or drop the citations and weaken to "logged, not artifacted".

### B5. v4-detector rows contaminate the scene counts — §3.2, §4.7 · **PARTIAL** · Medium-High

`experiments/results/perscene_counts.csv:383-387` contains **5 rows with malformed day IDs** (`20160, 20170, 20170615, 20180, 20260`) that are v4-detector OData crops (their totals match the v4 column of the crop table in `experiments/README.md:250-257` digit-for-digit), not v3.1 Sentinel-Hub scenes:

- "248 accepted scenes … v3.1" → true v3.1 total is **243** (248 − 5)
- "237 in 2021–2026 (v3.1)" → true v3.1 is **236** (the `20260` crop is counted in the 2026 bucket: "2026: 14" is really 13)
- §4.7's "five v4 OData crops (2016–2018) alongside 237 v3.1 scenes" double-counts `20260` and misdescribes the composition — this also explains the paper's own unresolved "243 vs 237" bookkeeping question (§, lines 349/366)

**Reproduction landmine:** `perscene_join.csv` predates the v4 append; re-running `experiments/aggregate_perscene.py` today injects a `2017-06` row (eopl=225, v4 scale) into the headline series and changes n=57→58. **Fix:** move the 5 crop rows to a separate artifact; pin the aggregation to v3.1 rows; restate scene counts.

---

## Non-blocking findings

### Method/provenance

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| N1 | v4 "+159% detections" not reproducible from committed code: rerun of `detect_vessels_v4.py`'s `trimmed_cfar()` on the 5 on-disk crops gives degenerate ~18k–174k detections (script also globs deleted `s1_vv_*.tif` files); the v3.1 baseline (558 mean) exists only as a prose table | PARTIAL | `detect_vessels_v4.py:10-45`; `README.md:250-258`; verifier re-run |
| N2 | S2Coast-2023 land mask **not used by the analysis pipeline**: `fetch_detect_perscene.py:63-70` builds a temporal-median mask; no committed `.py` loads `s2coast_sg_landmask.tif` (used only for the 5 v4 crops). Paper Figure 1 shows S2Coast feeding all detection; §3.3 discloses the temporal median only in passing | MISMATCH | grep `s2coast` in `*.py`: zero hits |
| N3 | `detect_vessels_v3.py:23` still carries the **old eOPL box (104.00–104.30 E, 1.08–1.24 N) that sits on Batam** — superseded 2026-09-04 by the open-water box everywhere else (`zones.py:16`, `fetch_detect_perscene.py:27`). The monthly-composite reference series (§4.10) is computed over a different eOPL than every other artifact | MISMATCH (stale script) | zone-fix history `CHANGELOG.md:72,77` |
| N4 | Generating scripts absent for: `parameter_optimization.csv` (iter 28), `ais_dwell_times.csv` (iter 29), historical-AIS analysis (iter 25), wind fetches, fusion R² (iter 19), v4/v3.1 calibration + ships-per-TEU (iter 21), VNL fetch. ~10 analysis steps exist only as ledger prose | PARTIAL | repo-wide grep |
| N5 | "F1-optimal = 0.77" (§4.3 note) irreproducible: standard F1 at the cited grid point = 0.61; no formula on the CSV yields 0.77; package preset docstring says "F1=0.69" (actual 0.55) | UNSUPPORTED (sub-claim) | recomputation |
| N6 | "latest rolling r = 0.64" stale: latest window = 0.6192 (0.62); no window rounds to 0.64 | PARTIAL | recomputation, 34 windows |
| N7 | `autoresearch.jsonl` missing iterations 14–18, 30–31 (paper header claims "iterations 0–32"); `econ_join.py` is the older parallel pipeline, not the headline one | PARTIAL | jsonl inventory |

### Package

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| N8 | `strait/__init__.py:17` — `__version__ = "0.1.0"` vs `pyproject.toml:7` — 0.2.0 (published dist). `tests/test_strait.py:234` **asserts the stale value**, locking it in | MISMATCH (cosmetic) | verified; pytest 36 passed |
| N9 | CDSE download path is **dead code**: `sentinel1.py:208` imports `from .odata import download_and_process`; `strait/data/` has no `odata` module. Lazy import masks it; the CDSE path raises `ModuleNotFoundError`. Local-cache path works credential-free (verified) | PARTIAL | import test |
| N10 | README quickstart references nonexistent `strait.AIS(...)` (real: `AISMatch`), `strait.Stats.from_datagov_sg()` (no `stats.py`), `Zones({...})` (real: `Zones.custom`), and an architecture tree listing 6 files that don't exist | MISMATCH (README) | `strait/README.md` vs `__init__.py:20-37` |
| N11 | "7,203 detections matching iteration 20 exactly": **reproduced exactly** by the audit (balanced preset on 6 local crops: 1289/1342/1390/1644/1538/0) — but no test asserts it and the crop fixtures are gitignored, so CI can never verify the claim | PARTIAL | audit re-run |

### Reproduction risks (cloner's view)

- **Not in the repo:** `experiments/data/ais_historical/` (588 MB; the entire AIS-validation section depends on it), `experiments/data/crops/` (83 MB; needed for 7,203), `.env` credentials, `nowcast_oos.json` / `robustness_summary.json` (never existed on disk).
- **Credential gates:** CDSE (any scene extension), AISStream.io (live capture), CDS/ERA5 (re-fetch; CSVs committed), EOG (VNL; crops committed), Mendeley (open but **no fetch script, no URL/DOI in the paper** — verifier located it: DOI 10.17632/r37vwd493d.1). data.gov.sg and Open-Meteo need no auth.
- **Docs:** `experiments/README.md` "Reproduce" section documents only 2 of 18 scripts; `ais_capture.py` (powers Figure 5) is never mentioned.
- **Test environment:** local venv is Python 3.14 — outside the claimed 3.10–3.12 support range (tests still pass).

---

## What checked out exactly (no action)

| Claim | Verification |
|---|---|
| r=+0.7269, ρ=+0.7378, n=57; ≥2021 r=+0.7218, n=52 | recomputed, exact |
| Detrended r=+0.4618 (n=45); ERA5 partial r=+0.6964 (n=54); Open-Meteo control +0.75 | recomputed, exact |
| Rolling: 34 windows, median 0.5166, range 0.2620–0.7104, 0 negative, 13 below r_crit=0.4044 | recomputed, exact |
| Dwell: 346 tanker events / 298 tankers / median 24.9 h / P25-P75 10.6–77.6 / 22,851 tanker-h | recomputed from `ais_dwell_times.csv`, exact (nit: "246 tankers stayed >12 h" counts events; distinct tankers = 223/159) |
| 72-point grid; precision preset 6.5/32/7 → 84.2% (argmax of the grid — "in-sample optimum" honestly labelled); balanced 72.0%; recall 61.9% | CSV verified |
| Package presets = paper Table 6 | `detect/__init__.py:29-42` |
| eOPL zone (104.00–104.35 E, 1.24–1.40 N) as shipped | `zones.py:16` |
| 36 tests passing; CI matrix 3.10/3.11/3.12; PyPI 0.2.0 live; GitHub live | pytest re-run + URL checks |
| Table 5 AIS daily means (296/658/337 unique; 90/502/147 anchored) | daily CSVs, exact |
| H1-2024 "no spike": event eOPL ≈82.5 vs baseline ≈86.6 (flat-to-down) | `congestion_2024.py` + CSV |
| Mega-ship retraction | `autoresearch.jsonl:18` iter 21, mechanism + flipped trend documented |
| Five-line atlite-style API (Cutout → prepare → detect → aggregate) | `cutout.py:61-196`; atlite's `Cutout.prepare()` is a real API |
| 248 OK rows / 26 missing months / 4 gap windows | CSV recount |

---

## Recommended fix order

1. **Abstract (B1, B2, B3):** drop "two-pass" from v3.1; state R²=0.528 satellite-only n=57 (or declare the n=54 base for all fusion numbers); restate AIS as ≈4.4K / 70–72% or commit the script.
2. **Artifacts (B4):** write `experiments/nowcast_oos.py` + `experiments/robustness_battery.py` with committed outputs, or cut the Appendix B citations.
3. **Data hygiene (B5):** quarantine the 5 v4 crop rows; re-pin the headline aggregation; restate 243/236; fix §4.7's "alongside 237" sentence.
4. **Stale code (N3, N8, N9, N10):** sync `detect_vessels_v3.py` zone box; bump `__version__` + fix the test; remove or stub the dead `odata` import with a clear error; rewrite README quickstart against the real API.
5. **Provenance (N1, N4, N5, N6):** commit generating scripts for the grid search, dwell, and AIS analyses; delete or recompute F1=0.77 and "latest 0.64".
6. **Citation (F8c):** add the Mendeley DOI (10.17632/r37vwd493d.1) to Appendix A; add a fetch helper or explicit manual-download instructions.

## Sources

- Paper: `papers/singapore-strait-observatory.md` (local, v2 draft 2026-09-06)
- Repository: https://github.com/siva-sub/strait-observatory
- Package: https://pypi.org/project/strait-observatory/0.2.0/
- Historical AIS dataset: Mendeley Data, "AIS Data from 11 ports around the globe", DOI 10.17632/r37vwd493d.1, https://data.mendeley.com/datasets/r37vwd493d/1 (verified live; cited by name only in the paper — DOI missing)
- Key local artifacts: `experiments/results/perscene_join.csv`, `experiments/results/perscene_counts.csv` (lines 383–387), `experiments/results/parameter_optimization.csv`, `experiments/results/ais_dwell_times.csv`, `experiments/data/ais_historical/anon_data/Singapore_anonymized.csv`, `experiments/detect_vessels_v3.py`, `experiments/detect_vessels_v4.py`, `experiments/fetch_detect_perscene.py`, `strait/strait/detect/__init__.py`, `strait/strait/zones.py`, `strait/strait/data/sentinel1.py`, `autoresearch.jsonl`
- Subagent audit reports: `.pi-subagents/artifacts/outputs/aa1f559c/research.md` (part 1), `.pi-subagents/artifacts/outputs/36edf21a/research.md` (part 2), `.pi-subagents/artifacts/outputs/8141022b/cited.md` (verifier)


---

## Addendum (2026-09-06, post-audit): fixes applied

All five blocking findings and the actionable non-blocking findings were fixed in the same session:

| Finding | Fix applied | Verified |
|---|---|---|
| B1 two-pass mislabel | Abstract → "local-threshold CFAR detector (v3.1; a two-pass trimmed variant, v4, is evaluated separately)" | grep: no stray "two-pass" on v3.1 |
| B2 R² sample mixing | Abstract + fusion table now declare samples: 0.528 (n=57) satellite-only; 0.495 (n=54) with wind; 0.700 (n=57) with arrivals | recomputed from artifacts |
| B3 AIS numbers | New committed script `experiments/ais_historical_analysis.py` → `ais_historical_stats.json`; paper now states 4,414 / 42,617 / 70.0% (71.8% speed variant) / type-80 49.2%; Table 5 regenerated from script (daily means 316/640/452; anchored 81/269/113; eOPL ratio 1.06, still highest) | script rerun matches JSON; paper matches script |
| B4 missing artifacts | `experiments/nowcast_oos.py` → `nowcast_oos.json` and `experiments/robustness_battery.py` → `robustness_summary.json` committed; paper numbers replaced with script output; old 0.104/0.120 RMSEs explicitly withdrawn (negative result survives, sharper: skill +0.006 alone; +0.137 combined) | artifacts exist on disk; 16-point verification sweep passed |
| B5 v4 contamination | 5 v4 crop rows quarantined → `perscene_counts_v4_crops.csv`; scene counts restated 243/236; §4.7 "alongside 237" fixed; re-running the aggregation is now stable (max monthly diff 0.003) | recount + re-aggregation check |
| Dwell (§4.3) | `experiments/ais_dwell.py` with documented 24h-gap event splitting → 651 events / 470 tankers / median 18.0 h / 21,284 tanker-h; paper states the definition-sensitivity range (10–28 h median across gap choices) | script rerun matches CSV; paper matches script |
| N3 stale zone box | `detect_vessels_v3.py` eastern_opl synced to (104.00, 1.24, 104.35, 1.40) with comment | grep |
| N5 F1=0.77 | Corrected to F1 = 0.61 at k=4.0/win=32/mp=3 (formula stated) | recomputed |
| N6 latest 0.64 | Corrected to 0.62 | robustness_summary.json |
| N8 version skew | `__version__` 0.2.1, pyproject 0.2.1, version test now cross-checks both; 0.2.1 published to PyPI | pytest 36 passed; https://pypi.org/project/strait-observatory/0.2.1/ |
| N9 dead odata import | Replaced with explicit `NotImplementedError` explaining the local-cache path | code inspection |
| N10 README drift | Quickstart now uses real API (`AISMatch`, `Zones.custom`); architecture tree matches actual files | grep: 0 stale refs |
| N2 S2Coast attribution | §3.3 and Figure 1 corrected: v3.1 headline series uses temporal-median mask; S2Coast is the package/v4 path; re-run flagged as open robustness item | text inspection |
| F8c Mendeley DOI | DOI 10.17632/r37vwd493d.1 added to §3.7 and Appendix A | — |
| 2,145 pool caveat | Explicitly flagged in Table 6 note as not regenerable from committed code | — |

Post-fix state: every quantitative claim in the paper now traces to a committed artifact or a committed script's output, with the two remaining known limitations (unscripted 2,145-vessel pool; headline series not yet re-run under S2Coast) stated in the paper itself.
