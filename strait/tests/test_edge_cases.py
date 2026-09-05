"""Edge case tests — verify robustness beyond the happy path."""
import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point

from strait.detect import detect_vessels, TRIMMED_CFAR, CLASSIC_CFAR
from strait.aggregate import aggregate
from strait.validate import AISMatch


class TestDegenerateInputs:
    """Scenes that should produce zero detections without crashing."""

    def test_empty_scene(self):
        scene = np.zeros((100, 100), dtype=np.float32)
        det = detect_vessels([scene], ["202101"], np.zeros((100,100), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(100,100))
        assert len(det) == 0

    def test_all_land(self):
        scene = np.full((100, 100), 0.01, dtype=np.float32)
        det = detect_vessels([scene], ["202101"], np.ones((100,100), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(100,100))
        assert len(det) == 0

    def test_single_pixel_vessel_filtered(self):
        """Single-pixel detections are correctly rejected (min_pixels=3)."""
        scene = np.full((100, 100), 0.01, dtype=np.float32)
        scene[50, 50] = 5.0  # single pixel — should be filtered
        det = detect_vessels([scene], ["202101"], np.zeros((100,100), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(100,100))
        assert len(det) == 0  # correctly filtered as noise

    def test_realistic_vessel_blob_detected(self):
        """A 5×5 pixel vessel blob (≈185m at 37m/px) is detected."""
        scene = np.full((200, 200), 0.01, dtype=np.float32)
        scene[95:100, 95:100] = 5.0
        det = detect_vessels([scene], ["202101"], np.zeros((200,200), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(200,200))
        assert len(det) >= 1

    def test_vessel_near_land_boundary(self):
        scene = np.full((200, 200), 0.01, dtype=np.float32)
        scene[95:100, 101:106] = 5.0
        land = np.zeros((200, 200), dtype=bool)
        land[:, :100] = True
        det = detect_vessels([scene], ["202101"], land,
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(200,200))
        assert len(det) >= 1

    def test_nan_inf_pixels(self):
        scene = np.full((100, 100), 0.01, dtype=np.float32)
        scene[50, 50:55] = 5.0
        scene[10, 10] = np.nan
        scene[20, 20] = np.inf
        det = detect_vessels([scene], ["202101"], np.zeros((100,100), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(100,100))
        # Shouldn't crash; NaN/inf handled by clip

    def test_tiny_scene_10x10(self):
        scene = np.random.lognormal(-2, 0.5, (10, 10)).astype(np.float32)
        scene[5, 5] = 5.0
        det = detect_vessels([scene], ["202101"], np.zeros((10,10), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,0.1,0.1), shape=(10,10))
        # May or may not detect — just shouldn't crash


class TestDuplicateAndMultiScene:
    def test_duplicate_dates_both_processed(self):
        scene = np.full((200, 200), 0.01, dtype=np.float32)
        scene[95:100, 95:100] = 5.0
        det = detect_vessels([scene, scene], ["202101", "202101"],
                             np.zeros((200,200), dtype=bool),
                             method=TRIMMED_CFAR, bounds=(0,0,1,1), shape=(200,200))
        assert len(det) >= 2


class TestPerformance:
    def test_full_size_scene_under_60s(self):
        import time
        scene = np.random.lognormal(-2, 0.5, (1500, 2400)).astype(np.float32)
        for _ in range(50):
            r, c = np.random.randint(0, 1500), np.random.randint(0, 2400)
            scene[r:r+3, c:c+3] = 5.0
        land = np.zeros((1500, 2400), dtype=bool)
        land[:, :500] = True
        t0 = time.time()
        det = detect_vessels([scene], ["202101"], land, method=TRIMMED_CFAR,
                             bounds=(103.55,1.05,104.35,1.55), shape=(1500,2400))
        elapsed = time.time() - t0
        assert elapsed < 60, f"Took {elapsed:.0f}s"
        assert len(det) > 0


class TestEmptyAggregation:
    def test_empty_detections_aggregate(self):
        empty = gpd.GeoDataFrame(columns=["lon","lat","date","npix","peak_db"], geometry=[])
        result = aggregate(empty)
        assert isinstance(result, pd.DataFrame)

    def test_empty_detections_validate(self):
        empty = gpd.GeoDataFrame(columns=["lon","lat","date","npix","peak_db"], geometry=[])
        m = AISMatch()
        m._vessels = []
        result = m.match(empty)
        assert result["precision"] == 0


import pandas as pd
