"""Sentinel-1 data access: local cache + CDSE (when available).

Two access paths:
1. Local cache: load pre-processed scenes from disk (no credentials needed)
2. CDSE OData: download full products and process locally (uses download quota)
3. CDSE Sentinel Hub: server-side processing (uses processing units, quota-limited)

For local mode, the package expects a directory structure:
    ~/.strait/  (or custom path)
    ├── scenes/          # pre-processed .tif scenes (float32, linear sigma0)
    ├── land_mask.tif    # S2Coast-2023 or similar boolean land mask
    └── manifest.json    # scene metadata (dates, coverage)
"""
import os
import json
import logging
import glob as globlib
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import rasterio
from rasterio.transform import from_bounds as affine_from_bounds

logger = logging.getLogger(__name__)


def discover_local_scenes(cache_dir: str = "~/.strait") -> List[dict]:
    """Find pre-processed scenes in the local cache.

    Returns list of dicts: {path, date, bounds, shape}
    """
    cache = Path(cache_dir).expanduser()
    scenes_dir = cache / "scenes"
    if not scenes_dir.exists():
        return []

    found = []
    for path in sorted(globlib.glob(str(scenes_dir / "*.tif"))):
        try:
            with rasterio.open(path) as src:
                b = src.bounds
                found.append({
                    "path": str(path),
                    "date": Path(path).stem.replace("s1_", "")[:8],
                    "bounds": (b.left, b.bottom, b.right, b.top),
                    "shape": (src.height, src.width),
                })
        except Exception:
            logger.warning("Could not read %s", path)
    return found


def load_local_scenes(
    cache_dir: str = "~/.strait",
    bounds: Optional[Tuple[float, float, float, float]] = None,
    shape: Tuple[int, int] = (1500, 2400),
) -> Tuple[List[np.ndarray], List[str], np.ndarray]:
    """Load scenes from local cache.

    Parameters
    ----------
    cache_dir : str
        Path to cache directory containing scenes/ and land_mask.tif
    bounds : tuple
        (lon_min, lat_min, lon_max, lat_max) — used for coordinate reference
    shape : tuple
        (rows, cols) expected scene shape

    Returns
    -------
    scenes : list of ndarray
    dates : list of str
    land_mask : ndarray
    """
    cache = Path(cache_dir).expanduser()

    # Load land mask
    mask_path = cache / "land_mask.tif"
    if mask_path.exists():
        with rasterio.open(mask_path) as src:
            land_mask = src.read(1) > 0
    else:
        logger.warning("No land mask found at %s. Using all-sea mask.", mask_path)
        land_mask = np.zeros(shape, dtype=bool)

    # Load scenes
    scenes_dir = cache / "scenes"
    if not scenes_dir.exists():
        raise FileNotFoundError(
            f"No scenes directory at {scenes_dir}. "
            f"Place .tif files (float32, linear sigma0) in {scenes_dir}/ "
            f"or use module='demo' for synthetic data."
        )

    scenes, dates = [], []
    for path in sorted(globlib.glob(str(scenes_dir / "*.tif"))):
        try:
            with rasterio.open(path) as src:
                data = np.nan_to_num(src.read(1).astype(np.float32), nan=0.0)
            scenes.append(data)
            date = Path(path).stem.replace("s1_", "")[:6]  # YYYYMM
            dates.append(date)
        except Exception as e:
            logger.warning("Skipping %s: %s", path, e)

    if not scenes:
        raise FileNotFoundError(f"No valid .tif scenes found in {scenes_dir}")

    logger.info("Loaded %d scenes from %s", len(scenes), scenes_dir)
    return scenes, dates, land_mask


def create_cache_from_directory(
    source_dir: str,
    cache_dir: str = "~/.strait",
    land_mask_path: Optional[str] = None,
):
    """Build a local cache from a directory of .tif scenes.

    This is the bridge between the observatory project's raw data
    and the strait package's cache format.
    """
    cache = Path(cache_dir).expanduser()
    scenes_dir = cache / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    # Copy scenes
    copied = 0
    for path in sorted(globlib.glob(os.path.join(source_dir, "*.tif"))):
        dst = scenes_dir / Path(path).name
        if not dst.exists():
            import shutil
            shutil.copy2(path, dst)
            copied += 1

    # Copy land mask
    if land_mask_path:
        dst_mask = cache / "land_mask.tif"
        if not dst_mask.exists():
            import shutil
            shutil.copy2(land_mask_path, dst_mask)

    # Write manifest
    manifest = {"scenes": discover_local_scenes(str(cache)), "created": str(np.datetime64("now"))}
    with open(cache / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)

    logger.info("Cache created: %d scenes copied, mask: %s", copied, bool(land_mask_path))


# ── CDSE access (requires credentials) ──

def get_credentials() -> Tuple[str, str]:
    """Get CDSE credentials from environment or .env file."""
    user = os.environ.get("CDSE_USER", "")
    password = os.environ.get("CDSE_PASSWORD", "")

    if not user:
        for env_path in [".env", os.path.expanduser("~/.strait/.env")]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("CDSE_USER="):
                            user = line.split("=", 1)[1]
                        elif line.startswith("CDSE_PASSWORD="):
                            password = line.split("=", 1)[1]
    return user, password


def get_token() -> str:
    """Get OAuth token from CDSE."""
    import requests

    user, password = get_credentials()
    if not user:
        raise RuntimeError("CDSE credentials not found. Set CDSE_USER and CDSE_PASSWORD.")

    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"grant_type": "password", "username": user, "password": password,
              "client_id": "cdse-public"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def prepare_sentinel1(
    bounds: Tuple[float, float, float, float],
    time_range: Tuple[str, str],
    cache_dir=None,
    shape: Tuple[int, int] = (1500, 2400),
    use_local: bool = True,
) -> Tuple[List[np.ndarray], List[str], np.ndarray]:
    """Prepare Sentinel-1 scenes for a bounding box.

    Tries local cache first, falls back to CDSE download.
    """
    if use_local:
        try:
            return load_local_scenes(str(cache_dir), bounds, shape)
        except FileNotFoundError:
            logger.info("No local cache found. Falling back to CDSE.")

    # CDSE path (requires credentials and quota)
    from .odata import download_and_process
    return download_and_process(bounds, time_range, cache_dir, shape)
