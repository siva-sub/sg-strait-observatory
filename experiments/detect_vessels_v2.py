#!/usr/bin/env python3
"""Vessel detection v2 — fixes from glm-5.3-flash vision QA (2026-09-04).

v0 issues (QA verdict ACCEPT-WITH-FIXES):
  M1: dense anchored queues merged into single >MAXP components -> whole queue dropped
      (Sept eastern_opl: >=10 ships, 3 detections).
  M2: moving ships smear (azimuth comets) -> elongated components > cap -> dropped.
  F1: subswath radiometric seam inflates zone counts (Jan 2026 spike suspect).
  F2: kelong/aquaculture rafts near coasts possible false positives.

v2 changes:
  - Background-normalized anomaly: a = x_db - bg, bg = uniform_filter(min_filter(x,96),193)
    -> seam/wind robust; no self-masking of isolated ships.
  - Peak-splitting: count local maxima within each component -> dense queues and
    comets yield per-ship counts instead of one oversized blob.
  - MINP 4 px (~150 m at 37 m/px) to cut small rafts; no MAXP cap (split instead).
  - Kept: median-composite land mask (QA1 PASS), zone rectangles (still approximations).

Outputs: experiments/results/detections_v2.geojson, monthly_counts_v2.csv.
"""
import os, glob, csv, json
import numpy as np
import rasterio
from scipy import ndimage

DATA = sorted(glob.glob("experiments/data/s1_vv_*.tif"))
OUT = "experiments/results"

ZONES = {
    "port_core":   (103.68, 1.20, 104.02, 1.34),
    "eastern_opl": (104.00, 1.08, 104.30, 1.24),
    "western_opl": (103.58, 1.10, 103.78, 1.32),
}
ANOM_DB = 8.0     # anomaly threshold above local background
FLOOR_DB = -13.0  # absolute floor (bright enough to be a large vessel)
MINP = 4          # min component px (~150 m)
LAND_MED_DB = -12.0

def zone_of(lon, lat):
    for z, (w, s_, e, n_) in ZONES.items():
        if w <= lon <= e and s_ <= lat <= n_:
            return z
    return "strait_other"

def main():
    imgs, transform = [], None
    for p in DATA:
        with rasterio.open(p) as src:
            a = src.read(1).astype(np.float32)
            transform = transform or src.transform
        imgs.append(10.0 * np.log10(np.clip(a, 1e-6, None)))
    stack = np.stack(imgs)
    dates = [os.path.basename(p)[6:12] for p in DATA]

    med = np.median(stack, axis=0)
    land = ndimage.binary_dilation(med > LAND_MED_DB, iterations=6)
    sea = ~land
    print(f"land/static mask: {land.mean()*100:.1f}% | rasters: {len(dates)}")

    feats, rows = [], []
    for a_db, date in zip(stack, dates):
        x0 = np.where(sea, a_db, -40.0)
        bg = ndimage.uniform_filter(ndimage.minimum_filter(x0, 96), 193)
        anom = a_db - bg
        cand = sea & (anom > ANOM_DB) & (a_db > FLOOR_DB)
        lab, nl = ndimage.label(cand)
        count = merged = 0
        if nl:
            objs = ndimage.find_objects(lab)
            lmax = ndimage.maximum_filter(a_db, size=7)
            for i, sl in enumerate(objs, start=1):
                comp = (lab[sl] == i)
                npix = int(comp.sum())
                if npix < MINP:
                    continue
                sub = np.where(comp, a_db[sl], -99.0)
                peaks = (sub >= lmax[sl]) & comp & (sub > -20)
                k = max(1, int(peaks.sum()))
                if npix > 400:
                    merged += 1
                ys, xs = np.nonzero(peaks if k > 1 else comp)
                if k == 1:  # single ship: component centroid
                    cy, cx = ndimage.center_of_mass(comp)
                    ys, xs = np.array([cy]), np.array([cx])
                for y, x in zip(ys, xs):
                    lon, lat = rasterio.transform.xy(transform, y + sl[0].start, x + sl[1].start)
                    feats.append({"type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                        "properties": {"date": date, "npix": npix, "ships_in_comp": k,
                                       "peak_db": round(float(sub.max()), 1),
                                       "zone": zone_of(lon, lat)}})
                count += k
        zc = {z: sum(1 for f in feats if f["properties"]["date"] == date
                     and f["properties"]["zone"] == z and f["properties"]["ships_in_comp"] >= 0)
              for z in list(ZONES)}
        # recount cleanly per date/zone from feats of this date
        df = [f for f in feats if f["properties"]["date"] == date]
        zc = {z: sum(1 for f in df if f["properties"]["zone"] == z) for z in list(ZONES) + ["strait_other"]}
        rows.append([date, count, zc["port_core"], zc["eastern_opl"], zc["western_opl"], zc["strait_other"]])
        print(f"{date}: {count:4d} ships ({merged} big/merged comps) | port {zc['port_core']}, eOPL {zc['eastern_opl']}, wOPL {zc['western_opl']}, other {zc['strait_other']}")

    json.dump({"type": "FeatureCollection", "features": feats},
              open(f"{OUT}/detections_v2.geojson", "w"))
    with open(f"{OUT}/monthly_counts_v2.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "total", "port_core", "eastern_opl", "western_opl", "other"])
        w.writerows(rows)
    print(f"\nwrote {OUT}/detections_v2.geojson ({len(feats)} ship-features), {OUT}/monthly_counts_v2.csv")

if __name__ == "__main__":
    main()
