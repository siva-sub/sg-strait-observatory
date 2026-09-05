#!/usr/bin/env python3
"""OData backfill: fill missing months via full-product downloads (no processing units).

Phase A: download ~12 spread months -> local median land mask (Otsu on dB composite;
  local sigma0 scale differs from SH gamma0, so threshold is data-driven).
Phase B: for each missing month (priority: 2026 -> 2023 -> 2020..2015), download the
  best-cover product for one day, crop via safe_to_crop, detect with v3.1 math,
  append row to perscene_counts.csv, delete zip, keep 13MB crop.
Disk-flat: one zip at a time; stops if free disk < 10 GB. Resumable by rows + kept crops.
"""
import os, sys, glob, json, csv, time, subprocess, shutil
import numpy as np
import rasterio
from scipy import ndimage
from scipy import stats as sstats
import importlib.util

ROOT = os.path.abspath(os.path.dirname(__file__) + "/..")
os.chdir(ROOT)
SPOOL = "experiments/data/spool"; CROPS = "experiments/data/crops"
COUNTS = "experiments/results/perscene_counts.csv"
BBOX = (103.55, 1.05, 104.35, 1.55); W, H = 2400, 1500
ZONES = {"port_core": (103.68, 1.20, 104.02, 1.34),
         "eastern_opl": (104.00, 1.24, 104.35, 1.40),
         "western_opl": (103.58, 1.10, 103.78, 1.32)}
TRANSFORM = rasterio.transform.from_bounds(*BBOX, W, H)

spec = importlib.util.spec_from_file_location("p", "experiments/fetch_detect_perscene.py")
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
spec2 = importlib.util.spec_from_file_location("s2c", "experiments/safe_to_crop.py")
S2C = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(S2C)

def free_gb():
    return shutil.disk_usage("/").free / 1e9

def done_days():
    if not os.path.exists(COUNTS): return set()
    return {r[0] for r in csv.reader(open(COUNTS)) if r and r[0].isdigit()}

def month_days(month):
    """Catalogue day-prefixes for a month (per-year query, small)."""
    import requests, re
    y = month[:4]
    s = f"{month[:4]}-{month[4:]}-01T00:00:00.000Z"
    ny, nm = (int(y)+1, 1) if month[4:] == "12" else (int(y), int(month[4:])+1)
    e = f"{ny:04d}-{nm:02d}-01T00:00:00.000Z"
    poly = "POLYGON((103.55 1.05,104.35 1.05,104.35 1.55,103.55 1.55,103.55 1.05))"
    flt = (f"Collection/Name eq 'SENTINEL-1' and contains(Name,'_IW_GRDH_1S') and "
           f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}') and "
           f"ContentDate/Start gt {s} and ContentDate/Start lt {e}")
    out = {}
    skip = 0
    while True:
        r = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
                         params={"$filter": flt, "$top": "800", "$skip": str(skip), "$select": "Name"}, timeout=120)
        val = r.json().get("value", [])
        if not val: break
        for p in val:
            m = re.match(r"(S1[A-Z]_IW_GRDH_1S[DA][HV]_\d{8}T\d{6})", p["Name"])
            if m: out.setdefault(m.group(1)[:22], True)
        skip += 800
        if skip > 2400: break
    return sorted(out.keys())

def crop_of(day):
    d = day.split("_")[-1][:8]
    return f"{CROPS}/s1_{d}.tif"

def process_crop(tif, day):
    with rasterio.open(tif) as s:
        a = np.nan_to_num(s.read(1).astype(np.float32), nan=-40.0)
    sat = "S1A" if day.startswith("S1A") else ("S1D" if day.startswith("S1D") else day[:3])
    try:
        counts, total, cov = P.detect(a)
    except ValueError as e:
        return ("LOWCOV", str(e))
    if cov < 0.80:
        return ("LOWCOV", f"cov {cov:.2f}")
    return ("OK", sat, day.split("_")[-1][:8], f"{cov:.3f}", total,
            counts["port_core"], counts["eastern_opl"], counts["western_opl"], counts["strait_other"])

def append_row(row):
    hdr = not os.path.exists(COUNTS)
    with open(COUNTS, "a", newline="") as f:
        w = csv.writer(f)
        if hdr: w.writerow(["day","sat","status","cov","total","port_core","eastern_opl","western_opl","other"])
        w.writerow(row); f.flush()

def build_local_mask():
    """Phase A: land mask from whatever crops exist (need >= 8)."""
    crops = sorted(glob.glob(f"{CROPS}/s1_*.tif"))
    if len(crops) < 8:
        return False
    stack = []
    for c in crops:
        with rasterio.open(c) as s:
            stack.append(np.nan_to_num(s.read(1).astype(np.float32), nan=-40.0))
    med = np.median(np.stack(stack), axis=0)
    valid = med > -30
    hist, edges = np.histogram(med[valid], bins=256)
    mids = (edges[:-1]+edges[1:])/2
    w0 = np.cumsum(hist).astype(float); wT = w0[-1]; w1 = wT - w0
    m0 = np.cumsum(hist*mids); mt = m0[-1]
    mu0 = m0/np.maximum(w0,1); mu1 = (mt-m0)/np.maximum(w1,1)
    sb = w0[:255]/wT * (w1[1:]/wT) * (mu0[:255]-mu1[1:])**2
    thr = mids[:255][np.argmax(sb)]
    land = ndimage.binary_dilation((med > thr) & valid, iterations=6)
    np.save(f"{SPOOL}/local_landmask.npy", land)
    # zones on our grid
    zm = {}
    for z, (w_, s_, e_, n_) in ZONES.items():
        r0, c0 = rasterio.transform.rowcol(TRANSFORM, w_, n_)
        r1, c1 = rasterio.transform.rowcol(TRANSFORM, e_, s_)
        m = np.zeros_like(land); m[max(r0,0):r1, max(c0,0):c1] = True; zm[z] = m
    P.SEA = ~land; P.ZMASK = zm; P.TR = TRANSFORM
    print(f"[mask] otsu thr {thr:.1f} dB | land {land.mean()*100:.0f}% | from {len(crops)} crops", flush=True)
    return True

def phaseA(months):
    have = {os.path.basename(c)[3:11] for c in glob.glob(f"{CROPS}/s1_*.tif")}
    need = [m for m in months if not any(h.startswith(m) for h in have)]
    spread = need[::max(1, len(need)//12)][:12] if need else []
    for m in spread:
        if free_gb() < 10: print("[A] low disk, stop"); return
        for day in month_days(m)[:2]:
            tif = crop_of(day)
            if os.path.exists(tif): continue
            z = f"{SPOOL}/tmp.zip"
            print(f"[A] {m}: {day} downloading...", flush=True)
            r = subprocess.run([sys.executable, "experiments/download_product.py", day, z],
                               capture_output=True, text=True, timeout=3600)
            if "OK" not in r.stdout:
                print(f"[A] dl fail: {r.stdout.strip()[:80]}"); continue
            try:
                S2C.main(z, tif)
            except SystemExit as e:
                print(f"[A] crop fail: {e}"); os.remove(z); continue
            os.remove(z)
            break

def phaseB(months, budget_minutes=99999):
    t0 = time.time()
    dd = done_days()
    for m in months:
        if (time.time()-t0)/60 > budget_minutes: print("[B] time budget reached"); break
        if free_gb() < 10: print("[B] low disk, stop"); break
        got_ok = any(r[0].startswith(m) and len(r)>2 and r[2]=="OK"
                     for r in csv.reader(open(COUNTS)) if r and r[0].isdigit())
        if got_ok: continue
        for day in month_days(m)[:3]:
            d8 = day.split("_")[-1][:8]
            if d8 in dd: continue
            tif = crop_of(day)
            if not os.path.exists(tif):
                z = f"{SPOOL}/tmp.zip"
                print(f"[B] {m}: {day} downloading...", flush=True)
                r = subprocess.run([sys.executable, "experiments/download_product.py", day, z],
                                   capture_output=True, text=True, timeout=3600)
                if "OK" not in r.stdout:
                    print(f"[B] dl fail: {r.stdout.strip()[:80]}"); continue
                try:
                    S2C.main(z, tif)
                except SystemExit as e:
                    print(f"[B] crop fail: {e}"); os.remove(z); continue
                os.remove(z)
            res = process_crop(tif, day)
            if res[0] == "OK":
                append_row([res[2], res[1], "OK", res[3], res[4], res[5], res[6], res[7], res[8]])
                print(f"[B] {m}: OK day {res[2]} cov {res[3]} total {res[4]} (eOPL {res[6]})", flush=True)
                break
            else:
                append_row([d8, day[:3], "LOWCOV", "", "", "", "", "", ""])
                print(f"[B] {m}: {day} {res[0]} {res[1]}", flush=True)

if __name__ == "__main__":
    missing = json.load(open(f"{SPOOL}/missing_months.json"))
    prio = sorted(missing, key=lambda m: (0 if m >= "2026" else 1 if m.startswith("2023") else 2, m), reverse=False)
    prio = sorted(prio, key=lambda m: -(int(m)))  # newest first
    print(f"missing: {len(prio)} months | order: {prio[:3]} ... {prio[-2:]}", flush=True)
    phaseA(prio)
    if not build_local_mask():
        print("Phase A incomplete (<8 crops) — rerun to continue"); sys.exit(2)
    phaseB(prio)
    print("BACKFILL DONE", flush=True)
