#!/usr/bin/env python3
"""Detrended analysis of the per-scene satellite index vs official series.

Findings (2026-09-04, n=141 months 2015-01..2026-09):
- LEVEL correlations are trend-dominated and era-unstable: 2015-19 r=-0.82 vs container,
  but 2020-22 and 2023-26 eras show no significant correlation (all p>0.1).
- Era means fall 344 -> 277 -> 269 ships/overpass: a ~2020 level break (candidate causes:
  COVID presence collapse + S1 processing-baseline/calibration drift + fleet consolidation
  into fewer/larger vessels — confounded, cannot separate with current data).
- DETRENDED (YoY, and MA3-YoY): no significant nowcast correlation for container/arrivals.
  One weak positive hint: bunker sales, MA3-YoY Spearman rho=+0.19 (p=0.035) — borderline,
  single test, treat as hypothesis only.
Conclusion: CFAR monthly presence counts do NOT nowcast monthly official trade statistics.
Satellite index value proposition pivots to: (a) event monitoring (congestion queues),
(b) structural change (fewer-but-bigger ships), (c) specialized anchorage dwell (bunker).
"""
import pandas as pd
from scipy import stats

m = pd.read_csv("experiments/results/perscene_join.csv", index_col=0).dropna(subset=["total_mean"])

def rep(x, y, label):
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 12: print(f"{label}: n={len(d)} too small"); return
    pr, pp = stats.pearsonr(d.iloc[:,0], d.iloc[:,1]); sr, sp = stats.spearmanr(d.iloc[:,0], d.iloc[:,1])
    print(f"{label}: n={len(d)} | Pearson r={pr:+.2f} (p={pp:.3f}) | Spearman ρ={sr:+.2f} (p={sp:.3f})")

print("=== LEVELS by era ===")
for era, lo, hi in [("2015-2019","2015-01","2019-12"),("2020-2022","2020-01","2022-12"),("2023-2026","2023-01","2026-08")]:
    s = m.loc[lo:hi]
    print(f"-- {era} (n={len(s)}) | mean {s['total_mean'].mean():.0f} ships/overpass | sd {s['total_mean'].std():.0f}")
    for t in ["container","arrivals","bunker"]:
        if t in s: rep(s["total_mean"], s[t], f"   total vs {t}")

print("\n=== YoY detrended ===")
d = m[["total_mean","eopl","wopl","port","container","arrivals","bunker"]].pct_change(12).dropna(how="all")
for t in ["container","arrivals","bunker"]:
    rep(d["total_mean"], d[t], f"d(total) vs d({t})")

print("\n=== MA3-YoY detrended ===")
ma = m[["total_mean","container","arrivals","bunker"]].rolling(3).mean().pct_change(12).dropna()
for t in ["container","arrivals","bunker"]:
    rep(ma["total_mean"], ma[t], f"d(MA3 total) vs d(MA3 {t})")
