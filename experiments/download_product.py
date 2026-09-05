#!/usr/bin/env python3
"""Download the S1 product for a day-prefix with BEST bbox coverage (OData).

Scores all candidate products by approx overlap of footprint polygon with the
AOI bbox (polygon-vertex sampling + bbox-corner containment), picks the best,
downloads via zipper $value. Prints 'OK <name> <GB>' or an error.
"""
import sys, re, requests, os

day_prefix, out = sys.argv[1], sys.argv[2]
AOI = (103.55, 1.05, 104.35, 1.55)
env = dict(l.strip().split("=", 1) for l in open(".env") if "=" in l and not l.startswith("#"))

def tok():
    return requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"grant_type": "password", "username": env["CDSE_USER"], "password": env["CDSE_PASSWORD"],
              "client_id": "cdse-public"}, timeout=30).json()["access_token"]

def wkt_overlap(geo):
    """Approx coverage score. Accepts GeoJSON dict or WKT string."""
    if not geo: return 0.0
    pts = []
    if isinstance(geo, dict):
        ring = (geo.get("coordinates") or [[]])[0]
        for c in ring:
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                pts.append((float(c[0]), float(c[1])))
    elif isinstance(geo, str):
        nums = [float(x) for x in re.findall(r"[-\d.]+(?:e[-\d]+)?", geo)]
        pts = list(zip(nums[0::2], nums[1::2]))
    if not pts: return 0.0
    lo, la, hi, lb = AOI
    inside = sum(1 for x, y in pts if lo <= x <= hi and la <= y <= lb)
    frac_v = inside / len(pts)
    # bbox-center and corners: is scene covering them (point-in-polygon)?
    def pip(px, py):
        c = False; n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]; x2, y2 = pts[(i+1) % n]
            if (y1 > py) != (y2 > py) and px < (x2-x1)*(py-y1)/(y2-y1+1e-12)+x1: c = not c
        return c
    corn = sum(pip(*p) for p in [(lo,la),(hi,la),(hi,lb),(lo,lb),((lo+hi)/2,(la+lb)/2)])
    return 0.5*frac_v + 0.1*corn

poly = "POLYGON((103.55 1.05,104.35 1.05,104.35 1.55,103.55 1.55,103.55 1.05))"
flt = (f"Collection/Name eq 'SENTINEL-1' and startswith(Name,'{day_prefix}') and contains(Name,'_IW_GRDH_1S') and "
       f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}')")
r = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
                 params={"$filter": flt, "$top": "10",
                         "$select": "Id,Name,ContentLength,GeoFootprint"}, timeout=60)
vals = r.json().get("value", [])
if not vals:
    print("NO_PRODUCT"); sys.exit(3)
for v in vals:
    v["_score"] = wkt_overlap(v.get("GeoFootprint", ""))
vals.sort(key=lambda v: -v["_score"])
p = vals[0]
print(f"selected {p['Name']} score {p['_score']:.2f} ({p['ContentLength']/1e9:.2f}GB; "
      f"others: {[round(v['_score'],2) for v in vals[1:3]]})", flush=True)
url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({p['Id']})/$value"
t = tok()
with requests.get(url, headers={"Authorization": f"Bearer {t}"}, stream=True, timeout=3600) as resp:
    if resp.status_code in (401, 403):
        t = tok()
        resp = requests.get(url, headers={"Authorization": f"Bearer {t}"}, stream=True, timeout=3600)
    resp.raise_for_status()
    with open(out, "wb") as f:
        for chunk in resp.iter_content(1 << 22):
            f.write(chunk)
print(f"OK {p['Name']} {os.path.getsize(out)/1e9:.2f}GB")
