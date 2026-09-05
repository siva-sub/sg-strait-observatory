#!/usr/bin/env python3
"""Vessel detection v0 for Singapore Strait S1 monthly composites.

Pipeline:
 1. Load all monthly VV gamma0 TIFFs (FLOAT32, common grid).
 2. Land mask = pixels whose MEDIAN dB across dates is high (land is static, ships move).
 3. Per date: CA-CFAR in dB domain on sea pixels (local mean+sigma, window ~1.6 km),
    guard by absolute floor; connected components; size filter -> vessel candidates.
 4. Outputs: detections_all.geojson, monthly_counts.csv, diagnostics.

Anchorage zones are APPROXIMATE rectangles pending official port-limit polygons
(dossier open question #2). This is detection v0: CFAR only, no ML, no AIS.
"""
import os, glob, csv, json
import numpy as np
import rasterio
from scipy import ndimage

DATA = sorted(glob.glob("experiments/data/s1_vv_*.tif"))
OUT = "experiments/results"
os.makedirs(OUT, exist_ok=True)

# approx zones (lon_min, lat_min, lon_max, lat_max) -- DOCUMENTED APPROXIMATIONS
ZONES = {
    "port_core":  (103.68, 1.20, 104.02, 1.34),
    "eastern_opl": (104.00, 1.08, 104.30, 1.24),
    "western_opl": (103.58, 1.10, 103.78, 1.32),
}

K = 5.5          # CFAR multiplier
WIN = 64         # window px (~1.6 km at 25 m)
MINP, MAXP = 3, 600   # component size bounds (px)
FLOOR_DB = -10.0 # absolute ship plausibility floor
LAND_MED_DB = -12.0   # median-above-this => land/static

def main():
    assert DATA, "no tifs found; run fetch_s1_monthly.py first"
    imgs, transform = [], None
    for p in DATA:
        with rasterio.open(p) as src:
            a = src.read(1).astype(np.float32)
            transform = transform or src.transform
        a_db = 10.0 * np.log10(np.clip(a, 1e-6, None))
        imgs.append(a_db)
    stack = np.stack(imgs)  # (n, h, w) float32
    dates = [os.path.basename(p)[6:12] for p in DATA]
    print(f"loaded {len(dates)} rasters {stack.shape[1:]}")

    # ---- land mask from temporal median ----
    med = np.median(stack, axis=0)
    land = med > LAND_MED_DB
    land = ndimage.binary_dilation(land, iterations=6)
    print(f"land/static mask: {land.mean()*100:.1f}% of AOI")

    sea = ~land
    feats, rows = [], []
    for a_db, date in zip(stack, dates):
        x = np.where(sea, a_db, np.nan)
        x0 = np.where(sea, a_db, -40.0)  # fill for filtering
        valid = sea.astype(np.float32)
        s1 = ndimage.uniform_filter(x0, WIN)
        n = ndimage.uniform_filter(valid, WIN)
        mu = s1 / np.maximum(n, 1e-6)
        x2 = np.where(sea, a_db * a_db, 0.0)
        var = ndimage.uniform_filter(x2, WIN) / np.maximum(n, 1e-6) - mu * mu
        sig = np.sqrt(np.clip(var, 0.0, 400.0))
        thr = np.maximum(mu + K * sig, FLOOR_DB)
        cand = sea & (a_db > thr)
        lab, nl = ndimage.label(cand)
        if nl == 0:
            rows.append([date, 0, 0, 0, 0]); continue
        objs = ndimage.find_objects(lab)
        count = 0
        for i, sl in enumerate(objs, start=1):
            npix = int((lab[sl] == i).sum())
            if not (MINP <= npix <= MAXP):
                continue
            cy, cx = ndimage.center_of_mass(lab[sl] == i)
            r, c = sl[0].start + cy, sl[1].start + cx
            lon, lat = rasterio.transform.xy(transform, r, c)
            zone = next((z for z, (w, s_, e, n_) in ZONES.items()
                         if w <= lon <= e and s_ <= lat <= n_), "strait_other")
            feats.append({"type": "Feature", "geometry": {"type": "Point",
                        "coordinates": [round(lon, 5), round(lat, 5)]},
                "properties": {"date": date, "npix": npix,
                               "peak_db": round(float(a_db[sl][lab[sl] == i].max()), 1),
                               "zone": zone}})
            count += 1
        zc = {z: sum(1 for f in feats if f["properties"]["date"] == date
                     and f["properties"]["zone"] == z) for z in ZONES}
        other = count - sum(zc.values())
        rows.append([date, count, zc["port_core"], zc["eastern_opl"], zc["western_opl"], other])
        print(f"{date}: {count:4d} vessels  (port {zc['port_core']}, eOPL {zc['eastern_opl']}, wOPL {zc['western_opl']}, other {other})")

    json.dump({"type": "FeatureCollection", "features": feats},
              open(f"{OUT}/detections_all.geojson", "w"))
    with open(f"{OUT}/monthly_counts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "total", "port_core", "eastern_opl", "western_opl", "other"])
        w.writerows(rows)
    print(f"\nwrote {OUT}/detections_all.geojson ({len(feats)} features), {OUT}/monthly_counts.csv")

if __name__ == "__main__":
    main()
