#!/usr/bin/env python3
"""SAFE -> sigma0 dB crop on the project grid (no CDSE processing units, no SNAP).

Opens a zipped S1 IW GRD product via GDAL's SAFE driver (UNCALIB DN + GCPs),
applies the product's own calibration LUTs (sigma0 = (DN/A)^2) from
annotation/calibration/*.xml, and inverse-warps onto the exact 2400x1500 bbox grid.
Noise LUT removal skipped (VV, local-statistics detector downstream).
"""
import sys, zipfile, re
import numpy as np
import rasterio
from scipy.interpolate import LinearNDInterpolator, RegularGridInterpolator
from scipy.ndimage import map_coordinates
import xml.etree.ElementTree as ET

BBOX = (103.55, 1.05, 104.35, 1.55); W, H = 2400, 1500

def load_luts(zip_path):
    """Per-swath sigma0 LUT interpolators from calibration XMLs (VV)."""
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist()
             if "/annotation/calibration/" in n
             and n.split("/")[-1].startswith("calibration-")
             and "-vv-" in n]
    luts = []
    for n in sorted(names):
        root = ET.fromstring(z.read(n))
        lines, pixels, vals = [], [], []
        for vec in root.iter("calibrationVector"):
            ln = int(vec.find("line").text)
            px = [int(x) for x in vec.find("pixel").text.split()]
            sv = [float(x) for x in vec.find("sigmaNought").text.split()]
            lines.append(ln); pixels.append(px); vals.append(sv)
        lines = np.array(lines)
        pix0 = np.array(pixels[0])
        M = np.zeros((len(lines), len(pix0)), dtype=np.float32)
        for i, (px, sv) in enumerate(zip(pixels, vals)):
            if len(px) == len(pix0):
                M[i] = sv
            else:  # variable-width safety
                M[i, :len(sv)] = sv[:len(pix0)]
        interp = RegularGridInterpolator((lines, pix0), M, bounds_error=False, fill_value=None)
        luts.append((lines.min(), lines.max(), pix0.min(), pix0.max(), interp))
        print(f"  lut {n.split('calibration-')[1][:16]}: lines {lines.min()}-{lines.max()} cols {pix0.min()}-{pix0.max()}")
    return luts

def calibrate(dn, rows, cols, luts):
    """sigma0 dB for sampled DN at (rows, cols)."""
    pts = np.column_stack([rows.ravel(), cols.ravel()])
    out = np.full(len(pts), np.nan, np.float32)
    for lo, hi, c0, c1, interp in luts:
        m = (pts[:,0] >= lo-3) & (pts[:,0] <= hi+3) & (pts[:,1] >= c0-3) & (pts[:,1] <= c1+3)
        if m.sum():
            out[m] = interp(pts[m]).astype(np.float32)
    nan = np.isnan(out)
    if nan.any() and luts:  # gaps between swaths: nearest LUT
        out[nan] = luts[0][4](pts[nan]).astype(np.float32)
    a = np.clip(out, 1e-6, None)
    return (10.0 * np.log10(np.clip(dn.ravel().astype(np.float32), 1e-6, None)**2 / a**2)).reshape(dn.shape)

def main(zip_path, out_tif):
    with zipfile.ZipFile(zip_path) as z:
        man = [n for n in z.namelist() if n.endswith("manifest.safe")][0]
    vsi = f"/vsizip/{zip_path}/{man}"
    with rasterio.open(vsi) as src:
        subs = [s for s in src.subdatasets if ":IW_VV:" in s and "UNCALIB" in s]
        with rasterio.open(subs[0]) as band:
            dn = band.read(1)
            gcps, _ = band.gcps
    # pre-multilook ~5x5 (8m -> ~40m) to suppress single-look speckle before resampling
    from scipy.ndimage import uniform_filter
    dn = uniform_filter(dn.astype(np.float32), size=5)
    print(f"DN {dn.shape} {dn.dtype} | gcps {len(gcps)}")
    luts = load_luts(zip_path)
    # GCP inverse warp to our grid
    g_lon = np.array([g.x for g in gcps]); g_lat = np.array([g.y for g in gcps])
    g_col = np.array([g.col for g in gcps], float); g_row = np.array([g.row for g in gcps], float)
    fi_col = LinearNDInterpolator(np.column_stack([g_lon, g_lat]), g_col)
    fi_row = LinearNDInterpolator(np.column_stack([g_lon, g_lat]), g_row)
    xs = np.linspace(BBOX[0], BBOX[2], W); ys = np.linspace(BBOX[3], BBOX[1], H)
    gx, gy = np.meshgrid(xs, ys)
    src_col = fi_col(gx, gy); src_row = fi_row(gx, gy)
    ok = np.isfinite(src_col) & np.isfinite(src_row)
    src_col = np.clip(src_col, 0, dn.shape[1]-1); src_row = np.clip(src_row, 0, dn.shape[0]-1)
    dn_s = map_coordinates(dn.astype(np.float32), [src_row, src_col], order=1, mode="constant", cval=0)
    db = calibrate(dn_s, src_row, src_col, luts)
    db[~ok] = -40.0
    sig = np.power(10.0, db / 10.0).astype(np.float32)   # linear sigma0, SH-crop compatible
    transform = rasterio.transform.from_bounds(*BBOX, W, H)
    with rasterio.open(out_tif, "w", driver="GTiff", height=H, width=W, count=1,
                       dtype="float32", crs="EPSG:4326", transform=transform) as dst:
        dst.write(sig, 1)
    valid = db > -39
    print(f"saved {out_tif} | valid {valid.mean()*100:.0f}% | p50(valid) {np.median(db[valid]):.1f} dB | >-12dB {(db>-12).mean()*100:.1f}% (SH-land-mask expectation ~55%)")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
