"""Vessel detection methods for Sentinel-1 SAR imagery.

Two methods available:
- CLASSIC_CFAR (v3.1): local mean + K*sigma threshold, with absolute floor
- TRIMMED_CFAR (v4): two-pass censored statistics (ships excluded from background)
  From Zhou et al. 2026 (arXiv 2509.22159) — finds ~159% more ships in dense scenes
"""
import numpy as np
from scipy import ndimage
import geopandas as gpd
from shapely.geometry import Point

CLASSIC_CFAR = "cfar"
TRIMMED_CFAR = "trimmed_cfar"

DEFAULT_K = 5.5
DEFAULT_WINDOW = 64  # pixels at ~37m/px ≈ 2.4 km
DEFAULT_MIN_PIXELS = 3
DEFAULT_SPLIT_THRESHOLD = 25  # split components larger than this into peaks


def detect_vessels(
    data,
    land_mask,
    method=TRIMMED_CFAR,
    bounds=None,
    k=DEFAULT_K,
    window=DEFAULT_WINDOW,
    min_pixels=DEFAULT_MIN_PIXELS,
    split_threshold=DEFAULT_SPLIT_THRESHOLD,
):
    """Detect vessels in a stack of calibrated SAR scenes.

    Parameters
    ----------
    data : list of numpy.ndarray
        Stack of calibrated scenes (linear sigma0, float32)
    land_mask : numpy.ndarray
        Boolean array: True = land, False = sea
    method : str
        "cfar" or "trimmed_cfar"
    bounds : tuple
        (lon_min, lat_min, lon_max, lat_max)
    k : float
        CFAR multiplier (higher = fewer detections)
    window : int
        Background window size in pixels
    min_pixels : int
        Minimum component size to count as a vessel
    split_threshold : int
        Split components larger than this into individual peaks

    Returns
    -------
    geopandas.GeoDataFrame
        Vessel detections with geometry (Point), date, zone, npix, peak_db
    """
    if method == CLASSIC_CFAR:
        threshold_fn = _classic_cfar_threshold
    elif method == TRIMMED_CFAR:
        threshold_fn = _trimmed_cfar_threshold
    else:
        raise ValueError(f"Unknown method: {method}. Use 'cfar' or 'trimmed_cfar'")

    sea = ~land_mask
    detections = []
    n_scenes = len(data)

    for i, scene in enumerate(data):
        db = 10 * np.log10(np.clip(scene, 1e-6, None))
        thr = threshold_fn(db, sea, k, window)
        scene_dets = _label_and_count(
            db, sea, thr, min_pixels, split_threshold
        )

        for det in scene_dets:
            det["scene_index"] = i
        detections.extend(scene_dets)

    # Convert to GeoDataFrame
    if not detections:
        return gpd.GeoDataFrame(columns=["date", "npix", "peak_db", "zone"])

    geometries = [Point(d["lon"], d["lat"]) for d in detections]
    gdf = gpd.GeoDataFrame(detections, geometry=geometries, crs="EPSG:4326")
    return gdf


def _classic_cfar_threshold(db, sea, k, window):
    """v3.1: local mean + k*sigma on dB, with absolute floor."""
    sea_valid = sea & (db > -30)
    fill = float(np.median(db[sea_valid]))

    x = np.where(sea_valid, db, 0.0)
    x2 = np.where(sea_valid, db * db, 0.0)
    valid = sea_valid.astype(np.float32)
    vf = np.maximum(ndimage.uniform_filter(valid, window), 1e-6)

    mu = ndimage.uniform_filter(x, window) / vf
    var = ndimage.uniform_filter(x2, window) / vf - mu * mu
    sig = np.sqrt(np.clip(var, 0, 400))

    return np.maximum(mu + k * sig, -12.0)


def _trimmed_cfar_threshold(db, sea, k, window):
    """v4: two-pass censored statistics (ships excluded from background)."""
    sea_valid = sea & (db > -30)
    vals = db[sea_valid]

    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    provisional = med + k * mad

    # Censor: exclude pixels above provisional threshold from background
    bg = sea_valid & (db < provisional)

    x = np.where(bg, db, 0.0)
    x2 = np.where(bg, db * db, 0.0)
    valid = bg.astype(np.float32)
    vf = np.maximum(ndimage.uniform_filter(valid, window), 1e-6)

    mu = ndimage.uniform_filter(x, window) / vf
    var = ndimage.uniform_filter(x2, window) / vf - mu * mu
    sig = np.sqrt(np.clip(var, 0, 400))

    return mu + k * sig  # purely adaptive, no floor


def _label_and_count(db, sea, thr, min_pixels, split_threshold):
    """Label connected components and count vessels (with peak splitting)."""
    import rasterio.transform

    cand = sea & (db > thr)
    labeled, n = ndimage.label(cand)
    if n == 0:
        return []

    lmax = ndimage.maximum_filter(db, size=7)
    detections = []

    for i, sl in enumerate(ndimage.find_objects(labeled), start=1):
        comp = labeled[sl] == i
        npix = int(comp.sum())
        if npix < min_pixels:
            continue

        sub = np.where(comp, db[sl], -99.0)

        if npix > split_threshold:
            # Split into peaks (for dense anchored queues)
            peaks = comp & (sub >= lmax[sl])
            ys, xs = np.nonzero(peaks)
            if len(ys) == 0:
                cy, cx = ndimage.center_of_mass(comp)
                ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])
        else:
            cy, cx = ndimage.center_of_mass(comp)
            ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])

        for y, x in zip(ys, xs):
            detections.append({
                "row": y + sl[0].start,
                "col": x + sl[1].start,
                "npix": npix,
                "peak_db": round(float(sub.max()), 1),
            })

    return detections
