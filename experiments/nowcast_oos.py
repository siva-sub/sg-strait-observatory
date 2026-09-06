#!/usr/bin/env python3
"""Out-of-sample nowcast test: satellite eOPL presence vs persistence (paper §4.6).

Question: does a satellite-based regression of monthly bunker sales on eOPL
anchorage presence beat a naive persistence baseline out of sample?

Design (matches autoresearch iteration 13):
  - target: monthly bunker sales, z-scored on the training window
  - predictor: eOPL presence (ships/scene), z-scored on the training window
  - train: 2021-09 .. 2023-01 (n=17); test: 2024-01 .. 2026-03 (n=27)
  - models: (a) persistence  y_hat_t = y_{t-1}
            (b) satellite    y_hat_t = a + b * x_t   (OLS on train)
            (c) combined     persistence + satellite (OLS on train)
  - metric: RMSE on the test window (z-units); skill = 1 - RMSE/RMSE_persist

Output: experiments/results/nowcast_oos.json
"""
import json
import numpy as np
import pandas as pd
from scipy import stats

JOIN = "experiments/results/perscene_join.csv"
OUT = "experiments/results/nowcast_oos.json"
TRAIN = ("2021-09", "2023-01")
TEST = ("2024-01", "2026-03")


def main():
    m = pd.read_csv(JOIN, index_col=0).dropna(subset=["eopl", "bunker"])
    m.index = pd.to_datetime(m.index)
    m = m.sort_index()

    train = m.loc[TRAIN[0]:TRAIN[1]]
    test = m.loc[TEST[0]:TEST[1]]
    mu, sd = train["bunker"].mean(), train["bunker"].std(ddof=1)
    xm, xsd = train["eopl"].mean(), train["eopl"].std(ddof=1)

    def z_b(s): return (s - mu) / sd
    def z_e(s): return (s - xm) / xsd

    y_tr, x_tr = z_b(train["bunker"]).values, z_e(train["eopl"]).values
    y_te, x_te = z_b(test["bunker"]).values, z_e(test["eopl"]).values
    y_lag_te = z_b(test["bunker"].shift(1)).values  # persistence input

    # (a) persistence
    pred_persist = y_lag_te[1:]
    actual = y_te[1:]
    rmse_persist = float(np.sqrt(np.mean((pred_persist - actual) ** 2)))

    # (b) satellite-only OLS
    b1, b0 = np.polyfit(x_tr, y_tr, 1)
    pred_sat = b0 + b1 * x_te
    rmse_sat = float(np.sqrt(np.mean((pred_sat - y_te) ** 2)))

    # (c) combined: lag + satellite (first test point dropped: lag undefined)
    y_tr_lag = z_b(train["bunker"].shift(1)).values
    X = np.column_stack([np.ones(len(x_tr) - 1), y_tr_lag[1:], x_tr[1:]])
    beta, *_ = np.linalg.lstsq(X, y_tr[1:], rcond=None)
    y_lag_te_ok = y_lag_te[1:]
    x_te_ok = x_te[1:]
    X_te = np.column_stack([np.ones(len(x_te_ok)), y_lag_te_ok, x_te_ok])
    pred_comb = X_te @ beta
    rmse_comb = float(np.sqrt(np.mean((pred_comb - actual) ** 2)))

    r_oos, p_oos = stats.pearsonr(pred_sat, y_te)
    out = {
        "train_window": list(TRAIN), "n_train": int(len(train)),
        "test_window": list(TEST), "n_test": int(len(test)),
        "target": "bunker sales, z-scored on train",
        "rmse_persistence": round(rmse_persist, 3),
        "rmse_satellite_ols": round(rmse_sat, 3),
        "rmse_combined": round(rmse_comb, 3),
        "skill_satellite_vs_persistence": round(1 - rmse_sat / rmse_persist, 3),
        "skill_combined_vs_persistence": round(1 - rmse_comb / rmse_persist, 3),
        "oos_r_satellite": round(float(r_oos), 3),
        "oos_p_satellite": round(float(p_oos), 3),
        "direction_share_satellite": round(
            float(np.mean(np.sign(np.diff(pred_sat)) == np.sign(np.diff(y_te)))), 3),
        "direction_share_persistence": round(
            float(np.mean(np.sign(np.diff(pred_persist)) == np.sign(np.diff(actual)))), 3),
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
