#!/usr/bin/env python3
"""Robustness battery for the eOPL-bunker correlation (paper §4.5, Table 9).

Computes, from experiments/results/perscene_join.csv:
  - rolling Pearson correlation over 24-observation windows (not calendar months)
  - count of windows below the two-sided 5% critical r at n=24 (0.4044)
  - COVID-period exclusion sensitivity
  - log-difference correlation
  - full-sample Pearson/Spearman for reference

Output: experiments/results/robustness_summary.json
"""
import json
import numpy as np
import pandas as pd
from scipy import stats

JOIN = "experiments/results/perscene_join.csv"
OUT = "experiments/results/robustness_summary.json"
W = 24  # observations per window


def main():
    m = pd.read_csv(JOIN, index_col=0).dropna(subset=["eopl", "bunker"]).sort_index()

    r, p = stats.pearsonr(m["eopl"], m["bunker"])
    rho, rp = stats.spearmanr(m["eopl"], m["bunker"])

    # rolling windows
    centers, rs = [], []
    for i in range(len(m) - W + 1):
        w = m.iloc[i:i + W]
        centers.append(w.index[W // 2])
        rs.append(stats.pearsonr(w["eopl"], w["bunker"])[0])
    rs = np.array(rs)
    t_crit = stats.t.ppf(0.975, W - 2)
    r_crit = t_crit / np.sqrt(t_crit**2 + W - 2)

    # COVID exclusion (2020-02..2021-12 loosely covers the disruption)
    no_covid = m.loc[~m.index.str[:4].isin(["2020", "2021"])]
    r_nc = stats.pearsonr(no_covid["eopl"], no_covid["bunker"])[0]

    # log-diff
    lg = np.log(m[["eopl", "bunker"]].astype(float)).diff().dropna()
    r_ld = stats.pearsonr(lg["eopl"], lg["bunker"])[0]

    out = {
        "n_months": int(len(m)),
        "pearson_r": round(float(r), 4), "pearson_p": float(p),
        "spearman_rho": round(float(rho), 4),
        "r_squared_full_sample": round(float(r) ** 2, 4),
        "rolling": {
            "window_observations": W,
            "n_windows": int(len(rs)),
            "min": round(float(rs.min()), 4),
            "max": round(float(rs.max()), 4),
            "median": round(float(np.median(rs)), 4),
            "negative_windows": int((rs < 0).sum()),
            "critical_r_5pct": round(float(r_crit), 4),
            "windows_below_critical": int((rs < r_crit).sum()),
            "latest_window_r": round(float(rs[-1]), 4),
            "centers_first_last": [centers[0], centers[-1]],
        },
        "covid_exclusion": {"dropped": "2020, 2021", "n": int(len(no_covid)),
                            "pearson_r": round(float(r_nc), 4)},
        "log_diff": {"n": int(len(lg)), "pearson_r": round(float(r_ld), 4)},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
