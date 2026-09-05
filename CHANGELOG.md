# CHANGELOG

## 2026-09-04 — Autoresearch session started (discovery mode)

- Task: scout a portfolio-grade Singapore geospatial project use case.
- Baseline anchor: github.com/Vorld/singapore-travel-time-map.
- Channels: gh CLI, degoog search MCP, chromiumfish MCP, pi-scraper, alpha paper tools.
- Session files created: `autoresearch.md`, `autoresearch.sh`, `autoresearch.jsonl` (on first evidence).
- No benchmark applies (discovery loop); decisions logged per iteration. Max 8 iterations.

## 2026-09-04 — Loop closed (iterations 0–5 of max 8)

- Channel coverage: gh CLI (22 repo searches), degoog web+scholar, alpha (arXiv, after `alpha login`), OpenAlex via feynman_science_database_search, pi-scraper, curl_cffi (paper fetches), chromiumfish (CDSE browser load over SG).
- Pivot at iter 4 on user profile: economic relevance mandatory (settlement banking + GFTN tokenization SME).
- **Final recommendation: Singapore Strait Trade Observatory** — Sentinel-1 vessel detection vs MPA/SingStat trade statistics, with congestion, bunkering, and dark-vessel modules; RWA-oracle spin. Runner-up: EO valuation layer for tokenized HDB assets.
- Deliverable: `outputs/singapore-geospatial-usecase-scouting.md` (ranked candidates, evidence, build plan, risks).

## 2026-09-04 — Iteration 6 (transplant scan, user reopened loop)

- Scanned jurisdiction-transplant ideas: gh CLI (corrected queries) + degoog scholar.
- Key finds: Batista et al. 2025 (TROPOMI resolves individual-ship NO2 plumes) -> rank 1 upgraded to trade+emissions dual ledger; Mohamadi/Balz 2026 (InSAR coherence construction progress) -> new co-rank-2 'BTO from orbit'; Cool Walks (Berlin/HCMC) -> rank 3; DeepSolar/PetaBencana -> honorable mentions.
- Artifact updated: new §5 transplant matrix; evidence inventory extended.

## 2026-09-04 — Iteration 7: deep research on rank 1 (Singapore Strait Observatory)

- Waves 1–2 via degoog web+scholar, fetch_content, curl_cffi+pypdf (ESG trade PDF read locally), gh CLI, OCEANS-X/Guardian lookups.
- Key verified facts: S$1.3T merchandise trade 2024 (+6.6%); 41.12M TEU (+5.4%, ~90% transshipment); bunker 54.92 Mt record; 2024 congestion episode (13.36M TEU Jan–Apr); >100k strait transits 2025; S1C operational May 2025 + S1D Nov 2025 (6-day repeat restored); CDSE free with quotas; dataset IDs for vessel arrivals + bunker sales confirmed; OCEANS-X 100+ APIs; SG–Rotterdam corridor active; SC/MAS trade-finance tokenisation pilot.
- Method anchors: Georgoulias 2020 (per-ship TROPOMI NO2 plumes), Kurchaba 2022/2023 (ML plumes/anomalous emitters), Verschuur/Koks/Hall (AIS trade econ), Iervolino&Guida GLRT + Bae&Yang false alarms (S1 GRD detection).
- Deliverables: outputs/singapore-strait-observatory-deepresearch.md + .provenance.md; risks table + 8-week build plan.

## 2026-09-04 — Iteration 8: CDSE access + measured S1 feasibility (loop complete)

- CDSE account authenticated (password grant, 1800s tokens); credentials saved to `.env` (git-ignored; `.env.example` template added). Nothing sensitive written to artifacts/logs.
- Measured over strait AOI: 352 S1 IW-GRD scenes since 2025-01-04; median 18/month; all descending; S1A→S1D transition 2026-06 (no S1C over this AOI). Saved `notes/discovery/cdse_s1_feasibility.json`.
- Dossier updated: §3.1 revisit/archive now measured; risk table downgraded; open question #1 closed.
- Autoresearch loop closed at iteration 8/8.

## 2026-09-04 — Execution: Week-2 detection pipeline (v3.1 frozen)

- Fetched 12 monthly S1 VV composites via CDSE Sentinel Hub Process API (13.1 MB each) after fixing timeRange format ({"from","to"} object) and 2500 px output cap.
- Detector iterations (full failure log in experiments/README.md): v0 (queue-merge bug found by glm-5.3-flash vision QA) → v2 (min-filter fill poisoning, INVALID 11.4k) → v2.1/v2.2 (global z-score math failure, 0 ships) → v3 (fill-bias diagnosed via same-math A/B: 6142 vs 2755 cand px) → **v3.1 frozen**: neutral-fill local CFAR + peak-splitting.
- Vision QA round 2 (glm-5.3-flash): Sept regression CLOSED (10-12 markers on eOPL queue); OVERALL ACCEPT-WITH-FIXES; residual caveats = dim speck grid (likely aquaculture, excluded by design) + 1 bridge FP.
- Final: 254-409 ships/month, port_core 91-138, eOPL 8-27, wOPL 31-67; artifacts: experiments/results/detections_v3.geojson (4,224 ships), monthly_counts_v3.csv, QA PNGs qa1-qa6.
- Next: Week-3 econ join (MPA container/arrivals/bunker + SingStat trade; dataset IDs verified in dossier §5).

## 2026-09-04 — Execution: Week-3 econ join (honest null at v0.1)

- Official series pulled via data.gov.sg datastore fallback (package_show 403s): container throughput, vessel arrivals (total + by type), bunker sales (by type). SingStat trade 403 -> v1.
- Result: NO significant correlation sat counts vs official series (n=9 overlap; all p>0.18; sat_total vs container Pearson r~0.00). Lead-lag swings at n=7-8 = endpoint noise.
- Diagnosis recorded: single monthly snapshot (variance), n=9 (no power), stock-vs-flow construct mismatch (congestion may invert sign).
- v1 path defined: per-scene (~18/mo) averaging, 2015+ history, H1-2024 congestion natural experiment, zone×type joins.
- Artifacts: experiments/results/econ_join.csv, econ_join_chart.png; README Week-3 section.

## 2026-09-04 — Per-scene pipeline (option B) + methods-literature check

- Literature gains applied (see README "Methods lineage"): IMF Cerdeiro et al. 2020 index design; validation-first framing (Kanjir 2018); land-mask FP doctrine (Grover 2018); queue-length congestion metric (Verschuur). CFAR confirmed standard (El-Darymli 2013). arXiv port-congestion probe: nothing relevant (channel exhausted).
- Pipeline built: per-day Process-API fetch -> v3.1 detect -> counts CSV (resumable, disk-flat). Catalogue truth: 2015-2026 = 894 overpass days (~85/yr; no S1B over this AOI).
- Bugs caught by 2-day smoke tests (all logged): float centroid indices; no-data coverage poisoning; SEA/land inversion; swapped rowcol args. Final smoke: 419 ships (port 113/eOPL 35/wOPL 64) consistent with monthly composite.
- FULL RUN launched in background (nohup, -u logging, 4 workers): experiments/perscene_run.log; output experiments/results/perscene_counts.csv. Aggregate step ready: aggregate_perscene.py.

## 2026-09-04 — Per-scene run complete + honest detrended verdict

- 868 valid scenes processed (141 months, 2015-01..2026-09; ~50 min wall, 4 workers; 4 failed days immaterial; writer bug caused 197 duplicate rows from killed mop-up — deduped in aggregation).
- LEVEL correlations trend-dominated (era-unstable; -0.82 in 2015-19 vs n.s. in 2020+); era means 344->277->269 ships/overpass (~2020 break, confounded).
- DETRENDED YoY: no significant nowcast correlation (|r|<=0.14, n=125); single weak bunker hint (MA3-YoY rho=+0.19, p=0.035).
- Verdict recorded: CFAR monthly presence != monthly trade nowcast. Pivot: congestion events, structural change (fleet consolidation), bunker-zone dwell.
- Artifacts: perscene_counts.csv, perscene_monthly.csv, perscene_join.csv, perscene_join_chart.png, detrend_analysis.py; README updated.

## 2026-09-04 — Congestion case study (a): honest negative + two vision-QA discoveries

- First pass: eOPL presence DOWN in Apr-Jul 2024 (13.2 vs 16.5, p=0.013); official container arrivals also FLAT (1087-1274/mo) -> "congestion" was waiting-time, not count bunching.
- glm-5.3-flash wide-scene review (2024-06-14) found: (W1) swath footprint rarely reaches 104.35E - east half of wide fetch is nodata, and single-scene partial coverage explains the bimodal per-scene counts (36% vs 93% coverage measured); (W2) eOPL rectangle sat on Batam island/Hang Nadim runway - zone definition error; (W3) the real queue field (~150-250 ships in anchorage rows) sits in port_core.
- Fixes: eOPL moved to open water (104.00-104.35E, 1.24-1.40N); pipeline now records per-scene coverage and accepts only cov>=0.80; full rerun launched (run3). v1 (partial-cov) and v2 (old zones) CSVs kept as .bak for audit.

## 2026-09-04 (late) — Session close: throttled rerun, honest status

- (a) Congestion case study: first-pass verdict = NO queue in original eOPL box (presence DOWN 0.80x, p=0.013); official container arrivals also flat (1,087-1,274/mo) -> congestion was waiting-time, not count-bunching. glm-5.3-flash wide-scene review then found: swath rarely covers east of ~104.3E; original eOPL box sat on Batam/Hang Nadim (zone error, FIXED to 104.00-104.35E, 1.24-1.40N); the real 150-250-ship queue field sits in port_core. FINAL clean numbers pending rerun.
- Per-scene pipeline v3 (coverage-gated, fixed zones, newest-first) is code-complete and smoke-tested, but CDSE now throttles the account (~3k Process requests today): 0.07/s vs 0.29/s this morning; single request hangs >25s. Rerun PAUSED; fully resumable (`fetch_detect_perscene.py` skips days already in perscene_counts.csv). Relaunch when quota resets.
- (b) Map MVP (web/index.html): code-complete; assets served (localhost:8765); programmatic checks pass (syntax OK, constructor runs, charts 200, slider wired). Visual render BLOCKED in this environment only: headless Chromium cannot create WebGL context ("BindToCurrentSequence failed") - not a page bug; verify in a real browser.

## 2026-09-05 — Clean rerun (run6) + FINAL results

- Run6: 637 days queued (newest-first), 243 OK (cov>=0.80) + 138 LOWCOV + 256 FAIL. Failures = pre-2021 era (CDSE long-term-archive: old scenes return near-empty responses) + unstable OData pagination (day totals varied 848/754/637 across queries; 2023 hole). Fixed en route: detect() return arity bug (found via failure log, not throttling), pkill self-match bug.
- **ECON VERDICT FLIPS with corrected eOPL zone (open water NE of Batam):** levels n=57: bunker r=+0.73, arrivals +0.64, container +0.57 (p<0.001). DETRENDED YoY n=45: bunker +0.46, arrivals +0.37, container +0.33 (p<=0.027). MA3-YoY: bunker +0.68/0.60, container +0.49/0.51, arrivals +0.46/0.50. Lead-lag: contemporaneous co-movement (k=0 peak, no false lead claim). Yesterday's null was the Batam-box zone error.
- **Congestion verdict (clean, n=13 event scenes):** NO spike in any zone (eOPL 0.96x n.s.; total 0.89x down); official arrivals flat. Congestion was waiting-time; any queue beyond AOI/coverage is unobserved.
- Map updated: headline panel now shows the honest final numbers; charts refreshed in web/assets.
