# Economic Relevance

Why satellite-based port monitoring matters, grounded in the Singapore case study.

## The core problem

Port trade statistics are published with a 2-4 week lag. By the time you know January's bunker sales, it's mid-February. For markets, supply chains, and policy decisions, that lag is expensive:

- **Fuel traders** price bunker contracts on last month's data
- **Supply chain managers** reroute vessels based on stale congestion information
- **Central banks** track trade flows quarterly, missing month-to-month turning points
- **Port authorities** see congestion building but lack quantitative metrics until after the fact

Satellite radar closes this gap. It images every port on Earth every 6-12 days, at night, through clouds, for free. The data exists **before** official statistics are compiled.

## The Singapore case study

Singapore is the world's largest bunkering port (54.92 million tonnes sold in 2024) and second-busiest container port (41.12 million TEU). Its monthly statistics are excellent — but published 2-3 weeks after the fact.

We built a pipeline that:

1. Detects every vessel at anchor in the Singapore Strait from Sentinel-1 radar
2. Counts them by anchorage zone (bunkering area, container area, bulk area)
3. Compares those counts to official monthly statistics

### What we found

**A satellite radar, alone, explains 48% of Singapore's bunker sales variance.**

| Model | R² | What it means |
|---|---|---|
| Satellite radar only | **0.478** | Nearly half the variance, no other data needed |
| + ERA5 wind control | 0.495 | Weather adds almost nothing (signal is clean) |
| + official tanker arrivals | **0.700** | Practical nowcasting model |

**The mechanism is confirmed:** the anchorage zone that tracks bunker sales (eOPL) is 77% tankers by AIS vessel type. These are ships waiting to bunker — refueling other vessels. When there are more tankers at anchor, more fuel is being sold.

**The signal is weather-robust:** controlling for wind speed barely changes the correlation (partial r = +0.696 vs raw +0.691). The satellite index measures real vessel presence, not sea-state artifacts.

**The signal survives detrending:** year-over-year changes in satellite counts correlate with YoY changes in bunker sales (r = +0.46). This isn't just two things trending upward — the *changes* track each other.

**Independent confirmation:** VIIRS nighttime lights (optical satellite, different sensing modality) also track the economy (+1.1% growth 2018→2021 in port-area radiance, matching eOPL growth).

### What we honestly could not do

- **Beat a persistence baseline.** Our out-of-sample nowcast (train on 2021-2023, test on 2024-2026) achieved 15% skill over the unconditional mean but did NOT beat naive persistence (predicting last month's change). Bunker sales are highly autocorrelated — a simple baseline is hard to beat with n=27 test months.

- **See the 2024 congestion episode.** The H1-2024 congestion (which made global headlines) did NOT show up as an anchorage-count spike. It was a waiting-time event, not a count event. Monthly count metrics capture volume, not delay.

- **Confirm the mega-ship hypothesis.** We initially found a declining ships-per-TEU trend (consistent with larger vessels carrying more cargo). After proper detector calibration, this trend disappeared — it was an artifact of mixing detector versions. We retracted it.

## Why this matters economically

### For trade finance and settlement

The user's background: a junior product owner in bank international settlement, now a freelance tokenization SME. Banks and clearing houses need real-time trade flow indicators for:

- **Trade finance pricing:** Letters of credit priced on last month's data are mispriced if activity shifted this month
- **Settlement volume forecasting:** Port activity is a leading input to settlement volumes (more trade = more transactions)
- **Risk assessment:** A sudden drop in port activity signals supply chain disruption before it appears in official data

A satellite-derived index available 2-3 weeks before official prints gives financial institutions a measurable information advantage. Even R² = 0.478 (48% of variance) is actionable when the alternative is waiting 3 weeks for 100% of the data.

### For tokenization and RWA

Real-world assets (RWAs) increasingly need verifiable, independent data feeds:

- **Tokenized trade finance instruments** need underlying trade flow data for pricing
- **Port revenue bonds** need port activity metrics for covenant monitoring
- **Supply chain finance platforms** need real-time activity indicators for risk scoring

A satellite-derived index is:
- **Independent** (not self-reported by any counterparty)
- **Objective** (radar measurements, not survey responses)
- **Frequent** (every 6-12 days, not monthly/quarterly)
- **Free** (Sentinel-1 is ESA's open data mission)

This is exactly the kind of oracle data that tokenized financial instruments need — an independent, machine-readable, frequently-updated measure of real economic activity.

### For port authorities and maritime insurers

- **Congestion monitoring:** Quantify how busy anchorages are (though our research shows count-based metrics miss waiting-time congestion)
- **Traffic pattern shifts:** Detect when vessels move between anchorage zones (e.g., more tankers = more bunkering demand)
- **Insurance pricing:** Ports with consistently high anchorage occupancy may carry different risk profiles

## Generalization: does this work for other ports?

We analyzed AIS data from 11 ports worldwide (Mendeley dataset, October 2023):

| Port | Vessels | Anchored % | Tanker % | Profile |
|---|---|---|---|---|
| **Singapore** | **5,850** | **80.2** | **52.0** | **Bunkering-dominated** |
| Antwerp | 4,629 | 77.3 | 44.4 | Mixed cargo/tanker |
| Algeciras | 2,891 | 42.3 | 47.7 | Bunkering hub (like Singapore) |
| Busan | 1,410 | 81.9 | 39.8 | Container-focused |
| Southampton | 194 | 87.4 | 60.0 | Small, tanker-heavy |

**Singapore's profile is distinctive:** high anchored share + high tanker share = a bunkering-dominated port. Algeciras (also a major bunkering hub) is the closest parallel.

**The method is portable; the interpretation is port-specific:**
- For bunkering ports (Singapore, Algeciras, Rotterdam, Fujairah): satellite anchorage counts should track bunker sales
- For container ports (Busan, LA, Shanghai): satellite counts should track container throughput
- For bulk ports (Gdansk, Cape Town): satellite counts should track commodity volumes

**The key requirement is open-water anchorages visible to SAR.** Ports with enclosed harbors or inland waterways may have different detection characteristics.

## Data as a public good

Everything in this project is open:

| Component | License | Cost |
|---|---|---|
| Sentinel-1 satellite data | Copernicus open license | Free |
| S2Coast-2023 land mask | Open (Zenodo) | Free |
| AIS from AISStream.io | Free tier | Free |
| Official statistics (data.gov.sg) | Singapore Open Data License | Free |
| ERA5 weather | Copernicus open license | Free |
| strait package | MIT | Free |

The entire pipeline — from satellite download to economic indicator — costs nothing beyond compute time. This is the point: **the data was always free; the pipeline to make sense of it is what was missing.**

## References

- Cerdeiro, Komáromi, Liu & Sridhar (2020), *World Seaborne Trade in Real Time*, IMF
- Arslanalp, Koepke & Verschuur (2021), *Tracking trade from space*, World Bank
- Elvidge et al. (2017/2021), VIIRS nighttime lights, Remote Sensing
- Feng et al. (2020), Bunkering statistics from AIS, Journal of Transport Geography
- Zhou et al. (2026), *Fifty Years of SAR ATR*, arXiv 2509.22159
- [The Singapore Strait Observatory](https://github.com/siva-sub/strait-observatory) — the source project
