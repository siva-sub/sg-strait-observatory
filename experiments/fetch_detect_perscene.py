#!/usr/bin/env python3
"""Per-scene pipeline: for every Sentinel-1 IW-GRD acquisition over the strait AOI,
fetch VV (Process API) -> run v3.1 detector -> append per-date zone counts -> delete TIFF.

Resumable: skips dates already present in experiments/results/perscene_counts.csv.
Disk-flat: tifs live in experiments/data/tmp and are deleted after detection.
Usage: .venv/bin/python experiments/fetch_detect_perscene.py 2019-01-01 2026-09-04 [workers]
"""
import os, sys, csv, glob, json, re, time, threading, requests
import numpy as np
import rasterio
from scipy import ndimage
from concurrent.futures import ThreadPoolExecutor, as_completed

START, END = (sys.argv[1] if len(sys.argv) > 1 else "2019-01-01"), (sys.argv[2] if len(sys.argv) > 2 else "2026-09-04")
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 4

OUT_CSV = "experiments/results/perscene_counts.csv"
FAIL_CSV = "experiments/results/perscene_failures.csv"
COV_MIN_OK = 0.80   # acceptance: valid-sea coverage fraction must be >= this
COV_MIN_ANY = 0.25  # below this the scene is unusable (hard fail)
TMP = "experiments/data/tmp"; os.makedirs(TMP, exist_ok=True)
os.makedirs("experiments/results", exist_ok=True)

BBOX = [103.55, 1.05, 104.35, 1.55]; W, H = 2400, 1500
ZONES = {"port_core": (103.68, 1.20, 104.02, 1.34),   # QA-verified: water + anchorage rows
         "eastern_opl": (104.00, 1.24, 104.35, 1.40),  # FIXED 2026-09-04: old box (1.08-1.24N) sat on Batam/Hang Nadim (glm vision QA); now open water NE of Batam
         "western_opl": (103.58, 1.10, 103.78, 1.32)}
K, WIN, MINP, FLOOR_DB, LAND_MED_DB, SPLIT = 5.5, 64, 3, -12.0, -12.0, 25

EVALSCRIPT = """//VERSION=3
function setup(){return{input:[{bands:["VV"]}],output:[{id:"vv",bands:1,sampleType:"FLOAT32"}]};}
function evaluatePixel(s){return{vv:[s.VV]};}"""

ENV = dict(l.strip().split("=", 1) for l in open(".env") if l.strip() and not l.startswith("#"))
LOCK = threading.Lock()

def get_token():
    r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                      data={"grant_type": "password", "username": ENV["CDSE_USER"],
                            "password": ENV["CDSE_PASSWORD"], "client_id": "cdse-public"}, timeout=30)
    r.raise_for_status(); return r.json()["access_token"]

def catalogue_dates():
    poly = "POLYGON((103.55 1.05,104.35 1.05,104.35 1.55,103.55 1.55,103.55 1.05))"
    flt = (f"Collection/Name eq 'SENTINEL-1' and contains(Name,'_IW_GRDH_1S') and "
           f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}') and "
           f"ContentDate/Start gt {START}T00:00:00.000Z and ContentDate/Start lt {END}T00:00:00.000Z")
    out, skip = {}, 0
    while True:
        r = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
                         params={"$filter": flt, "$top": "800", "$skip": str(skip),
                                 "$select": "Name,ContentDate"}, timeout=120)
        r.raise_for_status(); val = r.json().get("value", [])
        if not val: break
        for p in val:
            m = re.match(r"(S1[A-Z])_IW_GRDH_1S[DA][HV]_(\d{8})", p["Name"])
            if m: out.setdefault(m.group(2), m.group(1))  # one sample per day
        skip += 800
        if skip > 6000: break
    return sorted(out.items())

def land_mask_and_zones():
    imgs = []
    for p in sorted(glob.glob("experiments/data/s1_vv_*.tif"))[:12]:
        with rasterio.open(p) as s:
            a = np.nan_to_num(s.read(1).astype(np.float32), nan=0.0)
            imgs.append(10.0*np.log10(np.clip(a, 1e-6, None))); tr = s.transform
    med = np.median(np.stack(imgs), axis=0)
    land = ndimage.binary_dilation(med > LAND_MED_DB, iterations=6)
    zm = {}
    for z, (w, s_, e, n_) in ZONES.items():
        r0, c0 = rasterio.transform.rowcol(tr, w, n_)   # rowcol(x=lon, y=lat)
        r1, c1 = rasterio.transform.rowcol(tr, e, s_)
        m = np.zeros_like(land); m[max(r0,0):r1, max(c0,0):c1] = True; zm[z] = m
    return land, zm, tr

SEA, ZMASK, TR = None, None, None  # set in main

def detect(a):
    a_db = 10.0*np.log10(np.clip(a, 1e-6, None))
    sea_valid = SEA & (a_db > -45.0)
    cov = float(sea_valid.sum()) / max(float(SEA.sum()), 1.0)
    if cov < COV_MIN_ANY:
        raise ValueError(f"low coverage {cov:.2f}")
    sea = sea_valid
    gsea = float(np.median(a_db[sea]))
    x = np.where(sea, a_db, gsea); x2 = np.where(sea, a_db*a_db, gsea*gsea)
    mu = ndimage.uniform_filter(x, WIN)
    var = ndimage.uniform_filter(x2, WIN) - mu*mu
    sig = np.sqrt(np.clip(var, 0.0, 400.0))
    thr = np.maximum(mu + K*sig, FLOOR_DB)
    cand = sea & (a_db > thr)
    lab, nl = ndimage.label(cand)
    counts = {z: 0 for z in list(ZMASK) + ["strait_other"]}; total = 0
    if not nl: return counts, total, cov
    lmax = ndimage.maximum_filter(a_db, size=7)
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        comp = (lab[sl] == i)
        if comp.sum() < MINP: continue
        sub = np.where(comp, a_db[sl], -99.0)
        if comp.sum() > SPLIT:
            ys, xs = np.nonzero(comp & (sub >= lmax[sl]))
            if len(ys) == 0:
                cy, cx = ndimage.center_of_mass(comp)
                ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])
        else:
            cy, cx = ndimage.center_of_mass(comp)
            ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])
        for y, x_ in zip(ys, xs):
            r, c = y + sl[0].start, x_ + sl[1].start
            z = next((n for n, m in ZMASK.items() if m[r, c]), "strait_other")
            counts[z] += 1; total += 1
    return counts, total, cov

def process_day(tok_holder, day, sat):
    for attempt in range(3):
        try:
            start = f"{day[:4]}-{day[4:6]}-{day[6:]}T00:00:00Z"
            ny, nm, nd = (int(day[:4]), int(day[4:6]), int(day[6:]))
            import datetime as dt
            nxt = dt.date(ny, nm, nd) + dt.timedelta(days=1)
            body = {"input": {"bounds": {"bbox": BBOX, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
                              "data": [{"dataFilter": {"timeRange": {"from": start, "to": f"{nxt.isoformat()}T00:00:00Z"}},
                                        "type": "sentinel-1-grd", "processing": {"orthorectify": "true"}}]},
                    "output": {"width": W, "height": H, "responses": [{"identifier": "vv", "format": {"type": "image/tiff"}}]},
                    "evalscript": EVALSCRIPT}
            r = requests.post("https://sh.dataspace.copernicus.eu/api/v1/process", json=body,
                              headers={"Authorization": f"Bearer {tok_holder[0]}"}, timeout=300)
            if r.status_code == 401:
                tok_holder[0] = get_token(); continue
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1)); continue
            if r.status_code != 200 or len(r.content) < 1_000_000:
                return ("FAIL", day, sat, f"http {r.status_code}")
            tmp = f"{TMP}/s1_{day}.tif"; open(tmp, "wb").write(r.content)
            with rasterio.open(tmp) as s:
                a = np.nan_to_num(s.read(1).astype(np.float32), nan=0.0)
            counts, total, cov = detect(a)
            os.remove(tmp)
            if cov >= COV_MIN_OK:
                return ("OK", day, sat, cov, total, counts["port_core"], counts["eastern_opl"], counts["western_opl"], counts["strait_other"])
            else:
                return ("LOWCOV", day, sat, cov)
        except Exception as e:
            if attempt == 2: return ("FAIL", day, sat, str(e)[:120])
            time.sleep(5)
    return ("FAIL", day, sat, "retries exhausted")

def main():
    global SEA, ZMASK, TR
    _land, ZMASK, TR = land_mask_and_zones()
    SEA = ~_land          # function returns the LAND mask; SEA is its complement
    print(f"land mask: {(~SEA).mean()*100:.0f}% sea | loading catalogue {START}..{END}", flush=True)
    days = catalogue_dates()
    days = days[::-1]  # NEWEST FIRST: congestion window + recent era arrive early under throttling
    done = set()
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV) as f:
            done = {row["day"] for row in csv.DictReader(f)}  # any status: don't refetch partials
    todo = [(d, s) for d, s in days if d not in done]
    print(f"catalogue: {len(days)} days | done: {len(done)} | todo: {len(todo)}", flush=True)
    write_header = not os.path.exists(OUT_CSV)
    tok = [get_token()]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process_day, tok, d, s): d for d, s in todo}
        n = 0
        with open(OUT_CSV, "a", newline="") as fo, open(FAIL_CSV, "a", newline="") as ff:
            wo = csv.writer(fo); wf = csv.writer(ff)
            if write_header: wo.writerow(["day","sat","status","cov","total","port_core","eastern_opl","western_opl","other"])
            for fut in as_completed(futs):
                res = fut.result(); n += 1
                with LOCK:
                    if res[0] == "OK":
                        wo.writerow([res[1], res[2], res[0], f"{res[3]:.3f}"] + list(res[4:])); fo.flush()
                    elif res[0] == "LOWCOV":
                        wo.writerow([res[1], res[2], res[0], f"{res[3]:.3f}", "", "", "", "", ""]); fo.flush()
                    else:
                        wf.writerow(res[1:]); ff.flush()
                if n % 25 == 0:
                    rate = n / (time.time() - t0)
                    print(f"{n}/{len(todo)} | {rate:.2f}/s | eta {(len(todo)-n)/max(rate,1e-9)/60:.0f} min", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
