#!/usr/bin/env python3
"""Vessel detection v3 — final v0-style CFAR with the two QA-driven fixes.

Debugged history (see CHANGELOG):
  v0 : local mu/sigma CFAR OK; bug = MAXP=600 dropped merged queues/comets (vision-QA miss).
  v2 : min-filter bg poisoned by -40 land fill (bg≈-40) -> everything 'anomalous' -> explosion. INVALID.
  v2.1/v2.2: anomaly z-scoring math broken by same fill -> 0 ships.
  v3 : v0 detector (local sea-only mu+K*sigma, properly normalized) + peak-splitting for
       large/merged components (dense anchored queues, azimuth-smeared comets), no size cap.

Land/static mask: temporal-median > -12 dB (QA1 PASS; also suppresses kelong/aquaculture
static scatterers as intended). Zone rectangles remain APPROXIMATE.
Outputs: detections_v3.geojson, monthly_counts_v3.csv
"""
import os, glob, csv, json
import numpy as np
import rasterio
from scipy import ndimage

DATA = sorted(glob.glob("experiments/data/s1_vv_*.tif"))
OUT = "experiments/results"
ZONES = {"port_core": (103.68, 1.20, 104.02, 1.34),
         "eastern_opl": (104.00, 1.24, 104.35, 1.40),  # synced 2026-09-06: old box (1.08-1.24N) sat on Batam
         "western_opl": (103.58, 1.10, 103.78, 1.32)}
K = 5.5; WIN = 64; MINP = 3; FLOOR_DB = -12.0; LAND_MED_DB = -12.0

def zone_of(lon, lat):
    for z, (w, s_, e, n_) in ZONES.items():
        if w <= lon <= e and s_ <= lat <= n_: return z
    return "strait_other"

def main():
    imgs, transform = [], None
    for p in DATA:
        with rasterio.open(p) as src:
            a = np.nan_to_num(src.read(1).astype(np.float32), nan=0.0)
            transform = transform or src.transform
        imgs.append(10.0 * np.log10(np.clip(a, 1e-6, None)))
    stack = np.stack(imgs); dates = [os.path.basename(p)[6:12] for p in DATA]
    med = np.median(stack, axis=0)
    land = ndimage.binary_dilation(med > LAND_MED_DB, iterations=6); sea = ~land
    print(f"land/static mask: {land.mean()*100:.1f}% | rasters: {len(dates)}")

    feats, rows = [], []
    for a_db, date in zip(stack, dates):
        gsea = float(np.median(a_db[sea]))          # neutral fill: global sea median
        x = np.where(sea, a_db, gsea)
        x2 = np.where(sea, a_db * a_db, gsea * gsea)
        mu = ndimage.uniform_filter(x, WIN)
        var = ndimage.uniform_filter(x2, WIN) - mu * mu
        sig = np.sqrt(np.clip(var, 0.0, 400.0))
        thr = np.maximum(mu + K * sig, FLOOR_DB)
        cand = sea & (a_db > thr)
        lab, nl = ndimage.label(cand)
        count = split = 0
        if nl:
            lmax = ndimage.maximum_filter(a_db, size=7)
            for i, sl in enumerate(ndimage.find_objects(lab), start=1):
                comp = (lab[sl] == i)
                npix = int(comp.sum())
                if npix < MINP: continue
                sub = np.where(comp, a_db[sl], -99.0)
                if npix > 25:  # merged queue / smeared comet: count peaks = ships
                    peaks = comp & (sub >= lmax[sl])
                    ys, xs = np.nonzero(peaks)
                    if len(ys) == 0:
                        cy, cx = ndimage.center_of_mass(comp); ys, xs = np.array([cy]), np.array([cx])
                    split += 1
                else:
                    cy, cx = ndimage.center_of_mass(comp); ys, xs = np.array([cy]), np.array([cx])
                for y, x_ in zip(ys, xs):
                    lon, lat = rasterio.transform.xy(transform, y + sl[0].start, x_ + sl[1].start)
                    feats.append({"type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                        "properties": {"date": date, "npix": npix, "peak_db": round(float(sub.max()), 1),
                                       "zone": zone_of(lon, lat)}})
                    count += 1
        df = [f for f in feats if f["properties"]["date"] == date]
        zc = {z: sum(1 for f in df if f["properties"]["zone"] == z) for z in list(ZONES)}
        other = count - sum(zc.values())
        rows.append([date, count, zc["port_core"], zc["eastern_opl"], zc["western_opl"], other])
        print(f"{date}: {count:4d} ships ({split} split comps) | port {zc['port_core']}, eOPL {zc['eastern_opl']}, wOPL {zc['western_opl']}, other {other}")

    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{OUT}/detections_v3.geojson", "w"))
    with open(f"{OUT}/monthly_counts_v3.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["month","total","port_core","eastern_opl","western_opl","other"]); w.writerows(rows)
    print(f"\nwrote {OUT}/detections_v3.geojson ({len(feats)} ships), monthly_counts_v3.csv")

if __name__ == "__main__":
    main()
