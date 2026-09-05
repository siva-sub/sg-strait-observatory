#!/usr/bin/env python3
"""Week-3 econ join: satellite vessel counts vs official monthly series.

Reads experiments/data/official/*.csv + experiments/results/monthly_counts_v3.csv.
Auto-parses month columns (YYYY-MM or YYYYMM), picks value = explicit 'total...' column
when present else SUM of numeric columns (valid for by-type breakdowns).
Outputs: econ_join.csv (merged monthly table), printed Pearson/Spearman + lead-lag,
econ_join_chart.png (official series vs satellite counts, dual axis).

Honesty note: n ~ 10-12 overlapping months -> correlations are INDICATIVE ONLY.
"""
import glob, os, re
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def parse_series(path):
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    mcol = next((c for c in df.columns if re.search(r"month|date|period", c)), None)
    if mcol is None:
        return None, "no month column"
    def norm(v):
        s = str(v)[:7].replace("-", "")
        if re.fullmatch(r"\d{6}", s): return f"{s[:4]}-{s[4:]}"
        return None
    df["month"] = df[mcol].map(norm)
    df = df.dropna(subset=["month"])
    num = [c for c in df.columns if c not in ("month", mcol, "_id")
           and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.8]
    if not num:
        return None, "no numeric columns"
    PREF = ["container_throughput", "number_of_vessels", "bunker_sales", "gross_tonnage"]
    pick = next((c for c in PREF if c in num), None)
    tot = [c for c in num if "total" in c]
    if pick:
        df["value"] = pd.to_numeric(df[pick], errors="coerce"); vcol = pick
    elif len(num) == 1:
        df["value"] = pd.to_numeric(df[num[0]], errors="coerce"); vcol = num[0]
    elif len(tot) == 1:
        df["value"] = pd.to_numeric(df[tot[0]], errors="coerce"); vcol = tot[0]
    else:
        df["value"] = sum(pd.to_numeric(df[c], errors="coerce").fillna(0) for c in num); vcol = f"sum({len(num)} cols)"
    s = df.groupby("month")["value"].sum().sort_index()
    return s, vcol

sat = pd.read_csv("experiments/results/monthly_counts_v3.csv", dtype={"month": str})
sat["month"] = sat["month"].str[:4] + "-" + sat["month"].str[4:]

series = {}
for p in sorted(glob.glob("experiments/data/official/*.csv")):
    name = os.path.basename(p)[:-4]
    s, info = parse_series(p)
    if s is None:
        print(f"{name}: SKIP ({info})"); continue
    series[name] = s
    print(f"{name}: parsed value={info} | {len(s)} months | {s.index[0]}..{s.index[-1]} | last={s.iloc[-1]:,.0f}")

merged = sat.set_index("month").join(pd.DataFrame(series), how="outer").sort_index()
merged.to_csv("experiments/results/econ_join.csv")
print("\nmerged table (last 8 rows):")
print(merged.tail(8).to_string(float_format=lambda x: f"{x:,.0f}"))

print("\n=== correlations vs satellite counts (overlap only) ===")
targets = [c for c in series]
rows = []
for t in targets + ["port_core", "eastern_opl", "western_opl"]:
    pass  # satellite zones handled below
def corr_pair(a, b, label):
    m = a.dropna().align(b.dropna(), join="inner")
    x, y = m[0], m[1]
    n = len(x)
    if n < 6:
        print(f"{label}: n={n} too small"); return
    pr, pp = stats.pearsonr(x, y); sr, sp = stats.spearmanr(x, y)
    print(f"{label}: n={n} | Pearson r={pr:+.2f} (p={pp:.3f}) | Spearman ρ={sr:+.2f} (p={sp:.3f})")
    rows.append((label, n, pr, pp, sr, sp))
    # lead-lag: satellite month t vs official t+k
    for k in (-1, 0, 1, 2):
        yk = y.copy(); yk.index = y.index.map(lambda m: shift_month(m, -k))
        mm = x.dropna().align(yk.dropna(), join="inner")
        if len(mm[0]) >= 6:
            r2, _ = stats.pearsonr(mm[0], mm[1])
            if k != 0: print(f"    lead-lag k={k:+d} (sat leads official by {k}mo): r={r2:+.2f} (n={len(mm[0])})")

def shift_month(ym, k):
    y, m = map(int, ym.split("-")); t = y * 12 + (m - 1) + k
    return f"{t//12:04d}-{t%12+1:02d}"

for t in targets:
    corr_pair(merged["total"], merged[t], f"sat_total vs {t}")
for z in ["port_core", "eastern_opl", "western_opl"]:
    if "container" in series: corr_pair(merged[z], merged["container"], f"sat_{z} vs container")
    if "bunker" in series: corr_pair(merged[z], merged["bunker"], f"sat_{z} vs bunker")

# chart: container TEU vs satellite total
if "container" in series:
    m = merged.dropna(subset=["total", "container"])
    if len(m) >= 6:
        fig, ax1 = plt.subplots(figsize=(11, 5), dpi=110)
        ax2 = ax1.twinx()
        ax1.bar(m.index, m["container"], color="#9ecae1", label="Container throughput (TEU)")
        ax2.plot(m.index, m["total"], "o-", color="crimson", label="Satellite vessel count")
        ax1.set_ylabel("TEU"); ax2.set_ylabel("ships in scene")
        ax1.set_title(f"Singapore Strait: satellite vessel counts vs container throughput (n={len(m)} months)")
        ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
        plt.xticks(rotation=45)
        fig.tight_layout(); fig.savefig("experiments/results/econ_join_chart.png")
        print("saved experiments/results/econ_join_chart.png")
