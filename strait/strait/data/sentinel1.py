"""Sentinel-1 data access via Copernicus Data Space Ecosystem.

Two access paths:
1. Sentinel Hub Process API (server-side processing, uses processing units)
2. CDSE OData (full-product download, uses download quota only)

The module handles authentication, scene discovery, calibration, and
coastline-based land masking.
"""
import os
import logging
from typing import Tuple, Optional

import numpy as np
import rasterio
from rasterio.transform import from_bounds

logger = logging.getLogger(__name__)


def get_credentials() -> Tuple[str, str]:
    """Get CDSE credentials from environment or .env file."""
    user = os.environ.get("CDSE_USER", "")
    password = os.environ.get("CDSE_PASSWORD", "")

    if not user:
        # Try .env file
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
        data={
            "grant_type": "password",
            "username": user,
            "password": password,
            "client_id": "cdse-public",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def prepare_sentinel1(
    bounds: Tuple[float, float, float, float],
    time_range: Tuple[str, str],
    cache_dir=None,
    overwrite=False,
    width=2400,
    height=1500,
):
    """Download and process Sentinel-1 scenes for a bounding box.

    Returns
    -------
    data : list of numpy.ndarray
        Stack of calibrated scenes (linear sigma0, float32)
    land_mask : numpy.ndarray
        Boolean array: True = land
    """
    # TODO: implement full pipeline
    # For now, this is a stub that loads from the observatory project's cache
    logger.warning("Sentinel-1 data source not yet implemented as standalone module.")
    logger.info("Use the observatory project's scripts for now.")

    # Return empty placeholders
    data = []
    land_mask = np.zeros((height, width), dtype=bool)
    return data, land_mask


def load_s2coast_landmask(
    bounds: Tuple[float, float, float, float],
    width: int = 2400,
    height: int = 1500,
) -> np.ndarray:
    """Load S2Coast-2023 land mask for a bounding box.

    S2Coast-2023 is a global 10m coastline dataset from Sentinel-2.
    Available from Zenodo: https://zenodo.org/records/17092775
    """
    import geopandas as gpd
    from rasterio.features import rasterize
    from shapely.geometry import box as shapely_box

    # This assumes the S2Coast shapefile has been downloaded
    # In a future version, this would auto-download from Zenodo
    shp_path = os.path.join(
        os.path.expanduser("~/.strait"),
        "S2Coast-2023_Polygon_fishnet.shp"
    )

    if not os.path.exists(shp_path):
        logger.warning("S2Coast shapefile not found at %s. Using uniform sea mask.", shp_path)
        return np.zeros((height, width), dtype=bool)

    gdf = gpd.read_file(shp_path)
    bbox_geom = shapely_box(*bounds)
    region = gdf[gdf.intersects(bbox_geom)]

    transform = from_bounds(*bounds, width, height)
    land = rasterize(
        [(geom, 1) for geom in region.geometry],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=True,
    ).astype(bool)

    return land
