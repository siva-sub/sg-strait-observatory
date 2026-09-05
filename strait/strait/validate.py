"""SAR-AIS validation: match detections against AIS ground truth."""
import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from typing import Optional


class AISMatch:
    """Match SAR detections against AIS vessel positions.

    Supports multiple AIS sources:
    - "aisstream": AISStream.io WebSocket (live)
    - "aishub": AISHub.net REST API (live)
    - "file": Load from JSON/CSV file (historical)
    """

    def __init__(self, source: str = "aisstream", api_key: str = "", **kwargs):
        self.source = source
        self.api_key = api_key
        self.kwargs = kwargs
        self._vessels = None

    def load(self, path: Optional[str] = None):
        """Load AIS vessel positions from the configured source."""
        if self.source == "file" and path:
            with open(path) as f:
                data = json.load(f)
            if "vessels" in data:
                self._vessels = data["vessels"]
            else:
                self._vessels = data
        elif self.source == "aisstream":
            # For live capture, user should run capture first
            if path:
                with open(path) as f:
                    data = json.load(f)
                self._vessels = data.get("vessels", [])
        return self

    @property
    def vessels(self):
        if self._vessels is None:
            raise RuntimeError("Call load() first")
        return self._vessels

    def match(
        self,
        detections,
        threshold_m: float = 500,
    ) -> dict:
        """Match SAR detections to AIS vessels by proximity.

        Parameters
        ----------
        detections : GeoDataFrame
            Output from detect_vessels()
        threshold_m : float
            Maximum distance for a match (meters)

        Returns
        -------
        dict with keys: precision, recall, matched, unmatched_sar, unmatched_ais
        """
        with_pos = [v for v in self.vessels if v.get("lat") and v.get("lon")]
        if not with_pos or len(detections) == 0:
            return {"precision": 0, "recall": 0, "matched": 0,
                    "unmatched_sar": len(detections), "unmatched_ais": len(with_pos)}

        ais_coords = np.array([[v["lon"], v["lat"]] for v in with_pos])
        sar_coords = np.array(
            [[d.geometry.x, d.geometry.y] for _, d in detections.iterrows()]
        )

        # SAR → AIS (precision)
        tree_ais = cKDTree(ais_coords)
        dist_sar, _ = tree_ais.query(sar_coords, k=1)
        dist_sar_m = dist_sar * 111000  # degrees → meters

        # AIS → SAR (recall)
        tree_sar = cKDTree(sar_coords)
        dist_ais, _ = tree_sar.query(ais_coords, k=1)
        dist_ais_m = dist_ais * 111000

        matched_sar = int((dist_sar_m < threshold_m).sum())
        matched_ais = int((dist_ais_m < threshold_m).sum())

        return {
            "threshold_m": threshold_m,
            "n_sar": len(detections),
            "n_ais": len(with_pos),
            "matched_sar": matched_sar,
            "matched_ais": matched_ais,
            "precision": round(matched_sar / len(detections), 3) if len(detections) else 0,
            "recall": round(matched_ais / len(with_pos), 3) if len(with_pos) else 0,
            "unmatched_sar": len(detections) - matched_sar,
            "unmatched_ais": len(with_pos) - matched_ais,
        }
