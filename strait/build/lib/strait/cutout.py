"""Cutout: spatial/temporal abstraction for satellite data.

Like atlite.Cutout, this defines WHERE, WHEN, and from WHICH SOURCE.
Call `prepare()` to download/process data, then `detect()` to find vessels.

Example:
    >>> import strait
    >>> cutout = strait.Cutout(
    ...     module="sentinel1",
    ...     x=slice(103.4, 104.6),
    ...     y=slice(1.0, 1.6),
    ...     time=slice("2021-01", "2026-09"),
    ... )
    >>> cutout.prepare()
    >>> detections = cutout.detect()
    >>> monthly = cutout.aggregate(detections, zones=strait.Zones.singapore_strait())

Offline mode (for testing/demos):
    >>> cutout = strait.Cutout(module="demo")  # synthetic scenes, no download
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple

import numpy as np
import geopandas as gpd

logger = logging.getLogger(__name__)


class Cutout:
    """Spatiotemporal subset of satellite data for vessel detection.

    Parameters
    ----------
    module : str
        Data source: "sentinel1" (Copernicus SAR) or "demo" (synthetic).
    x : slice
        Longitude range, e.g. slice(103.4, 104.6)
    y : slice
        Latitude range, e.g. slice(1.0, 1.6)
    time : slice
        Time range, e.g. slice("2021-01", "2026-09")
    path : str, optional
        Cache directory. Defaults to ~/.strait/
    """

    def __init__(
        self,
        module: str = "demo",
        x: slice = slice(103.4, 104.6),
        y: slice = slice(1.0, 1.6),
        time: slice = slice("2021-01", "2021-03"),
        path: Optional[str] = None,
        **kwargs,
    ):
        self.module = module
        self.x = x
        self.y = y
        self.time = time
        self.path = Path(path) if path else Path.home() / ".strait"
        self.path.mkdir(parents=True, exist_ok=True)
        self.kwargs = kwargs

        self._scenes: list = []
        self._dates: list = []
        self._land_mask: Optional[np.ndarray] = None
        self._detections: Optional[gpd.GeoDataFrame] = None
        self._shape: Tuple[int, int] = (1500, 2400)  # (rows, cols)

        self.bounds = (
            float(x.start), float(y.start), float(x.stop), float(y.stop)
        )
        logger.debug(
            "Cutout %s: x=[%.2f,%.2f] y=[%.2f,%.2f] time=[%s,%s]",
            module, x.start, x.stop, y.start, y.stop, time.start, time.stop,
        )

    def __repr__(self):
        n = len(self._scenes)
        prepared = f"({n} scenes)" if n > 0 else "(not prepared)"
        return (
            f'<Cutout "{self.module}" '
            f"x={self.x.start:.2f}⟷{self.x.stop:.2f}, "
            f"y={self.y.start:.2f}⟷{self.y.stop:.2f} "
            f"{prepared}>"
        )

    @property
    def bbox(self):
        """Bounding box as (lon_min, lat_min, lon_max, lat_max)."""
        return self.bounds

    def prepare(self, overwrite: bool = False, n_scenes: int = 6):
        """Download and process satellite scenes.

        For module="demo": generates synthetic SAR scenes (no download).
        For module="sentinel1": downloads from CDSE (requires credentials).
        """
        if self._scenes and not overwrite:
            logger.info("Using %d cached scenes", len(self._scenes))
            return self

        if self.module == "demo":
            self._prepare_demo(n_scenes)
        elif self.module == "sentinel1":
            self._prepare_sentinel1()
        else:
            raise ValueError(f"Unknown module: {self.module}")

        logger.info("Prepared %d scenes", len(self._scenes))
        return self

    def detect(self, method: str = "trimmed_cfar", preset: str = "balanced", **kwargs):
        """Detect vessels in prepared scenes.

        Parameters
        ----------
        method : str
            "trimmed_cfar" (v4, recommended) or "cfar" (v3.1)
        preset : str
            Parameter preset: "balanced" (default), "precision", or "recall".
            Optimized via AIS ground-truth grid search.
        **kwargs
            Override individual parameters (k, window, min_pixels).

        Returns
        -------
        geopandas.GeoDataFrame
            Vessel detections with geometry (Point), date, npix, peak_db.
        """
        if not self._scenes:
            raise RuntimeError("Call cutout.prepare() before detect()")

        from .detect import detect_vessels, PRESETS

        # Apply preset defaults, allow kwargs to override
        preset_params = PRESETS.get(preset, {}).copy()
        preset_params.pop("description", None)
        preset_params.update({k_: v for k_, v in kwargs.items() if k_ in ("k", "window", "min_pixels")})

        self._detections = detect_vessels(
            scenes=self._scenes,
            dates=self._dates,
            land_mask=self._land_mask,
            method=method,
            bounds=self.bounds,
            shape=self._shape,
            **preset_params,
        )
        logger.info("Detected %d vessels (preset=%s)", len(self._detections), preset)
        return self._detections

    def aggregate(
        self,
        detections: Optional[gpd.GeoDataFrame] = None,
        zones: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
        freq: str = "MS",
    ) -> "pd.DataFrame":
        """Aggregate detections by zone and time period.

        Returns a DataFrame indexed by period with one column per zone.
        """
        det = detections if detections is not None else self._detections
        if det is None:
            raise RuntimeError("Call cutout.detect() before aggregate()")

        from .aggregate import aggregate
        return aggregate(det, zones=zones, freq=freq)

    def validate(
        self,
        detections: Optional[gpd.GeoDataFrame] = None,
        ais_vessels: Optional[list] = None,
        threshold_m: float = 500,
    ) -> dict:
        """Match detections against AIS vessels (precision/recall)."""
        det = detections if detections is not None else self._detections
        if det is None:
            raise RuntimeError("Call cutout.detect() before validate()")

        from .validate import AISMatch
        matcher = AISMatch()
        matcher._vessels = ais_vessels or []
        return matcher.match(det, threshold_m=threshold_m)

    # ── Internal: data preparation ──

    def _prepare_demo(self, n_scenes: int):
        """Generate synthetic SAR scenes for testing/demos."""
        import pandas as pd
        from scipy import ndimage

        rng = np.random.default_rng(42)
        rows, cols = self._shape

        # Create a synthetic coastline (land in the west, sea in the east)
        lon_min, lat_min, lon_max, lat_max = self.bounds
        land = np.zeros((rows, cols), dtype=bool)
        # Land = west of 30% of the bbox
        land[:, :int(cols * 0.3)] = True
        # Add an island in the middle
        cy, cx = rows // 2, int(cols * 0.5)
        yy, xx = np.ogrid[:rows, :cols]
        island = (xx - cx) ** 2 + (yy - cy) ** 2 < (50) ** 2
        land |= island
        # Dilate for coastal buffer
        land = ndimage.binary_dilation(land, iterations=3)
        self._land_mask = land

        # Parse time range
        t_start = pd.Timestamp(str(self.time.start))
        t_end = pd.Timestamp(str(self.time.stop))
        months = pd.date_range(t_start, t_end, freq="MS")

        for i in range(min(n_scenes, len(months))):
            # Sea background: speckle noise around -20 dB (in linear: ~1e-2)
            sea_noise = rng.lognormal(mean=np.log(0.01), sigma=0.5, size=(rows, cols))

            # Add "vessels": bright point targets in sea areas
            scene = sea_noise.copy()
            n_vessels = rng.integers(50, 200)
            for _ in range(n_vessels):
                r = rng.integers(0, rows)
                c = rng.integers(0, cols)
                if not land[r, c]:
                    # Vessel: bright target (sigma0 ~ 1.0, i.e., ~0 dB)
                    size = rng.integers(1, 4)
                    scene[r:r+size, c:c+size] = rng.uniform(0.5, 5.0)

            self._scenes.append(scene.astype(np.float32))
            self._dates.append(months[i].strftime("%Y%m"))

        logger.info("Demo mode: %d synthetic scenes", len(self._scenes))

    def _prepare_sentinel1(self):
        """Download and process real Sentinel-1 scenes.

        Tries local cache first (faster, no credentials needed).
        Falls back to CDSE download if no cache found.
        """
        from .data.sentinel1 import prepare_sentinel1

        scenes, dates, land_mask = prepare_sentinel1(
            bounds=self.bounds,
            time_range=(str(self.time.start), str(self.time.stop)),
            cache_dir=self.path,
            shape=self._shape,
            use_local=True,
        )
        self._scenes = scenes
        self._dates = dates
        self._land_mask = land_mask
