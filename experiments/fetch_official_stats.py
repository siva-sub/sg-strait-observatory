#!/usr/bin/env python3
"""Fetch official monthly series from data.gov.sg (CKAN) for the econ join.

Datasets (IDs verified in deep-research dossier §5):
  container : Container Throughput, Monthly (TEU)          d_da030f7028200d19ffcbe4a2d71af39c
  arrivals  : Vessel Arrivals (>75 GT) Total, Monthly      d_d48c5a038904f6da3c603cd854b6c191
  arrivals_br : Vessel Arrivals (>75 GT) Breakdown, Monthly d_8f264219109e61fffa87ac64dd5a9a65
  bunker    : Bunker Sales Breakdown, Monthly (tonnes)     d_4f5abbf4486bf8e52bbed3be56dde562
  trade     : Merchandise Trade Monthly, SA (SingStat)     d_c41b1f16d0847996b1dcfd2ded0b2d91

Strategy per dataset: package_show -> newest CSV resource -> download.
Fallback: treat dataset id as datastore resource_id -> datastore_search dump.
"""
import os, json, requests

DS = {
    "container":    "d_da030f7028200d19ffcbe4a2d71af39c",
    "arrivals":     "d_d48c5a038904f6da3c603cd854b6c191",
    "arrivals_br":  "d_8f264219109e61fffa87ac64dd5a9a65",
    "bunker":       "d_4f5abbf4486bf8e52bbed3be56dde562",
    "trade":        "d_c41b1f16d0847996b1dcfd2ded0b2d91",
}
OUT = "experiments/data/official"
os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "sg-strait-observatory/0.1"

def package_csv(id_):
    r = S.get("https://data.gov.sg/api/action/package_show", params={"id": id_}, timeout=60)
    r.raise_for_status()
    res = r.json()["result"]["resources"]
    csvs = [x for x in res if (x.get("format") or "").upper() == "CSV"
            or (x.get("url") or "").lower().endswith(".csv")]
    if not csvs:
        return None, res
    csvs.sort(key=lambda x: x.get("last_modified") or x.get("created") or "", reverse=True)
    return csvs[0], res

def datastore_dump(id_):
    rows, offset = [], 0
    while True:
        r = S.get("https://data.gov.sg/api/action/datastore_search",
                  params={"resource_id": id_, "limit": 32000, "offset": offset}, timeout=60)
        if r.status_code != 200: return None
        j = r.json()["result"]; rows += j["records"]
        if len(rows) >= j.get("total", 0) or not j["records"]: break
        offset += len(j["records"])
    return rows

for key, id_ in DS.items():
    path = f"{OUT}/{key}.csv"
    try:
        rec, res = package_csv(id_)
        if rec:
            url = rec.get("download_url") or rec.get("url")
            d = S.get(url, timeout=120)
            if d.status_code == 200 and len(d.content) > 200:
                open(path, "wb").write(d.content)
                print(f"{key}: OK via package CSV ({len(d.content)/1e3:.0f} KB) <- {rec.get('name','?')[:60]}")
                continue
            print(f"{key}: CSV download failed {d.status_code}")
        else:
            print(f"{key}: no CSV resource among {[x.get('format') for x in res]}")
    except Exception as e:
        print(f"{key}: package_show failed: {e}")
    # fallback
    try:
        rows = datastore_dump(id_)
        if rows:
            cols = list(rows[0].keys())
            import csv as _csv
            with open(path, "w", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
            print(f"{key}: OK via datastore ({len(rows)} rows)")
            continue
    except Exception as e:
        print(f"{key}: datastore fallback failed: {e}")
    print(f"{key}: FAILED")

# print headers for parser calibration
import glob
for p in sorted(glob.glob(f"{OUT}/*.csv")):
    try:
        head = open(p).readline().strip()
        print(f"-- {os.path.basename(p)}: {head[:200]}")
    except Exception as e:
        print(f"-- {p}: unreadable {e}")
