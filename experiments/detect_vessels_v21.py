#!/usr/bin/env python3
"""Vessel detection v2.1 — recall fix kept, precision restored.

v2 failure (logged): min-filter background too dark -> broad rough-sea/rain texture
cleared the 8 dB anomaly gate; peak-splitting multiplied false peaks (Jan-2026: 11.4k).
v2.1 failure (logged): GLOBAL z-score impossible - min-filter bg makes anomaly systematically
  positive with scene-wide spread; med_a+6*MAD ~ 40-70 dB -> 0 ships; NaN in 202509 poisoned
  medians. v2.2: LOCAL anomaly stats (uniform_filter, win 64), nan-safe load. Gates:
  G1  x > bg + 8 dB          (compact bright target over dark-water background)
  G2  x > mu_a + 4.5*sig_a   (local anomaly z-score; adapts to texture/rough patches)
  G3  x > -8 dB              (large-vessel brightness floor)
  G4  component mean anomaly >= 6 dB (reject broad uplift/weather blobs)
  G5  peaks = local maxima (sep ~3 px) per component -> per-ship counts (queue fix)
Outputs: detections_v21.geojson, monthly_counts_v21.csv
"""
import os, glob, csv, json
import numpy as np
import rasterio
from scipy import ndimage

DATA = sorted(glob.glob("experiments/data/s1_vv_*.tif"))
OUT = "experiments/results"
ZONES = {"port_core": (103.68, 1.20, 104.02, 1.34),
         "eastern_opl": (104.00, 1.08, 104.30, 1.24),
         "western_opl": (103.58, 1.10, 103.78, 1.32)}
BG_BRIGHT = 8.0; Z = 4.5; FLOOR = -8.0; MEAN_ANOM = 6.0; MINP = 4; LAND_MED_DB = -12.0; WIN = 64

def zone_of(lon, lat):
    for z, (w, s_, e, n_) in ZONES.items():
        if w <= lon <= e and s_ <= lat <= n_: return z
    return "strait_other"

def main():
    imgs, transform = [], None
    for p in DATA:
        with rasterio.open(p) as src:
            a = np.nan_to_num(src.read(1).astype(np.float32), nan=0.0); transform = transform or src.transform
        imgs.append(10.0 * np.log10(np.clip(a, 1e-6, None)))
    stack = np.stack(imgs); dates = [os.path.basename(p)[6:12] for p in DATA]
    med = np.median(stack, axis=0)
    land = ndimage.binary_dilation(med > LAND_MED_DB, iterations=6); sea = ~land

    feats, rows = [], []
    for a_db, date in zip(stack, dates):
        x0 = np.where(sea, a_db, -40.0)
        bg = ndimage.uniform_filter(ndimage.minimum_filter(x0, 96), 193)
        anom = a_db - bg
        anom_f = np.where(sea, anom, 0.0)
        valid = sea.astype(np.float32)
        mu_a = ndimage.uniform_filter(anom_f, WIN) / np.maximum(ndimage.uniform_filter(valid, WIN), 1e-6)
        a2 = np.where(sea, anom_f * anom_f, 0.0)
        var_a = ndimage.uniform_filter(a2, WIN) / np.maximum(ndimage.uniform_filter(valid, WIN), 1e-6) - mu_a * mu_a
        sig_a = np.sqrt(np.clip(var_a, 0.0, 400.0))
        thr = np.maximum(np.maximum(bg + BG_BRIGHT, mu_a + Z * sig_a), FLOOR)
        cand = sea & (a_db > thr)
        lab, nl = ndimage.label(cand)
        count = 0
        if nl:
            lmax = ndimage.maximum_filter(a_db, size=9)
            for i, sl in enumerate(ndimage.find_objects(lab), start=1):
                comp = (lab[sl] == i)
                if comp.sum() < MINP: continue
                if float((anom[sl][comp]).mean()) < MEAN_ANOM: continue  # broad blob
                sub = np.where(comp, a_db[sl], -99.0)
                peaks = comp & (sub >= lmax[sl]) & (sub > -20)
                ys, xs = np.nonzero(peaks)
                if len(ys) == 0:
                    cy, cx = ndimage.center_of_mass(comp); ys, xs = np.array([cy]), np.array([cx])
                for y, x in zip(ys, xs):
                    lon, lat = rasterio.transform.xy(transform, y + sl[0].start, x + sl[1].start)
                    feats.append({"type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                        "properties": {"date": date, "npix": int(comp.sum()),
                                       "peak_db": round(float(sub.max()), 1), "zone": zone_of(lon, lat)}})
                    count += 1
        df = [f for f in feats if f["properties"]["date"] == date]
        zc = {z: sum(1 for f in df if f["properties"]["zone"] == z) for z in list(ZONES)}
        other = count - sum(zc.values())
        rows.append([date, count, zc["port_core"], zc["eastern_opl"], zc["western_opl"], other])
        print(f"{date}: {count:4d} ships | port {zc['port_core']}, eOPL {zc['eastern_opl']}, wOPL {zc['western_opl']}, other {other}")

    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{OUT}/detections_v21.geojson", "w"))
    with open(f"{OUT}/monthly_counts_v21.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["month","total","port_core","eastern_opl","western_opl","other"]); w.writerows(rows)
    print(f"\nwrote {OUT}/detections_v21.geojson ({len(feats)} ships), monthly_counts_v21.csv")

if __name__ == "__main__":
    main()
