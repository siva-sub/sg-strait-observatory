# Provenance — Singapore Strait Observatory Deep-Research Dossier

Session date: 2026-09-04. Tools: degoog meta-search MCP (`search`, web+scholar), `fetch_content`, curl_cffi 0.15.0 (bash), gh CLI, alpha tools, chromiumfish, OpenAlex (feynman_science_database_search). Every claim below maps to a fetch performed this session; "snippet-only" = search-result snippet, page body not read.

| # | Claim in dossier | Source (URL) | Tool / evidence mode |
|---|---|---|---|
| 1 | S$1.3T merchandise trade 2024, +6.6% | enterprisesg.gov.sg MR 004/25 PDF | curl_cffi download + pypdf text read; PDF saved `notes/papers/esg_2024_trade_review.pdf` |
| 2 | 41.12M TEU 2024, +5.4%, ~90% transshipment | mpa.gov.sg "Strong growth momentum"; straitstimes.com | snippets, two corroborating sources |
| 3 | Bunker sales 54.92 Mt 2024 record (+6.0%); alt fuels 1.34 Mt | mpa.gov.sg release; offshore-energy.biz | snippets, corroborated |
| 4 | 2024 congestion: container bunching; 13.36M TEU Jan–Apr 2024; bunker/tanker anchorages unaffected | mpa.gov.sg media response | snippet |
| 5 | Dataset IDs: container `d_da030f7028200d19ffcbe4a2d71af39c`; cargo coll. 390; vessel arrivals total `d_d48c5a038904f6da3c603cd854b6c191`; breakdown `d_8f264219109e61fffa87ac64dd5a9a65` (coll. 394); bunker sales `d_4f5abbf4486bf8e52bbed3be56dde562`; trade `d_c41b1f16d0847996b1dcfd2ded0b2d91` | data.gov.sg dataset pages | snippets from official dataset URLs |
| 6 | S1B failed 2021-12-23; S1C on CDSE since Jan 2025, fully operational May 2025; S1D launched 2025-11-04; June 2026 orbital reconfiguration | dataspace.copernicus.eu; sentiwiki.copernicus.eu; earthdata.nasa.gov; sentinels.copernicus.eu | snippets, corroborated across four official pages |
| 7 | CDSE free tier has quotas (bandwidth + monthly transfer) | documentation.dataspace.copernicus.eu/FAQ.html | snippet |
| 8 | CDSE API family: OData/S3/Sentinel Hub/openEO/STAC | dataspace.copernicus.eu/analyse/apis | snippet |
| 9 | Copernicus Browser loads at Singapore coords | browser.dataspace.copernicus.eu (nav 1.2903, 103.8520) | chromiumfish navigate success (session jsonl) |
| 10 | >100,000 vessel transits 2025 (Malacca+Singapore) | seatrade-maritime.com; thelogisticnews.com | snippets, corroborated |
| 11 | OCEANS-X: 100+ APIs/datasets at launch; API catalogue incl. vessel-arrival breakdown | oceans-x.mpa.gov.sg; mpa.gov.sg launch release | snippets |
| 12 | SG–Rotterdam corridor strengthened 2025-04-09; bio-methane trial in SG planned 2025 | portofrotterdam.com; mpa.gov.sg | snippets, corroborated |
| 13 | SC trade-finance tokenisation pilot under MAS initiative | gtreview.com; sc.com; xdc.org | snippets, corroborated; article date unverified (flagged in dossier §9) |
| 14 | Georgoulias et al. 2020 ERL individual-ship NO₂ plumes; Kurchaba et al. 2022/2023 ML plume papers | iopscience.iop.org 10.1088/1748-9326/abc445; arXiv 2203.06993, 2302.12744 | scholar snippets + arXiv abs pages (fetched earlier in loop for related papers) |
| 15 | Verschuur/Koks/Hall: COVID maritime losses (arXiv 2010.15907), ports criticality (Nat Comms, 218 cites) | arxiv.org; nature.com; sciencedirect.com | scholar/OpenAlex snippets |
| 16 | Iervolino & Guida 2017 GLRT detector; Bae & Yang 2020 S1 false alarms | ieeexplore.ieee.org 7927377; doi.org/10.7780/kjrs.2020.36.4.4 | scholar/OpenAlex snippets |
| 17 | Batista et al. 2025 Remote Sensing 17(13):2202 review (TROPOMI ship-plume limits) | mdpi.com/2072-4292/17/13/2202 | scholar snippet |
| 18 | Cong/Mayer/Rabetti SSRN 7094059 RWA tokenization | papers.ssrn.com | scholar snippet |
| 19 | Repo stats: SARfish 160★, LS-SSDD 78★, DeepSolar 267★, CoastSat top shoreline tool, titiler 1157★, geemap 4022★ | gh CLI searches (notes/discovery/gh*.json) | gh API JSON, star counts from GitHub |
| 20 | TROPOMI NO₂ resolution 3.5×5.5 km² since Aug 2019 | (standard S5P product spec) | dossier §3.3 — **snippet-level only this session; verify on CDSE S5P collection page before publishing** |

Unverified/flagged items deliberately carried: #13 article date; #20 resolution figure; Bai et al. 2023 MDPI abstract content (earlier iteration); MPA anchorage polygon GIS availability (open question §9).
