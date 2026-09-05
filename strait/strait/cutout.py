"""Cutout: spatial/temporal abstraction for satellite data (atlite-inspired).

A Cutout defines WHERE and WHEN you want data, and from WHICH source.
It handles downloading, processing, and caching — the user just calls
`prepare()` and then `detect()`.

Usage:
    cutout = strait.Cutout(
        module="sentinel1",
        x=slice(103.4, 104.6),
        y=slice(1.0, 1.6),
        time=slice("2021-01", "2026-09"),
    )
    cutout.prepare()
    detections = cutout.detect()
"""
import os
import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import geopandas as gpd
from shapely.geometry import box

logger = logging.getLogger(__name__)


class Cutout:
    """Spatiotemporal subset of satellite data for vessel detection.

    Parameters
    ----------
    module : str
        Data source. Currently: "sentinel1" (Copernicus SAR).
    x : slice
        Longitude range, e.g. slice(103.4, 104.6)
    y : slice
        Latitude range, e.g. slice(1.0, 1.6)
    time : slice
        Time range, e.g. slice("2021-01", "2026-09")
    path : str, optional
        Directory for cached data. Defaults to ~/.strait/
    """

    def __init__(
        self,
        module: str = "sentinel1",
        x: slice = slice(103.4, 104.6),
        y: slice = slice(1.0, 1.6),
        time: slice = slice("2021-01", "2026-09"),
        path: Optional[str] = None,
    ):
        self.module = module
        self.x = x
        self.y = y
        self.time = time
        self.path = Path(path) if path else Path.home() / ".strait"
        self.path.mkdir(parents=True, exist_ok=True)

        self._data = None
        self._land_mask = None
        self._detections = None

        self.bounds = (
            x.start, y.start, x.stop, y.stop  # lon_min, lat_min, lon_max, lat_max
        )
        logger.info(
            "Cutout %s: x=%.2f⟷%.2f, y=%.2f⟷%.2f, time=%s to %s",
            module, x.start, x.stop, y.start, y.stop, time.start, time.stop,
        )

    def __repr__(self):
        n_scenes = len(self._data) if self._data is not None else 0
        return (
            f'<Cutout "{self.module}" '
            f"x={self.x.start:.2f}⟷{self.x.stop:.2f}, "
            f"y={self.y.start:.2f}⟷{self.y.stop:.2f}, "
            f"time={self.time.start} to {self.time.stop} "
            f"({n_scenes} scenes)>"
        )

    @property
    def bbox(self):
        """Bounding box as shapely geometry."""
        return box(*self.bounds)

    def prepare(self, overwrite: bool = False):
        """Download and process satellite scenes for this cutout.

        This is the expensive step (downloads + calibrates + land-masks).
        Results are cached; subsequent calls are fast unless overwrite=True.
        """
        from .data.sentinel1 import prepare_sentinel1

        logger.info("Preparing cutout (downloading + processing scenes)...")
        self._data, self._land_mask = prepare_sentinel1(
            bounds=self.bounds,
            time_range=(self.time.start, self.time.stop),
            cache_dir=self.path,
            overwrite=overwrite,
        )
        logger.info("Prepared %d scenes", len(self._data))
        return self

    def detect(self, method: str = "trimmed_cfar", **kwargs):
        """Detect vessels in the prepared scenes.

        Parameters
        ----------
        method : str
            Detection method: "trimmed_cfar" (v4, recommended) or "cfar" (v3.1)
        **kwargs
            Additional arguments passed to the detector.

        Returns
        -------
        geopandas.GeoDataFrame
            One row per vessel detection with lat, lon, date, zone, npix, peak_db.
        """
        if self._data is None:
            raise RuntimeError("Call cutout.prepare() before detect()")

        from .detect import detect_vessels

        self._detections = detect_vessels(
            self._data,
            self._land_mask,
            method=method,
            bounds=self.bounds,
            **kwargs,
        )
        logger.info("Detected %d vessels", len(self._detections))
        return self._detections

    def aggregate(self, detections=None, zones=None, freq="MS"):
        """Aggregate detections by zone and time period.

        Parameters
        ----------
        detections : GeoDataFrame, optional
            Output from detect(). If None, uses self._detections.
        zones : dict or Zones
            Zone definitions: {"name": (lon_min, lat_min, lon_max, lat_max)}
        freq : str
            Pandas frequency: "MS" (monthly start), "W" (weekly), "D" (daily)

        Returns
        -------
        pandas.DataFrame
            Indexed by time, columns by zone name.
        """
        from .aggregate import aggregate

        det = detections if detections is not None else self._detections
        if det is None:
            raise RuntimeError("Call cutout.detect() before aggregate()")

        return aggregate(det, zones=zones, freq=freq)
