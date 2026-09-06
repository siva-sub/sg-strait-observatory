"""Tests for strait package — validates all use cases work end-to-end."""
import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Point

import strait
from strait import Cutout, Zones, TRIMMED_CFAR, CLASSIC_CFAR
from strait.detect import detect_vessels
from strait.aggregate import aggregate
from strait.validate import AISMatch


# ── Fixtures ──

@pytest.fixture
def demo_cutout():
    """Create a small demo cutout with synthetic data."""
    return Cutout(
        module="demo",
        x=slice(103.4, 104.6),
        y=slice(1.0, 1.6),
        time=slice("2021-01", "2021-06"),
    )


@pytest.fixture
def prepared_cutout(demo_cutout):
    demo_cutout.prepare(n_scenes=3)
    return demo_cutout


@pytest.fixture
def sample_detections():
    """Synthetic detections for aggregation testing."""
    np.random.seed(42)
    n = 100
    lons = np.random.uniform(103.6, 104.4, n)
    lats = np.random.uniform(1.1, 1.5, n)
    dates = np.random.choice(["202101", "202102", "202103"], n)
    return gpd.GeoDataFrame(
        {"date": dates, "npix": np.random.randint(3, 10, n),
         "peak_db": np.random.uniform(-5, 15, n)},
        geometry=[Point(lo, la) for lo, la in zip(lons, lats)],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_ais():
    """Synthetic AIS vessels for validation testing."""
    return [
        {"lat": 1.25, "lon": 103.90, "name": "TEST TANKER", "sog": 0.0, "type": 80},
        {"lat": 1.22, "lon": 103.85, "name": "TEST CARGO", "sog": 0.1, "type": 70},
        {"lat": 1.28, "lon": 103.95, "name": "TEST MOVING", "sog": 8.0, "type": 70},
    ]


# ── Use Case 1: Port Activity Monitoring ──

class TestPortActivity:
    """A trade analyst monitors monthly vessel presence in port zones."""

    def test_detect_returns_geodataframe(self, prepared_cutout):
        det = prepared_cutout.detect()
        assert isinstance(det, gpd.GeoDataFrame)
        assert len(det) > 0
        assert "geometry" in det.columns
        assert "date" in det.columns
        assert "peak_db" in det.columns

    def test_aggregate_produces_monthly_counts(self, prepared_cutout):
        det = prepared_cutout.detect()
        zones = Zones.singapore_strait()
        monthly = prepared_cutout.aggregate(det, zones=zones)
        assert isinstance(monthly, pd.DataFrame)
        assert len(monthly) > 0
        assert "total" in monthly.columns

    def test_monthly_counts_are_positive(self, prepared_cutout):
        det = prepared_cutout.detect()
        zones = Zones.singapore_strait()
        monthly = prepared_cutout.aggregate(det, zones=zones)
        assert (monthly["total"] > 0).all()


# ── Use Case 2: Anchorage Congestion ──

class TestAnchorageCongestion:
    """A shipping company monitors whether anchorages are congested."""

    def test_zone_specific_counts(self, sample_detections):
        zones = Zones.singapore_strait()
        result = aggregate(sample_detections, zones=zones)
        for zone_name in zones:
            if zone_name in result.columns:
                assert result[zone_name].sum() > 0

    def test_zone_assignment_correct(self, sample_detections):
        zones = {"test_zone": (103.8, 1.2, 104.0, 1.4)}
        result = aggregate(sample_detections, zones=zones)
        assert "test_zone" in result.columns or "other" in result.columns


# ── Use Case 3: Dark Vessel Detection ──

class TestDarkVesselDetection:
    """A maritime authority finds vessels not broadcasting AIS."""

    def test_precision_recall_computed(self, sample_detections, sample_ais):
        matcher = AISMatch()
        matcher._vessels = sample_ais
        result = matcher.match(sample_detections, threshold_m=500)
        assert "precision" in result
        assert "recall" in result
        assert 0 <= result["precision"] <= 1
        assert 0 <= result["recall"] <= 1

    def test_unmatched_detections_identified(self, sample_detections, sample_ais):
        matcher = AISMatch()
        matcher._vessels = sample_ais
        result = matcher.match(sample_detections, threshold_m=100)
        assert "unmatched_sar" in result
        assert result["unmatched_sar"] > 0  # most detections have no AIS match


# ── Use Case 4: Bunkering Activity ──

class TestBunkeringActivity:
    """A fuel trader estimates bunkering from anchored tanker counts."""

    def test_eopl_zone_populated(self, sample_detections):
        zones = Zones.singapore_strait()
        result = aggregate(sample_detections, zones=zones)
        # At least some detections should fall in a named zone
        named = [c for c in result.columns if c != "total" and c != "other"]
        total_in_zones = sum(result[c].sum() for c in named)
        assert total_in_zones > 0


# ── Use Case 5: Research/Econometrics ──

class TestResearchTimeSeries:
    """A researcher builds vessel presence time series."""

    def test_multi_month_time_series(self, sample_detections):
        zones = Zones.singapore_strait()
        ts = aggregate(sample_detections, zones=zones, freq="MS")
        assert len(ts) >= 1  # at least one period

    def test_custom_zones(self, sample_detections):
        custom = Zones.custom({"my_zone": (103.5, 1.0, 104.5, 1.6)})
        result = aggregate(sample_detections, zones=custom)
        assert isinstance(result, pd.DataFrame)


# ── Detection Algorithm Tests ──

class TestDetectionAlgorithms:
    """Both CFAR variants work correctly."""

    def test_trimmed_cfar_finds_vessels(self, prepared_cutout):
        det = prepared_cutout.detect(method="trimmed_cfar")
        assert len(det) > 0

    def test_classic_cfar_finds_vessels(self, prepared_cutout):
        det = prepared_cutout.detect(method="cfar")
        assert len(det) > 0

    def test_trimmed_finds_more_than_classic(self, prepared_cutout):
        det_trimmed = prepared_cutout.detect(method="trimmed_cfar")
        det_classic = prepared_cutout.detect(method="cfar")
        # Trimmed should find >= classic (literature says ~159% more)
        assert len(det_trimmed) >= len(det_classic)

    def test_invalid_method_raises(self, prepared_cutout):
        with pytest.raises(ValueError):
            prepared_cutout.detect(method="invalid")

    def test_detections_have_valid_coordinates(self, prepared_cutout):
        det = prepared_cutout.detect()
        lons = det.geometry.x
        lats = det.geometry.y
        assert lons.min() >= 103.4
        assert lons.max() <= 104.6
        assert lats.min() >= 1.0
        assert lats.max() <= 1.6


# ── Zone Tests ──

class TestZones:
    def test_singapore_strait_zones(self):
        zones = Zones.singapore_strait()
        assert "port_core" in zones
        assert "eastern_opl" in zones
        assert "western_opl" in zones

    def test_custom_zones(self):
        zones = Zones.custom({"test": (0, 0, 1, 1)})
        assert zones["test"] == (0, 0, 1, 1)


# ── Cutout Tests ──

class TestCutout:
    def test_repr(self, demo_cutout):
        assert "Cutout" in repr(demo_cutout)
        assert "demo" in repr(demo_cutout)

    def test_bounds(self, demo_cutout):
        assert demo_cutout.bounds == (103.4, 1.0, 104.6, 1.6)

    def test_prepare_then_detect(self, demo_cutout):
        demo_cutout.prepare(n_scenes=2)
        det = demo_cutout.detect()
        assert len(det) > 0

    def test_detect_before_prepare_raises(self):
        c = Cutout(module="demo")
        with pytest.raises(RuntimeError):
            c.detect()

    def test_aggregate_before_detect_raises(self):
        c = Cutout(module="demo")
        with pytest.raises(RuntimeError):
            c.aggregate()


# ── Version ──

def test_version():
    assert strait.__version__ == __import__("strait").__version__  # self-consistency
    import importlib.metadata, pathlib
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = next(l.split('"')[1] for l in pyproject.read_text().splitlines() if l.startswith('version ='))
    assert strait.__version__ == declared, f"__version__ {strait.__version__} != pyproject {declared}"
