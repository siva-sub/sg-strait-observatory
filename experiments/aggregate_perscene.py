#!/usr/bin/env python3
"""Aggregate per-scene counts -> monthly index (IMF/Cerdeiro et al. 2020 style), then econ join.

Method lineage: per-overpass-day presence counts within explicit port/anchorage polygons ->
monthly mean with 95% t-CI and n_days -> index normalized to first-12-month mean (=100) ->
join official series -> Pearson/Spearman + lead-lag.
"""
import os
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "experiments/results/perscene_counts.csv"
OFF = "experiments/data/official"

with open(SRC) as _f:
    _f.readline(); _first = _f.readline().rstrip("\n")
_cols7 = ["day", "sat", "total", "port_core", "eastern_opl", "western_opl", "other"]
if _first.count(",") == 6:  # legacy 7-field OK rows (pre-fix writer had no status col)
    df = pd.read_csv(SRC, dtype={"day": str}, skiprows=1, header=None, names=_cols7)
    df = df.drop_duplicates(subset="day", keep="last")
else:
    df = pd.read_csv(SRC, dtype={"day": str})
    if "status" in df.columns:
        df = df[df["status"] == "OK"].copy()
df = df.dropna(subset=["total"])
df["month"] = df["day"].str[:4] + "-" + df["day"].str[4:6]
print(f"per-scene rows OK: {len(df)} | {df['month'].min()}..{df['month'].max()}")

# per-day sanity: drop days with absurd counts (weather bursts > 3x median of month)
g = df.groupby("month")
monthly = g.agg(n_days=("day", "nunique"),
                total_mean=("total", "mean"), total_sd=("total", "std"),
                port=("port_core", "mean"), eopl=("eastern_opl", "mean"),
                wopl=("western_opl", "mean"))
monthly["ci95"] = 1.96 * monthly["total_sd"] / np.sqrt(monthly["n_days"].clip(lower=1))
base = monthly["total_mean"].head(12).mean()
monthly["index"] = 100.0 * monthly["total_mean"] / base
monthly.round(2).to_csv("experiments/results/perscene_monthly.csv")
print(monthly.round(1).tail(12).to_string())
print(f"\nbase (first 12-mo mean) = {base:.1f} ships/overpass | saved perscene_monthly.csv")

# --- official join ---
def parse_series(path):
    d = pd.read_csv(path); d.columns = [str(c).strip().lower() for c in d.columns]
    mcol = next(c for c in d.columns if "month" in c)
    d["month"] = d[mcol].astype(str).str[:7]
    num = [c for c in d.columns if c not in ("month", mcol, "_id")
           and pd.to_numeric(d[c], errors="coerce").notna().mean() > 0.8]
    PREF = ["container_throughput", "number_of_vessels", "bunker_sales"]
    pick = next((c for c in PREF if c in num), num[0] if len(num) == 1 else None)
    if pick is None:
        pick = next((c for c in num if "total" in c), num[0])
    d["value"] = pd.to_numeric(d[pick], errors="coerce")
    return d.groupby("month")["value"].sum().sort_index(), pick

series = {}
for name in ["container", "arrivals", "bunker"]:
    p = f"{OFF}/{name}.csv"
    if os.path.exists(p):
        s, col = parse_series(p); series[name] = s

m = monthly.join(pd.DataFrame(series), how="left")
m.to_csv("experiments/results/perscene_join.csv")

print("\n=== correlations (monthly means, overlap only) ===")
def report(x, y, label):
    mm = pd.concat([x, y], axis=1).dropna()
    n = len(mm)
    if n < 8: print(f"{label}: n={n} (too small)"); return
    pr, pp = stats.pearsonr(mm.iloc[:, 0], mm.iloc[:, 1])
    sr, sp = stats.spearmanr(mm.iloc[:, 0], mm.iloc[:, 1])
    print(f"{label}: n={n} | Pearson r={pr:+.2f} (p={pp:.3f}) | Spearman ρ={sr:+.2f} (p={sp:.3f})")

for t in series:
    report(m["total_mean"], m[t], f"sat_total_mean vs {t}")
    report(m["eopl"], m[t], f"sat_eOPL_mean vs {t}")
    report(m["wopl"], m[t], f"sat_wOPL_mean vs {t}")

if "container" in series and m["total_mean"].notna().sum() > 8:
    mm = m.dropna(subset=["total_mean", "container"])
    fig, ax1 = plt.subplots(figsize=(13, 5.5), dpi=110)
    ax2 = ax1.twinx()
    ax1.bar(mm.index, mm["container"], color="#9ecae1", label="Container throughput (TEU)")
    ax1.errorbar(mm.index, mm["total_mean"], yerr=mm["ci95"], fmt="o-", color="crimson",
                 capsize=3, label="Satellite ships/overpass (±95% CI)")
    ax1.set_ylabel("TEU / ships"); ax1.tick_params(axis="x", rotation=60)
    ax1.set_title(f"Singapore Strait per-scene index vs container throughput (n months={len(mm)})")
    ax1.legend(loc="upper left")
    fig.tight_layout(); fig.savefig("experiments/results/perscene_join_chart.png")
    print("saved experiments/results/perscene_join_chart.png")
