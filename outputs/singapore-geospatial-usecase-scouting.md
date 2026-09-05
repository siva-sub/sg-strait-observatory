# Singapore Geospatial Portfolio Project — Use-Case Scouting Brief

**Session:** autoresearch discovery loop, 2026-09-04 · **Mode:** evidence-ranked candidate selection
**Profile constraint:** junior product owner (bank international settlement) + freelance tokenization SME (GFTN); needs a portfolio project with **economic relevance**, Singapore-specific, head-turning like `Vorld/singapore-travel-time-map`, and built on **free international satellite data (Copernicus/Landsat)**.

---

## 1. Recommendation (rank 1): **Singapore Strait Observatory**
### *"Nowcast Singapore's trade, port activity and shipping emissions from free satellite data — before the official numbers drop."**

Detect, count, and track vessels in Singapore's port waters and anchorages from **Sentinel-1 SAR** (works at night, through clouds — critical in the tropics) and **Sentinel-2** (daytime optical), then turn detections into **economic indicators** validated against official statistics.

**Why it is economically valuable (the interview pitch):**
1. **Leading indicator for trade/settlement volumes.** Official MPA container/cargo throughput and SingStat trade figures arrive with a lag; satellite vessel counts arrive continuously. This is a nowcasting demo of the kind banks, trade-finance desks, and supply-chain teams pay for. The method is proven at IMF/World Bank scale: *Arslanalp, Koepke & Verschuur (2021), "Tracking trade from space: an application to Pacific island countries."*
2. **Port congestion index.** Singapore's 2024 congestion episode made global freight headlines. Queue length in the Eastern/Western OPL and EPL anchorages vs. berth throughput = demurrage/detention risk, freight-rate pressure — directly monetizable insight.
3. **Bunkering nowcast.** Singapore is the world's top bunkering port; dwell time of vessels at bunkering anchorages can be compared with MPA bunker-sales statistics — a uniquely Singapore angle nobody has demoed publicly.
4. **Compliance / dark-vessel watch (optional module).** AIS-off and unusual ship-to-ship transfer detection — sanctions & trade-based-Money-laundering screening narrative that resonates with a banking background. Template: *Ballinger (2024), arXiv 2404.07607* (open CNN pipeline for dark STS detection).
5. **Maritime-emissions ledger (iteration-6 upgrade).** Sentinel-5P TROPOMI can resolve NO₂ plumes of **individual large ships** — established in *Batista, Jamal & Isbaex et al. (2025), "Sentinel Data for Monitoring of Pollutant Emissions by Maritime Transport — A Literature Review," Remote Sensing 17(13):2202*. Fuse with S1 vessel tracks → a per-corridor pollution ledger for the Strait. Economic hook: shipping entered the EU ETS in 2024 and IMO carbon rules are tightening; verify the current status of Singapore's green-corridor initiatives (e.g., SG–Rotterdam Green & Digital Shipping Corridor) before citing. This turns the project from a trade index into a **trade + carbon dual-ledger** — a story carbon markets, trade-finance and ESG desks all recognize.
6. **Tokenization bridge (optional spin for GFTN audiences).** A satellite-derived trade-activity feed is a credible **oracle data layer for tokenized real-world assets** (tokenized trade finance / port revenue instruments). Academic anchor: *Cong, Mayer & Rabetti (2025), "Tokenizing real-world assets," SSRN 7094059* — which explicitly discusses oracles and valuation as the hard part of RWAs.

**Data stack (all free):**

| Layer | Source | Notes |
|---|---|---|
| Vessel detection (primary) | Sentinel-1 GRD IW, Copernicus Data Space Ecosystem (CDSE) | Free; cloud/night independent; SLC/GRD available ~1 month post-publication + full archive |
| Vessel detection (validation) | Sentinel-2 L2A, CDSE | Daytime, 10 m; frequent cloud loss in tropics → secondary role |
| Ground truth #1 | MPA **Container Throughput, Monthly** (data.gov.sg `d_da030f7028200d19ffcbe4a2d71af39c`) | Monthly TEU, verified dataset page |
| Ground truth #2 | MPA **Cargo Throughput, Monthly** (data.gov.sg collection 390) | By cargo type |
| Ground truth #3 | SingStat **Merchandise Trade, Monthly** (data.gov.sg `d_c41b1f16d0847996b1dcfd2ded0b2d91`) | Current prices, seasonally adjusted |
| Context | MPA Port Statistics page; **OCEANS-X** (oceans-x.mpa.gov.sg, MPA's own maritime data platform) | Benchmark of what the official ecosystem offers |
| Basemap | OneMap tiles (SLA, Singapore Open Data Licence) + MapLibre | Same stack as the travel-time-map anchor repo |

**Method pipeline (v0):**
1. CDSE account → OData/OpenSearch query: all S1 GRD IW scenes intersecting a Singapore Strait AOI (port + anchorages), last 12–24 months.
2. Preprocess GRD (calibration, speckle filter, land-sea mask via coastline polygon).
3. Vessel detection: CA-CFAR thresholding first; upgrade to a pretrained/tuned detector using **LS-SSDD** (large-scale SAR ship detection dataset built from Sentinel-1, 78★) or adapt `MJCruickshank/SARfish` (160★).
4. Spatial aggregation: counts inside named polygons (port limit, EPL, Eastern OPL, Western OPL anchorage approximations).
5. Monthly aggregation → correlate/lead-lag against MPA container & cargo throughput and SingStat merchandise trade (levels and YoY changes).
6. Frontend: MapLibre + OneMap basemap, vessel density heatmap, time slider (echoes the travel-time map's UX), plus a chart panel overlaying satellite index vs. official stats.

**MVP scope (2 weekends):**
- Weekend 1: CDSE account; download ~24 S1 scenes spanning 12 months; CFAR detection; density map + anchorage counts.
- Weekend 2: join MPA/SingStat monthly series; correlation + lead-lag notebook; single-page dashboard; README with method, caveats, and the economic story.

**v1 (≈6 weeks):** vessel-size-based class proxies (tanker vs container vs bulk) per anchorage; bunker-anchorage dwell vs MPA bunker sales (verify bunker dataset availability on MPA research & statistics page — not yet verified in this session); 2024 congestion case study; dark-vessel alert prototype; deck.gl animated "strait in motion" hero visual; write-up framed for trade-finance/settlement readers.

**Risks & mitigations (state honestly):**
- **Sentinel-1 revisit over the equator** is multi-day (not daily) — sufficient for monthly official-stat correlation, not for daily ops. Verify actual scene frequency over the AOI in the CDSE catalogue during MVP.
- **No free historical AIS for Singapore waters** (global AIS is commercial; Danish DMA free AIS covers Danish waters only). Mitigate: validate class/dwell via Sentinel-2 optical samples + monthly official stats; optionally buy one month of AIS for a gold-standard validation chapter.
- **S2 cloud loss** in the tropics is severe — hence SAR-first architecture (documented tropical cloud/gap-filling literature exists, e.g., arXiv 2309.12416 for LST interpolation under clouds).
- **GRD resolution (~20×22 m)** misses small craft; targets are large commercial vessels — acceptable for a trade indicator.

**Why this beats a clone of the travel-time map:** travel-time/isochrone apps are crowded (Seoul `vuski/seoulsubway`, London `adamjamesfrench-ldn/london-travel-time`, `econaxis/time2reach`, `switzograms` for Switzerland — and Vorld already did Singapore properly with r5py/RAPTOR precomputation). Nothing in the SG GitHub landscape combines EO + port economics.

---

## 2. Runner-up (rank 2): **EO Valuation Oracle for Tokenized Singapore Real Assets**
*"Satellite-derived environmental factors (heat, greenery, flood/subsidence exposure) as a valuation layer for HDB assets — the missing data oracle for tokenized real-world assets."*

- Build Landsat LST (heat), Sentinel-2 NDVI (greenery), and flood/subsidence exposure layers; join to **HDB Resale Flat Prices 1990–2025** (data.gov.sg collection 189); estimate hedonic price effects; publish per-town/factor scores framed as oracle feeds for RWA tokenization.
- Evidence: **Giglio, Maggiori & Rao (2021, *Review of Financial Studies* 34(8))** — climate risk priced in real estate and long-run discount rates; **McNamara et al. (2024, *Nature Communications*)** — coastal price dynamics under SLR; **Jusuf et al. (2007, *Habitat International*)** — the classic Singapore UHI/Landsat study; **Catalão & Nico (2020, *Remote Sensing* 12(2):296)** — InSAR subsidence + sea-level flood risk for Singapore; **arXiv 2604.22433 (Apr 2026)** — LST vs UTCI heat-mapping **in Singapore** with GW-XGBoost (validates data + shows the pure-science niche is taken → differentiate via the finance/RWA framing); **Cong/Mayer/Rabetti (2025)** for the tokenization-oracle framing.
- Risk: HDB hedonics is a common student project; only the RWA/oracle + climate-risk framing makes it non-generic.

## 3. Rank 3: **NO₂ Economy Nowcast (Sentinel-5P)**
TROPOMI NO₂ as a proxy for local economic activity — *Parubets & Naito (2025, PLOS ONE)* did this for Japan; nobody has done it for the Singapore–Johor corridor. Elegant but a smaller "wow" than the port; strong complement to #1 (same CDSE account, same economics story).

## 4. Rank 4 (context): Coastal/land-reclamation change atlas & InSAR subsidence
Beautiful storytelling (Landsat archive since 1972; Singapore grew its land area by reclamation; CoastSat toolkit — Vos et al. 2019, 657 citations; DEA CoastLines method — Bishop-Taylor et al. 2021; Singapore-specific subsidence papers exist: Catalão 2020, Bai et al. 2023). **Dropped from rank 1–2 for lack of direct economic hook** under the user's constraint; keep as an appendix module (e.g., the "how much land did Singapore buy/make" narrative page).

---

## 5. Transplant scan (iteration 6): proven in other jurisdictions, not yet in Singapore

| # | Idea (origin jurisdiction) | Evidence | Singapore transplant | Economic hook | Verdict |
|---|---|---|---|---|---|
| T1 | Tracking trade/port activity from space (Pacific islands — IMF/World Bank) | Arslanalp et al. 2021; Chico et al. 2025 (strait passageways) | → Strait vessel-count index vs MPA/SingStat | Trade-finance leading indicator | **Absorbed into rank 1** |
| T2 | Maritime emission-plume detection from TROPOMI (EU literature) | Batista et al. 2025, Remote Sensing 17(13):2202 (individual-ship NO₂ plumes) | → Strait carbon/pollution ledger | EU ETS/IMO carbon accounting | **Absorbed into rank 1 (module 5)** |
| T3 | Construction-progress monitoring from InSAR coherence time series (China) | Mohamadi, Balz et al. 2026, Geo-spatial Information Science | → **"BTO from orbit"**: track HDB BTO estates under construction from S1/S2 time series; SG GitHub has BTO ballot/price apps but **no satellite monitoring** (whitespace verified via gh) | BTO waiting times ↔ resale prices; construction-delay economics | **New candidate — co-rank 2** |
| T4 | Shade-aware pedestrian routing (Berlin ABM; HCMC GeoAI) | Verma, Mumm & Carlow 2026 (Berlin); Hot Hẻm arXiv 2512.11896 (HCMC: GSV+LST, OSMnx routing); open code `henrik-wolf/CoolWalks` 7★, Taipei student port | → "Cool Walks Singapore" on NParks canopy + OneMap network | Health/productivity; weaker finance hook | Rank 3 (companion project) |
| T5 | Nationwide rooftop-PV mapping (US: DeepSolar; Germany: DeepSolar-DE) | `wangzhecheng/DeepSolar` 267★; `kdmayer/3D-PV-Locator` 63★; Kasmi et al. arXiv 2408.07828 | → HDB rooftop solar audit vs SolarNova targets | Energy economics | Honorable mention — SERIS already publishes SG solar maps (check novelty) |
| T6 | Crowdsourced real-time flood map (Jakarta/Bandung: PetaBencana) | `urbanriskmap/petabencana-*` on GitHub | → PUB-flood transplant | Weak economic hook; PUB already alerts | Pass |

**Note on T3 (BTO from orbit):** every Singaporean knows the BTO waiting-time story; a public map of "which BTO site is actually progressing, seen from Sentinel-1/Sentinel-2" is emotionally sticky, technically grounded in Mohamadi et al. 2026 (InSAR coherence time series detects project-development phases), and links to open HDB resale data for the property-economics angle. Risk: S1 coherence over equatorial vegetation + small sites needs care; fallback is S2 bare-soil/NDVI change detection at 10 m.

## 6. Evidence inventory (provenance)

**Anchor repos (user-provided):** `Vorld/singapore-travel-time-map` (25★, AGPL, live at traveltime.sg; React/MapLibre/OneMap, r5py+RAPTOR precomputed isochrones, self-built `Vorld/singapore-gtfs`); `eu-cdse/copernicus-browser` (88★, MIT; source of the CDSE Sentinel-1/2/3/5P browser, timelapses, WMS, evalscripts); `eu-cdse/sentinel-hub-custom-scripts` (evalscript patterns for rendering satellite products).

**Selected international demos (gh CLI sweep, 22 queries, full log in `notes/discovery/gh_summary_all.txt`):** `gee-community/geemap` 4022★, `developmentseed/titiler` 1157★ (raster tiles server), `phelber/EuroSAT` 573★ (S2 land-use ML), `MJCruickshank/SARfish` 160★, `kvos/CoastSat` (satellite shoreline toolkit), `TianwenZhang0825/LS-SSDD-v1.0-OPEN` 78★ (S1 ship-detection dataset), `gSulpizio/sat_tracker` (SAR+AIS dark-vessel fusion), `damienallen/urban-heat` (interactive UHI explorer), `econaxis/time2reach`, `vuski/seoulsubway`, `adamjamesfrench-ldn/london-travel-time` (travel-time genre). Singapore landscape: `gpng/onemap-react-maplibre-demo`, `jtlx/singapore-mrt-voronoi`, `foldaway/mrtdown-site`, `elliotwutingfeng/railrailrail` — **no port/EO economics project found** (whitespace confirmed).

**Key papers (all URLs verified via search this session unless noted):**
- Arslanalp, Koepke & Verschuur (2021) *Tracking trade from space* — https://books.google.com/books?id=bEZEEAAAQBAJ
- Chico, Cordel, Mariasingham & Tan (2025) *Analyzing anomalous events in passageways with high-frequency ship signals*, PLOS ONE — https://doi.org/10.1371/journal.pone.0320129
- Ballinger (2024) *Automatic Detection of Dark Ship-to-Ship Transfers*, arXiv 2404.07607 — https://arxiv.org/abs/2404.07607
- Pritt (2020) *Deep Learning for Recognizing Mobile Targets in Satellite Imagery*, arXiv 2010.06520
- Parubets & Naito (2025) *Predicting economic activity using atmospheric NO₂*, PLOS ONE — https://doi.org/10.1371/journal.pone.0337901
- Giglio, Maggiori & Rao (2021) *Climate Change and Long-Run Discount Rates*, RFS 34(8):3527 — https://academic.oup.com/rfs/article-pdf/34/8/3527/39071814/hhab032.pdf
- McNamara et al. (2024) *Policy and market forces delay real estate price declines on the US coast*, Nat. Comms. — https://doi.org/10.1038/s41467-024-46548-6
- Cong, Mayer & Rabetti (2025) *Tokenizing real-world assets*, SSRN 7094059 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7094059
- Catalão & Nico (2020) *InSAR … Flood Inundation Risk in Coastal Cities: The Case of Singapore*, Remote Sens. 12(2):296 — https://www.mdpi.com/2072-4292/12/2/296
- Jusuf, Wong, Hagen, Anggoro & Hong (2007) *The influence of land use on the urban heat island in Singapore*, Habitat Int. — https://www.sciencedirect.com/science/article/pii/S0197397507000148
- arXiv 2604.22433 (2026) *LST and UTCI heat mapping … in Singapore* — https://arxiv.org/abs/2604.22433 (abstract read via curl_cffi)
- Bai et al. (2023) *Land subsidence in the Singapore coastal area with TerraSAR-X*, Remote Sens. 15(9):2415 — https://www.mdpi.com/2072-4292/15/9/2415 (page fetched 200; abstract not parsed — **unverified content**)
- Vos et al. (2019) *CoastSat*, Environ. Model. Softw. — DOI 10.1016/j.envsoft.2019.104528 (OpenAlex W2977103245, 657 cites)
- Bishop-Taylor et al. (2021) *Mapping Australia's dynamic coastline*, RSE — DOI 10.1016/j.rse.2021.112734 (282 cites)
- Hanami et al. (2025) *Sumatra air pollutants from Sentinel-5P*, Urban Science 9(2):42 — https://www.mdpi.com/2413-8851/9/2/42 (transboundary-haze template)
- Batista, Jamal, Isbaex et al. (2025) *Sentinel Data for Monitoring of Pollutant Emissions by Maritime Transport — A Literature Review*, Remote Sensing 17(13):2202 — https://www.mdpi.com/2072-4292/17/13/2202 (individual-ship NO₂ plumes; iteration-6 find)
- Mohamadi, Balz, Pirasteh et al. (2026) *Detecting and monitoring urban project development from space: InSAR coherence time series*, Geo-spatial Information Science — https://www.tandfonline.com/doi/abs/10.1080/10095020.2025.2542976 (iteration-6 find)
- Verma, Mumm & Carlow (2026) *Seeking shade: shadow-focused pedestrian movement (Berlin)*, Transportation Research Interdisciplinary Perspectives — https://www.sciencedirect.com/science/article/pii/S2590198226000485
- Kasmi et al. (2024) *Space-scale exploration of the poor reliability of DL for rooftop-PV remote sensing*, arXiv 2408.07828; DeepSolar repos: `wangzhecheng/DeepSolar` (267★), `kdmayer/3D-PV-Locator` (63★)
- Biljecki & Ito (2021) *Street view imagery in urban analytics and GIS: A review*, Landscape & Urban Planning (GSV-methods backbone for T4)

**Singapore data sources:** data.gov.sg datasets listed above; OneMap (onemap.gov.sg, SLA); MPA port statistics (mpa.gov.sg/who-we-are/newsroom-resources/research-and-statistics/port-statistics); OCEANS-X (oceans-x.mpa.gov.sg); LTA DataMall (transit layer, if a mobility module is added).

**Satellite access:** Copernicus Data Space Ecosystem — free, open access to Sentinel-1/2/3/5P + Landsat 8/9 (browser + APIs: OData, Sentinel Hub incl. evalscripts, openEO) — https://dataspace.copernicus.eu ; verified working: chromiumfish loaded the Copernicus Browser over Singapore coordinates without issue (session log `autoresearch.jsonl`).

## 7. Open questions / next steps
1. Verify Sentinel-1 scene frequency over the Singapore Strait AOI in the CDSE catalogue (decides index granularity).
2. Check MPA research & statistics page for monthly **bunker sales** series (unlocks the bunkering-nowcast module).
3. Decide MVP detection route: CFAR-only (fast) vs LS-SSDD-trained detector (better classes).
4. Optional AIS purchase (1 month) for a validation appendix; else rely on S2 samples + official monthly stats.
5. Name/branding pass; then scaffold repo (`sg-strait-observatory`), reuse MapLibre+OneMap stack from `gpng/onemap-react-maplibre-demo` and the anchor repo's static-data pattern (~small static artifacts on R2/Pages, no server needed).

*Session files:* `autoresearch.md` (plan/ledger), `autoresearch.jsonl` (iteration log), `autoresearch.sh` (reproducible gh sweep), `notes/discovery/` (raw search JSON), `notes/papers/` (fetched paper HTML), `CHANGELOG.md`.
