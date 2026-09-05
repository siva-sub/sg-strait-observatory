# Singapore Strait Observatory — Deep-Research Dossier (Rank 1)

**Project:** *Nowcast Singapore's trade, port activity and shipping emissions from free satellite data.*
**Companion artifacts:** `singapore-geospatial-usecase-scouting.md` (ranked candidates) · this dossier (execution evidence) · provenance sidecar `singapore-strait-observatory-deepresearch.provenance.md`.
**Research loop:** autoresearch iteration 7, 2026-09-04. All URLs verified this session unless marked *unverified*.

---

## 1. Executive summary

The project counts and classifies vessels in Singapore's port waters and anchorages from **Sentinel-1 SAR**, cross-validates the resulting indices against **official monthly statistics already published as open data** (container throughput, cargo throughput, vessel arrivals, bunker sales, merchandise trade), and adds a **Sentinel-5P/TROPOMI maritime-emissions layer** whose per-ship plume detection was only proven in 2020–2025 literature. Every input is free; the economic story is verified (a **S$1.3 trillion merchandise-trade economy, 41.12M TEU, 54.92 Mt of bunker sales in 2024**); and the two identity hooks — trade-finance/settlement and tokenized real-world assets — both have citable anchors.

**Positioning line for interviews / GitHub README:**
> *"Singapore moved S$1.3 trillion of merchandise trade and 41 million TEUs in 2024. I track the ships that carry it — from free Copernicus radar, night and cloud included — and nowcast the official numbers before they drop."*

## 2. Verified headline facts (all 2024–2026 sources)

| Fact | Value | Source |
|---|---|---|
| Total merchandise trade 2024 | **S$1.3 trillion, +6.6% YoY** (non-oil +8.3%, oil −0.1%) | EnterpriseSG media release MR 004/25 (PDF fetched & read this session) |
| Container throughput 2024 | **41.12M TEU**, +5.4%, first time >40M; ~**90% transshipment** | MPA release; Straits Times, 2025-01-15 |
| Bunker sales 2024 | **54.92 Mt record**, +6.0%; alternative fuels 1.34 Mt (first time >1 Mt) | MPA release; Offshore-Energy 2025-01-24 |
| 2024 congestion episode | Container "bunching"; 13.36M TEU in Jan–Apr 2024; tanker/bulk unaffected (bunkering at anchorages) | MPA media response on extended berth waiting times |
| Strait traffic 2025 | **>100,000 vessel transits** through Malacca + Singapore Straits | Seatrade-Maritime; The Logistic News (2026) |
| Sentinel-1 constellation | S1B failed 2021-12-23; **S1C operational since May 2025** (data on CDSE since Jan 2025); **S1D launched 2025-11-04**; ~6-day repeat restored; June 2026 orbital reconfiguration (S1C briefly suspended, S1A+S1D nominal) | CDSE collection page; SentiWiki; NASA Earthdata; Sentinel Online |
| SG–Rotterdam Green & Digital Shipping Corridor | Active since 2022, strengthened 2025-04-09; bio-LNG bunkering trial planned in SG | Port of Rotterdam + MPA releases |
| MAS Project Guardian trade-finance tokenisation | Standard Chartered trade-finance tokenisation pilot under MAS initiative | GTR; SC paper page |

## 3. Satellite data feasibility

### 3.1 Sentinel-1 (primary — works at night, through cloud)
- **Product:** GRD, IW mode, ~10 m × 10 m ground range (GRD resampled; native azimuth ~22 m). VV/VH.
- **Revisit (measured, not assumed — CDSE OData query, 2026-09-04):** **352 IW-GRD scenes** over the strait AOI from 2025-01-04 → 2026-09-03; **median 18 scenes/month** (max 24; min 2 = partial current month), i.e. roughly one usable pass every ~1.7 days. All scenes over this AOI are **descending** (`*1SDV`, VV/VH) — no ascending acquisitions in the archive — with provider mix S1A (308) → S1D (44, from 2026-06). Raw query results: `notes/discovery/cdse_s1_feasibility.json`.
- **Access:** CDSE OData/OpenSearch (bulk download), Sentinel Hub Process API (server-side band math via evalscripts — the `eu-cdse/sentinel-hub-custom-scripts` repo the user provided is the pattern library), openEO. **Free, but all channels have user quotas (bandwidth + monthly transfer)** per CDSE FAQ — budget ~1 AOI × ~200 scenes for MVP, trivially within limits.
- **Archive:** full S1 history on CDSE; 2022-01→2024-12 was the single-satellite era (~12-day revisit if you backfill those years). Empirically this AOI ran on S1A alone until 2026-06, then S1D — S1C does not appear in this AOI's archive — so sampling continuity is good, but don't assume three-satellite density.

### 3.2 Sentinel-2 (secondary — daytime optical verification samples)
- 10 m MSI; Singapore tile(s) — look up exact MGRS tiles (e.g., 48NUG/48NUH; confirm in catalogue) in week 1. Cloud loss is frequent in the tropics → use only for visual spot-checks and class-labeling of large vessels, never as the primary feed.
- Also in CDSE (and Landsat 8/9 available in the Copernicus Browser since 2026-01 — context only; not core here).

### 3.3 Sentinel-5P TROPOMI (emissions layer)
- NO₂ tropospheric column at **3.5 × 5.5 km²** (since Aug 2019; 7 × 3.5 km² before), ~13:30 local overpass, daily global coverage; L2 products free on CDSE.
- Individual-ship plumes are resolvable for **large ships under favourable winds** (Georgoulias et al. 2020, Mediterranean; Kurchaba et al. 2022 ML segmentation; Batista et al. 2025 review). Over the Strait, pixel size vs channel width (~10–20 km) and heavy traffic mean plume *attribution* needs wind-aligned along-track aggregation (divergence method) — an honest engineering challenge and a genuine research-flavoured contribution.
- Cloud contamination affects UV-Vis retrievals (tropics) — plan monthly/seasonal aggregates, not daily.

## 4. Method stack

1. **Preprocess S1 GRD:** orbit file → calibration → speckle (Lee) → land-sea mask (coastline/EEZ polygons; OneMap/MPA port-limit layers).
2. **Vessel detection v0:** cell-averaging CFAR on σ⁰; classical GLRT detector literature exists for exactly this (Iervolino & Guida 2017); false-alarm control matters — RFI and azimuth smearing are the known S1 failure modes (Bae & Yang 2020).
3. **Detection v1 (ML):** fine-tune on **LS-SSDD-v1.0** (large-scale SAR ship dataset built from Sentinel-1, 78★) or adapt `MJCruickshank/SARfish` (160★); deploy as batch inference.
4. **Aggregation:** counts + mean backscatter size proxy inside named polygons — port limit, Eastern OPL, Western OPL, EPL (digitize approximate anchorage polygons; verify official port-limit geometry from MPA sources).
5. **Econ join:** monthly sums/means vs the open-data series in §5; correlation, lead-lag (cross-correlation at ±1–2 months), simple nowcast regression (satellite index → TEU/trade YoY). Report in a public notebook — this is the "oracle" evidence.
6. **Emissions module:** S5P NO₂ wind-rotated plume composites over the strait corridor; correlate NO₂ load with S1 vessel counts (same month); flag anomalous emitters per Kurchaba et al. 2023.
7. **Frontend:** MapLibre + OneMap basemap (same free stack as the anchor travel-time repo), density heatmap + time slider; chart panel with satellite index vs official series; static hosting (GitHub Pages/Cloudflare), precomputed small JSON artifacts per the anchor repo's architecture.

## 5. Ground-truth & economic data (all open, dataset IDs verified)

| Series | ID / URL | Granularity |
|---|---|---|
| Container Throughput, Monthly (TEU) | data.gov.sg `d_da030f7028200d19ffcbe4a2d71af39c` | monthly |
| Cargo Throughput, Monthly (by type) | data.gov.sg MPA collection 390 | monthly |
| Vessel Arrivals (>75 GT) Total | data.gov.sg `d_d48c5a038904f6da3c603cd854b6c191` | monthly |
| Vessel Arrivals (>75 GT) Breakdown by type | data.gov.sg `d_8f264219109e61fffa87ac64dd5a9a65` (coll. 394) | monthly |
| **Bunker Sales Breakdown, Monthly (tonnes)** | data.gov.sg `d_4f5abbf4486bf8e52bbed3be56dde562` | monthly |
| Merchandise Trade, Monthly, SA | data.gov.sg `d_c41b1f16d0847996b1dcfd2ded0b2d91` (SingStat) | monthly |
| MPA Port Statistics hub | mpa.gov.sg/who-we-are/newsroom-resources/research-and-statistics/port-statistics | — |
| MPA Bunkering statistics hub | mpa.gov.sg/port-marine-ops/marine-services/bunkering/bunkering-statistics | monthly + suppliers |
| OCEANS-X (MPA data platform) | oceans-x.mpa.gov.sg (+ `/marketplace/apis`; 100+ APIs/datasets at launch) | incl. vessel-arrival API |
| EnterpriseSG 2024 trade review (PDF) | enterprisesg.gov.sg MR 004/25 (saved: `notes/papers/esg_2024_trade_review.pdf`) | annual |

data.gov.sg datasets are CKAN-accessible (stable resource IDs above) → scripted pulls, no scraping.

## 6. Research-evidence chain

**Trade-from-space / AIS economics (the transplant lineage):**
- Arslanalp, Koepke & Verschuur (2021), *Tracking trade from space: an application to Pacific island countries* — satellite-derived daily port/trade indicators (Google Books chapter).
- Chico, Cordel, Mariasingham & Tan (2025), *Analyzing anomalous events in passageways with high-frequency ship signals*, PLOS ONE — https://doi.org/10.1371/journal.pone.0320129
- Verschuur, Koks & Hall (2020), COVID maritime trade losses, arXiv 2010.15907; (2022), *Ports' criticality in international trade and global supply-chains*, Nature Communications (218+ cites) — https://www.nature.com/articles/s41467-022-32070-0
- Parubets & Naito (2025), NO₂ → local economic activity, PLOS ONE — https://doi.org/10.1371/journal.pone.0337901

**SAR vessel detection:**
- Iervolino & Guida (2017), GLRT ship detector incl. non-AIS small vessels, IEEE JSTARS — https://ieeexplore.ieee.org/abstract/document/7927377
- Bae & Yang (2020), S1 false-alarm suppression (RFI, azimuth smearing) — https://doi.org/10.7780/kjrs.2020.36.4.4
- Datasets/code: `TianwenZhang0825/LS-SSDD-v1.0-OPEN` (78★), `MJCruickshank/SARfish` (160★), `gSulpizio/sat_tracker` (SAR+AIS dark-vessel fusion), Ballinger (2024) dark STS arXiv 2404.07607.

**Maritime-emissions ledger:**
- Georgoulias, Boersma, van Vliet et al. (2020), *Detection of NO₂ pollution plumes from individual ships with TROPOMI/S5P*, Environ. Res. Letters — https://iopscience.iop.org/article/10.1088/1748-9326/abc445
- Kurchaba et al. (2022), supervised segmentation of ship NO₂ plumes, arXiv 2203.06993; (2023) anomalous-emitter detection & inspection prioritisation, arXiv 2302.12744.
- Batista, Jamal, Isbaex et al. (2025), *Sentinel data for monitoring of pollutant emissions by maritime transport — a literature review*, Remote Sensing 17(13):2202 — https://www.mdpi.com/2072-4292/17/13/2202

**Tokenization bridge (RWA oracle framing):**
- Cong, Mayer & Rabetti (2025), *Tokenizing real-world assets*, SSRN 7094059 (oracles/valuation as the RWA bottleneck).
- Standard Chartered trade-finance tokenisation pilot under MAS initiative (GTR 2023*; SC paper page) — date of article unverified, claim itself corroborated by two sources.
- Singapore–Rotterdam Green & Digital Shipping Corridor (MPA + Port of Rotterdam, strengthened 2025-04-09) — the policy frame that makes a "carbon ledger" Strait product timely.

## 7. Risks & mitigations (updated)

| Risk | Severity | Mitigation |
|---|---|---|
| No free historical AIS for SG waters | medium | Validate vs monthly official series (§5); S2 optical spot-checks; optional 1-month paid AIS for gold-standard appendix; frame as "AIS-free by design" (works where AIS is spoofed/off — cite Ballinger 2024) |
| S1 sampling (measured 2026-09-04: median 18 descending scenes/month since 2025, single pass direction) | low | Ample for monthly econ aggregation; note single-direction passes for any motion/dwell analysis |
| CFAR false alarms (RFI, azimuth smearing) | medium | Land/anchorage gating + size filters + Bae&Yang techniques; report precision on hand-labeled sample |
| TROPOMI pixel (3.5×5.5 km) vs strait width; plume attribution | high for per-ship claims | Scope v0 to *corridor-level* monthly NO₂ vs vessel counts; per-ship plumes only as showcase on high-wind case days (à la Georgoulias 2020) |
| CDSE quotas | low | Small AOI, GRD-only, ≤300 scenes MVP; process server-side via Sentinel Hub where possible |
| Anchorage polygon geometry | low | Digitize from charts + verify against MPA port-limit publications; sensitivity analysis on polygon size |
| Official stats revisions ("preliminary estimates") | low | Pin dataset versions; note revision dates |

## 8. Build plan (concrete)

**Week 1 — catalogue + access.** CDSE account; OData query for S1 GRD over AOI (2024-06→present); count scenes/period; download first 12; establish quota reality. Pull all §5 datasets via CKAN. Set up repo `sg-strait-observatory` (Python: `requests`, `rasterio`, `numpy`, `scipy`, `geopandas`).
**Week 2 — detection v0.** Calibration + land-sea mask + CFAR; visual QA against Copernicus Browser at same timestamps; output detections GeoJSON; anchorage counts time series.
**Week 3 — econ join + notebook.** Monthly aggregates; correlation/lead-lag vs TEU, vessel arrivals, bunker sales, trade; publish analysis notebook with honest caveats.
**Week 4 — map MVP.** MapLibre + OneMap; density heatmap + time slider; chart overlay panel; README with pitch + method + sources; deploy static.
**v1 (weeks 5–8).** ML detector (LS-SSDD); vessel-size class proxies per anchorage (tanker/bulk vs container); bunkering module (bunker-anchorages dwell vs bunker sales); 2024 congestion case study; TROPOMI corridor NO₂ composites + one per-ship plume showcase; dark-vessel alert prototype; write-up for trade-finance audience; optional OCEANS-X integration submission (MPA explicitly invites third-party services on it).

## 9. Open questions
1. ~~Exact S1 pass pattern over AOI~~ **ANSWERED (2026-09-04):** descending-only; median 18 scenes/month; S1A → S1D from 2026-06; see `notes/discovery/cdse_s1_feasibility.json`. CDSE account authenticated OK (credentials in `.env`, git-ignored).
2. Official port-limit / anchorage polygon availability as open GIS (MPA GeoHub? OCEANS-X?) — else digitize.
3. TROPOMI L2 via CDSE quotas for a 2-year corridor stack — size it.
4. Whether MPA/EnterpriseSG monthly series suffice for lead-lag claims with ~24 usable months of twin-satellite S1 (2025+) — may need to include 12-day era for N.
5. GTR article date for the SC trade-finance pilot (cite MAS/SC primary pages instead).

## 10. Sources (direct URLs)
- https://dataspace.copernicus.eu · https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1 · https://documentation.dataspace.copernicus.eu/FAQ.html · https://sentiwiki.copernicus.eu/web/s1-mission · https://sentinels.copernicus.eu/-/sentinel-1-orbital-reconfiguration-dates · https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/sentinel-1 · https://browser.dataspace.copernicus.eu
- https://www.mpa.gov.sg/who-we-are/newsroom-resources/research-and-statistics/port-statistics · https://www.mpa.gov.sg/media-centre/details/strong-growth-momentum-for-maritime-singapore · https://www.mpa.gov.sg/media-centre/details/in-response-to-media-queries-on--vessels--extended-waiting-times-for-berths-in-the-port-of-singapore · https://www.mpa.gov.sg/port-marine-ops/marine-services/bunkering/bunkering-statistics · https://www.mpa.gov.sg/media-centre/details/rotterdam-and-singapore-strengthen-collaboration-on-green-and-digital-shipping-corridor · https://www.portofrotterdam.com/en/news-and-press-releases/rotterdam-and-singapore-strengthen-collaboration-green-and-digital-shipping
- https://oceans-x.mpa.gov.sg · https://oceans-x.mpa.gov.sg/marketplace/apis · https://www.mpa.gov.sg/media-centre/details/singapore-launches-oceans-x-to-advance-maritime-digital-connectivity-and-support-global-trade-flows
- https://data.gov.sg/datasets/d_da030f7028200d19ffcbe4a2d71af39c/view · https://data.gov.sg/collections/390/view · https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view · https://data.gov.sg/datasets/d_8f264219109e61fffa87ac64dd5a9a65/view · https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view · https://data.gov.sg/datasets/d_c41b1f16d0847996b1dcfd2ded0b2d91/view
- https://www.straitstimes.com/singapore/transport/singapores-port-sets-new-records-for-vessel-arrivals-shipping-containers-handled-in-2024 · https://www.offshore-energy.biz/mpa-alternative-bunker-fuel-sales-exceed-1-million-tonnes-in-2024 · https://www.seatrade-maritime.com/tankers/malacca-strait-vessel-traffic-at-record-levels-in-2025 · https://www.enterprisesg.gov.sg/-/media/esg/files/media-centre/media-releases/2025/february/mr00425_review-of-2024-trade-performance.pdf (saved locally)
- Papers as listed in §6.
