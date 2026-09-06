#!/usr/bin/env python3
"""Historical-AIS anchorage analysis (regenerates the numbers cited in paper §4.3).

Source: Mendeley Data, "AIS Data from 11 ports around the globe",
DOI 10.17632/r37vwd493d.1 — Singapore subset (October 2023, ~610K records).

Computes, per zone (eOPL / Port Core / wOPL) and for the full AOI:
  - unique vessels (MMSI) and daily means
  - anchored-unique vessels and anchored-report counts
  - tanker (ship types 80-89) share of anchored reports

Anchored definition: NavigationalStatus == 1 ("At anchor"); a speed<0.5-kn
variant is reported alongside because the status field is sparsely populated
in some feeds. Speed column in this dataset is `speed` (kn).

Output: experiments/results/ais_historical_stats.json (consumed by the paper).
"""
import json
import pandas as pd

SRC = "experiments/data/ais_historical/anon_data/Singapore_anonymized.csv"
OUT = "experiments/results/ais_historical_stats.json"

ZONES = {
    "eastern_opl": (104.00, 1.24, 104.35, 1.40),
    "port_core":   (103.68, 1.20, 104.02, 1.34),
    "western_opl": (103.58, 1.10, 103.78, 1.32),
}
AOI = (103.55, 1.05, 104.40, 1.45)


def in_box(lon, lat, box):
    return (box[0] <= lon) & (lon <= box[2]) & (box[1] <= lat) & (lat <= box[3])


def main():
    df = pd.read_csv(SRC,
                     usecols=lambda c: c.strip() in
                     ["MMSI", "Latitude", "Longitude", "NavigationalStatus",
                      "speed", "ShipType", "Rounded_time"],
                     dtype={"MMSI": "int64"})
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"Latitude": "lat", "Longitude": "lon",
                            "NavigationalStatus": "nav", "speed": "sog",
                            "ShipType": "type", "Rounded_time": "t"})
    print(f"loaded {len(df):,} AIS records")

    anchored_status = df["nav"] == 1
    anchored_speed = df["sog"] < 0.5
    tanker = df["type"].between(80, 89)
    df["t"] = pd.to_datetime(df["t"])
    df["day"] = df["t"].dt.strftime("%Y-%m-%d")

    out = {"source": "Mendeley 10.17632/r37vwd493d.1 (Singapore, Oct 2023)",
           "n_records": int(len(df)), "zones": {}, "definitions": {
               "anchored": "NavigationalStatus == 1",
               "anchored_speed_variant": "SOG < 0.5 kn",
               "tanker": "ShipType in 80..89"}}

    for zone, box in list(ZONES.items()) + [("aoi", AOI)]:
        m = in_box(df["lon"].values, df["lat"].values, box)
        z = df[m]
        a = z[anchored_status[m]]
        a_spd = z[anchored_speed[m]]
        out["zones"][zone] = {
            "unique_vessels": int(z["MMSI"].nunique()),
            "unique_vessels_daily_mean": round(float(z.groupby("day")["MMSI"].nunique().mean()), 1),
            "anchored_unique_status": int(a["MMSI"].nunique()),
            "anchored_unique_daily_mean_status": round(float(a.groupby("day")["MMSI"].nunique().mean()), 1),
            "anchored_reports_status": int(len(a)),
            "anchored_tanker_reports_status": int(tanker[m][anchored_status[m]].sum()),
            "tanker_share_anchored_reports_pct": round(
                100 * tanker[m][anchored_status[m]].sum() / max(len(a), 1), 1),
            "tanker_share_anchored_reports_speed_pct": round(
                100 * tanker[m][anchored_speed[m]].sum() / max(len(a_spd), 1), 1),
            "type80_share_anchored_pct": round(
                100 * (df.loc[m & anchored_status.values, "type"] == 80).sum() / max(len(a), 1), 1),
        }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out["zones"].items()}, indent=2)[:1200])
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
