#!/usr/bin/env python3
"""Fetch monthly Sentinel-1 VV (gamma0, orthorectified) crops of the Singapore Strait AOI
via CDSE Sentinel Hub Process API. One image per month (SIMPLE mosaicking = latest coverage).
Reads credentials from .env. Output: experiments/data/s1_vv_YYYYMM.tif (FLOAT32, ~32 MB each).
"""
import os, sys, time, requests

MONTHS = [f"2025{m:02d}" for m in range(9, 13)] + [f"2026{m:02d}" for m in range(1, 9)]  # 12 months
BBOX = [103.55, 1.05, 104.35, 1.55]  # lon_min, lat_min, lon_max, lat_max
W, H = 2400, 1500                     # ~37 m/px (Sentinel Hub caps dimensions at 2500 px)

EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV"] }],
    output: [{ id: "vv", bands: 1, sampleType: "FLOAT32" }]
  };
}
function evaluatePixel(s) { return { vv: [s.VV] }; }
"""

def load_env(path=".env"):
    env = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env

def get_token(env):
    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"grant_type": "password", "username": env["CDSE_USER"],
              "password": env["CDSE_PASSWORD"], "client_id": "cdse-public"},
        timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_month(tok, yyyymm):
    start = f"{yyyymm[:4]}-{yyyymm[4:]}-01T00:00:00Z"
    y, m = int(yyyymm[:4]), int(yyyymm[4:])
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    end = f"{ny:04d}-{nm:02d}-01T00:00:00Z"
    body = {
        "input": {
            "bounds": {"bbox": BBOX,
                       "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{"dataFilter": {"timeRange": {"from": start, "to": end}},
                      "type": "sentinel-1-grd",
                      "processing": {"orthorectify": "true"}}]
        },
        "output": {"width": W, "height": H,
                   "responses": [{"identifier": "vv", "format": {"type": "image/tiff"}}]},
        "evalscript": EVALSCRIPT
    }
    r = requests.post("https://sh.dataspace.copernicus.eu/api/v1/process",
                      json=body, headers={"Authorization": f"Bearer {tok}"}, timeout=300)
    return r

def main():
    os.makedirs("experiments/data", exist_ok=True)
    env = load_env()
    tok = get_token(env)
    print("token acquired")
    ok, fail = 0, 0
    for ym in MONTHS:
        out = f"experiments/data/s1_vv_{ym}.tif"
        if os.path.exists(out) and os.path.getsize(out) > 1_000_000:
            print(f"{ym}: exists ({os.path.getsize(out)/1e6:.1f} MB), skip"); ok += 1; continue
        r = fetch_month(tok, ym)
        if r.status_code == 200 and len(r.content) > 1_000_000:
            open(out, "wb").write(r.content)
            print(f"{ym}: OK  {len(r.content)/1e6:.1f} MB"); ok += 1
        else:
            print(f"{ym}: FAIL {r.status_code} {r.text[:180]}"); fail += 1
            if r.status_code == 401:  # token expired mid-run
                tok = get_token(env); print("  re-authenticated")
                r = fetch_month(tok, ym)
                if r.status_code == 200 and len(r.content) > 1_000_000:
                    open(out, "wb").write(r.content); print(f"{ym}: OK retry"); ok += 1; fail -= 1
        time.sleep(2)
    print(f"done: {ok} ok, {fail} failed")
    sys.exit(0 if fail == 0 else 1)

if __name__ == "__main__":
    main()
