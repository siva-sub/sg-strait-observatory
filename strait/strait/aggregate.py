"""Aggregate vessel detections by zone and time period."""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def aggregate(
    detections,
    zones: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
    freq: str = "MS",
) -> pd.DataFrame:
    """Aggregate detections by zone and time period.

    Parameters
    ----------
    detections : geopandas.GeoDataFrame
        Output from detect_vessels() — needs geometry + date columns
    zones : dict
        {"zone_name": (lon_min, lat_min, lon_max, lat_max)}
    freq : str
        Pandas frequency: "MS" (monthly), "W" (weekly), "D" (daily)

    Returns
    -------
    pd.DataFrame
        Indexed by period, one column per zone (+ "total")
    """
    if detections is None or len(detections) == 0:
        return pd.DataFrame()

    df = detections.copy()

    # Assign zones
    if zones:
        df["zone"] = _assign_zones(df, zones)
    else:
        df["zone"] = "all"

    # Parse dates if needed
    if "date" in df.columns:
        df["period"] = pd.to_datetime(df["date"], format="%Y%m", errors="coerce")
    elif "scene_index" in df.columns:
        df["period"] = df["scene_index"]  # fallback to scene index
    else:
        df["period"] = pd.Timestamp.now()

    # Group by period × zone
    result = df.groupby([pd.Grouper(key="period", freq=freq), "zone"]).size()
    result = result.unstack(fill_value=0)

    # Add total
    result["total"] = result.sum(axis=1)

    return result


def _assign_zones(df, zones):
    """Assign zone name to each detection based on lat/lon."""
    zone_names = []
    for _, row in df.iterrows():
        lon, lat = row.geometry.x, row.geometry.y
        assigned = "other"
        for name, (lon_min, lat_min, lon_max, lat_max) in zones.items():
            if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
                assigned = name
                break
        zone_names.append(assigned)
    return zone_names
