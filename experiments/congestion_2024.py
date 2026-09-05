#!/usr/bin/env python3
"""H1-2024 Singapore congestion case study (per-scene satellite evidence).

Event: Red-Sea-diversion container bunching; MPA confirmed elevated berth waiting
times Apr-Jul 2024, record throughput (13.36M TEU Jan-Apr), normalization by late July.
Thesis: satellite anchorage presence (eOPL zone) spikes during the event window even
though throughput is at record levels (stock vs flow divergence).

Design:
- Baseline window: 2023-01..2024-03 | Event: 2024-04..2024-07 | Post: 2024-08..2024-12
- Statistic: per-scene eOPL + total counts, Welch t-test event vs baseline, Cohen's d
- Official cross-evidence: monthly container-vessel arrivals (arrivals_br pivot)
Outputs: congestion_2024.csv (monthly), congestion_2024.png (per-scene scatter + means
+ shaded event window + official container arrivals overlay)
"""
import pandas as pd, numpy as np
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

cols9 = ["day","sat","status","cov","total","port_core","eastern_opl","western_opl","other"]
df = pd.read_csv("experiments/results/perscene_counts.csv", dtype={"day": str})
if list(df.columns) != cols9:
    df = pd.read_csv("experiments/results/perscene_counts.csv", dtype={"day": str}, skiprows=1, header=None, names=cols9)
df = df[(df["status"] == "OK") & (df["cov"] >= 0.80)].drop_duplicates("day", keep="last")
df["date"] = pd.to_datetime(df["day"], format="%Y%m%d")
df["month"] = df["day"].str[:4] + "-" + df["day"].str[4:6]
sat = df[(df["month"] >= "2023-01") & (df["month"] <= "2025-06")].copy()
print(f"scenes 2023-01..2025-06: {len(sat)} | eOPL mean overall: {sat['eastern_opl'].mean():.1f}")

# official container-vessel arrivals
ab = pd.read_csv("experiments/data/official/arrivals_br.csv")
ab.columns = [c.strip().lower() for c in ab.columns]
ab["month"] = ab["month"].astype(str).str[:7]
piv = ab.pivot_table(index="month", columns="vessel_type", values="number_of_vessels", aggfunc="sum")
ccol = [c for c in piv.columns if "container" in str(c).lower()]
print("vessel types:", list(piv.columns)[:12])
cont = piv[ccol[0]] if ccol else None

W = {"baseline": ("2023-01", "2024-03"), "event": ("2024-04", "2024-07"), "post": ("2024-08", "2024-12")}
def win(m, w):
    lo, hi = W[w]; return m[(m["month"] >= lo) & (m["month"] <= hi)]

print("\n=== per-scene zone counts by window (mean ± sd, n scenes) ===")
for z in ["eastern_opl", "western_opl", "port_core", "total"]:
    b, e, p = win(sat, "baseline")[z], win(sat, "event")[z], win(sat, "post")[z]
    print(f"{z:12s}: base {b.mean():5.1f}±{b.std():4.1f} (n={len(b)}) | "
          f"event {e.mean():5.1f}±{e.std():4.1f} (n={len(e)}) | post {p.mean():5.1f}±{p.std():4.1f} (n={len(p)})")

print("\n=== event vs baseline (Welch t-test, Cohen's d) ===")
for z in ["eastern_opl", "total"]:
    b, e = win(sat, "baseline")[z].values, win(sat, "event")[z].values
    t, p = stats.ttest_ind(e, b, equal_var=False)
    sp = np.sqrt(((len(b)-1)*b.std(ddof=1)**2 + (len(e)-1)*e.std(ddof=1)**2) / (len(b)+len(e)-2))
    d = (e.mean() - b.mean()) / sp if sp > 0 else np.nan
    print(f"{z:12s}: t={t:+.2f} p={p:.4f} d={d:+.2f} | event/base ratio = {e.mean()/max(b.mean(),1e-9):.2f}x")

# monthly means table
monthly = sat.groupby("month").agg(n_days=("day","nunique"), eopl=("eastern_opl","mean"),
                                   eopl_sd=("eastern_opl","std"), total=("total","mean"),
                                   port=("port_core","mean"), wopl=("western_opl","mean"))
monthly["eopl_ci95"] = 1.96*monthly["eopl_sd"]/np.sqrt(monthly["n_days"].clip(lower=1))
if cont is not None:
    monthly = monthly.join(cont.rename("container_arrivals"))
monthly.round(2).to_csv("experiments/results/congestion_2024.csv")
print("\nsaved congestion_2024.csv | event-month detail:")
ev = monthly.loc["2024-03":"2024-09", ["n_days","eopl","eopl_ci95","total"]]
print(ev.round(1).to_string())
if cont is not None:
    ce = monthly.loc["2024-03":"2024-09","container_arrivals"]
    print("official container-vessel arrivals/month:", ce.round(0).to_dict())

# chart
fig, ax1 = plt.subplots(figsize=(13.5, 6), dpi=110)
ax2 = ax1.twinx()
x = sat["date"]
ax1.scatter(x, sat["eastern_opl"], s=14, c="#74add1", alpha=0.6, label="eOPL ships per scene")
mm = monthly.dropna(subset=["eopl"]); mx = pd.to_datetime(mm.index + "-15")
ax1.errorbar(mx, mm["eopl"], yerr=mm["eopl_ci95"], fmt="o-", color="crimson", capsize=3, lw=2,
             label="monthly mean eOPL ±95% CI")
ev_lo, ev_hi = pd.Timestamp("2024-04-01"), pd.Timestamp("2024-08-01")
ax1.axvspan(ev_lo, ev_hi, color="orange", alpha=0.15, label="congestion window (MPA statements)")
if cont is not None:
    cx = pd.to_datetime(cont.dropna().index + "-15")
    ax2.bar(cx, cont.dropna().values, width=18, color="#cccccc", alpha=0.55,
            label="container-vessel arrivals (official)")
ax1.set_ylabel("ships in eastern OPL (satellite)"); ax2.set_ylabel("container-vessel arrivals")
ax1.set_title("Singapore Strait Observatory — H1-2024 congestion: anchorage presence vs official arrivals")
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m")); plt.setp(ax1.get_xticklabels(), rotation=45)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
fig.tight_layout(); fig.savefig("experiments/results/congestion_2024.png")
print("saved congestion_2024.png")
