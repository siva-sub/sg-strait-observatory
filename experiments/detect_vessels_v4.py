#!/usr/bin/env python3
"""Vessel detection v4 — trimmed CFAR (literature-guided optimization, 2026-09-05).

Paper-driven change (SAR ATR 50-yr survey arXiv 2509.22159; Iervolino & Guida 2017;
Ai et al. 2021 BTS-CFAR; El-Darymli et al. 2013):
  PROBLEM: uniform_filter mean/sigma includes bright ship pixels in the window ->
    ships raise the local threshold, suppressing neighboring detections
    (exactly the anchored-queue miss from vision QA).
  FIX: two-pass trimmed CFAR:
    Pass 1: provisional global threshold from robust stats (median + K * MAD)
    Pass 2: compute local mu/sigma from sea-only pixels (below provisional threshold)
    -> ship pixels are censored from background estimate (equivalent to TM-CFAR
       with the censoring depth set by the data, not a fixed percentage)

Also: removes the absolute floor (-12 dB) and uses purely adaptive threshold
(literature standard; floor may clip dim vessels in rough seas).

Outputs: detections_v4.geojson, monthly_counts_v4.csv
"""
import os, glob, csv, json
import numpy as np
import rasterio
from scipy import ndimage

DATA = sorted(glob.glob("experiments/data/s1_vv_*.tif"))
OUT = "experiments/results"
ZONES = {"port_core": (103.68, 1.20, 104.02, 1.34),
         "eastern_opl": (104.00, 1.24, 104.35, 1.40),
         "western_opl": (103.58, 1.10, 103.78, 1.32)}
K = 5.5; WIN = 64; MINP = 3; SPLIT = 25; LAND_MED_DB = -12.0

def zone_of(lon, lat):
    for z, (w, s_, e, n_) in ZONES.items():
        if w <= lon <= e and s_ <= lat <= n_: return z
    return "strait_other"

def trimmed_cfar(a_db, sea):
    """Two-pass CFAR: provisional threshold censors ships from background."""
    # Pass 1: global robust stats on sea
    sea_vals = a_db[sea & (a_db > -30)]
    if len(sea_vals) < 100: return None
    med = float(np.median(sea_vals))
    mad = float(np.median(np.abs(sea_vals - med))) * 1.4826
    prov_thr = med + K * mad
    # Pass 2: sea-only pixels (censored: above provisional threshold)
    sea_bg = sea & (a_db > -30) & (a_db < prov_thr)
    bg_fill = med  # neutral fill for non-background pixels
    x = np.where(sea_bg, a_db, bg_fill)
    x2 = np.where(sea_bg, a_db * a_db, bg_fill * bg_fill)
    valid = sea_bg.astype(np.float32)
    vf = np.maximum(ndimage.uniform_filter(valid, WIN), 1e-6)
    mu = ndimage.uniform_filter(x, WIN) / vf
    var = ndimage.uniform_filter(x2, WIN) / vf - mu * mu
    sig = np.sqrt(np.clip(var, 0.0, 400.0))
    thr = mu + K * sig
    return thr, prov_thr

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
    print(f"land mask: {land.mean()*100:.0f}% | rasters: {len(dates)}")

    feats, rows = [], []
    for a_db, date in zip(stack, dates):
        result = trimmed_cfar(a_db, sea)
        if result is None:
            rows.append([date, 0, 0, 0, 0, 0]); continue
        thr, prov = result
        cand = sea & (a_db > thr)
        lab, nl = ndimage.label(cand)
        count = split = 0
        if nl:
            lmax = ndimage.maximum_filter(a_db, size=7)
            for i, sl in enumerate(ndimage.find_objects(lab), start=1):
                comp = (lab[sl] == i); npix = int(comp.sum())
                if npix < MINP: continue
                sub = np.where(comp, a_db[sl], -99.0)
                if npix > SPLIT:
                    peaks = comp & (sub >= lmax[sl])
                    ys, xs = np.nonzero(peaks)
                    if len(ys) == 0:
                        cy, cx = ndimage.center_of_mass(comp)
                        ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])
                    split += 1
                else:
                    cy, cx = ndimage.center_of_mass(comp)
                    ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])
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
        print(f"{date}: {count:4d} ships ({split} split) prov_thr={prov:.1f} | port {zc['port_core']}, eOPL {zc['eastern_opl']}, wOPL {zc['western_opl']}, other {other}")

    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{OUT}/detections_v4.geojson", "w"))
    with open(f"{OUT}/monthly_counts_v4.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["month","total","port_core","eastern_opl","western_opl","other"]); w.writerows(rows)
    print(f"\nwrote {OUT}/detections_v4.geojson ({len(feats)}), monthly_counts_v4.csv")

if __name__ == "__main__":
    main()
