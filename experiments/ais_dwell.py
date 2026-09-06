#!/usr/bin/env python3
"""Per-vessel anchorage dwell times (paper §4.3; regenerates ais_dwell_times.csv).

Method: for each vessel in each zone (anchored reports only,
NavigationalStatus == 1), reports are split into separate dwell events whenever
the gap between consecutive reports exceeds GAP_H hours (the vessel left the
zone or stopped reporting); each event's dwell = first-to-last report in hours.

Source: Mendeley 10.17632/r37vwd493d.1, Singapore subset (Oct 2023).

Output: experiments/results/ais_dwell_times.csv  (one row per dwell event)
        experiments/results/ais_monthly_dwell.csv (summary per zone)
"""
import pandas as pd

SRC = "experiments/data/ais_historical/anon_data/Singapore_anonymized.csv"
OUT = "experiments/results/ais_dwell_times.csv"
OUT_SUM = "experiments/results/ais_monthly_dwell.csv"
GAP_H = 24.0

ZONES = {
    "eastern_opl": (104.00, 1.24, 104.35, 1.40),
    "port_core":   (103.68, 1.20, 104.02, 1.34),
    "western_opl": (103.58, 1.10, 103.78, 1.32),
}


def main():
    df = pd.read_csv(SRC,
                     usecols=lambda c: c.strip() in
                     ["MMSI", "Latitude", "Longitude", "NavigationalStatus",
                      "ShipType", "Rounded_time"],
                     dtype={"MMSI": "int64"})
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"Latitude": "lat", "Longitude": "lon",
                            "NavigationalStatus": "nav",
                            "ShipType": "type", "Rounded_time": "t"})
    df["t"] = pd.to_datetime(df["t"])

    def zone_of(lon, lat):
        for z, (w, s_, e, n_) in ZONES.items():
            if w <= lon <= e and s_ <= lat <= n_:
                return z
        return None

    anc = df[df["nav"] == 1].copy()
    anc["zone"] = [zone_of(lo, la) for lo, la in zip(anc["lon"], anc["lat"])]
    anc = anc.dropna(subset=["zone"])
    anc = anc.rename(columns={"MMSI": "mmsi"}).sort_values(["mmsi", "zone", "t"])

    # split into dwell events at reporting gaps > GAP_H hours
    gap_h = anc.groupby(["mmsi", "zone"])["t"].diff().dt.total_seconds() / 3600
    new_event = (gap_h.isna()) | (gap_h > GAP_H)
    anc["event_id"] = new_event.cumsum()

    events = (anc.groupby(["mmsi", "zone", "event_id"])
                 .agg(start=("t", "min"), end=("t", "max"),
                      ship_type=("type", "first"))
                 .reset_index())
    events["dwell_hours"] = (events["end"] - events["start"]).dt.total_seconds() / 3600
    events["month"] = events["start"].dt.strftime("%Y-%m")
    events = events[["mmsi", "zone", "start", "dwell_hours", "ship_type", "month"]]
    events.to_csv(OUT, index=False)
    print(f"{len(events)} dwell events → {OUT}")

    # summary (all vessels + tankers)
    rows = []
    for zone, g in events.groupby("zone"):
        t = g[g["ship_type"].between(80, 89)]
        rows.append({
            "zone": zone,
            "events": len(g), "unique_vessels": g["mmsi"].nunique(),
            "median_dwell_h": round(g["dwell_hours"].median(), 1),
            "p25_h": round(g["dwell_hours"].quantile(.25), 1),
            "p75_h": round(g["dwell_hours"].quantile(.75), 1),
            "total_vessel_hours": round(g["dwell_hours"].sum(), 0),
            "tanker_events": len(t), "tanker_unique": t["mmsi"].nunique(),
            "tanker_median_dwell_h": round(t["dwell_hours"].median(), 1),
            "tanker_p25_h": round(t["dwell_hours"].quantile(.25), 1),
            "tanker_p75_h": round(t["dwell_hours"].quantile(.75), 1),
            "tanker_hours": round(t["dwell_hours"].sum(), 0),
            "tanker_events_gt12h": int((t["dwell_hours"] > 12).sum()),
            "tanker_events_gt24h": int((t["dwell_hours"] > 24).sum()),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_SUM, index=False)
    print(summary.to_string(index=False))
    print(f"summary → {OUT_SUM}")


if __name__ == "__main__":
    main()
