"""Integration test: full end-to-end pipeline on demo data."""
import numpy as np
import pytest
import strait


def test_full_pipeline():
    """Complete workflow: Cutout → prepare → detect → aggregate → validate."""
    # 1. Create cutout
    cutout = strait.Cutout(
        module="demo",
        x=slice(103.4, 104.6),
        y=slice(1.0, 1.6),
        time=slice("2021-01", "2021-06"),
    )

    # 2. Prepare (generates synthetic scenes)
    cutout.prepare(n_scenes=3)
    assert len(cutout._scenes) == 3

    # 3. Detect vessels
    detections = cutout.detect(method="trimmed_cfar")
    assert len(detections) > 0
    assert "geometry" in detections.columns
    assert "date" in detections.columns

    # 4. Aggregate by zone
    zones = strait.Zones.singapore_strait()
    monthly = cutout.aggregate(detections, zones=zones)
    assert len(monthly) > 0
    assert "total" in monthly.columns

    # 5. Compare methods
    det_classic = cutout.detect(method="cfar")
    det_trimmed = cutout.detect(method="trimmed_cfar")
    # Trimmed should find at least as many
    assert len(det_trimmed) >= len(det_classic)

    print(f"\nPipeline results:")
    print(f"  Scenes processed: {len(cutout._scenes)}")
    print(f"  Detections (trimmed): {len(det_trimmed)}")
    print(f"  Detections (classic): {len(det_classic)}")
    print(f"  Monthly aggregates: {len(monthly)} periods")
    print(f"  Zones with data: {[c for c in monthly.columns if c != 'total']}")


def test_validate_against_ais():
    """Validate SAR detections against AIS ground truth."""
    cutout = strait.Cutout(module="demo", time=slice("2021-01", "2021-03"))
    cutout.prepare(n_scenes=1)
    detections = cutout.detect()

    # Synthetic AIS vessels near some detections
    ais = [
        {"lat": float(d.geometry.y), "lon": float(d.geometry.x),
         "name": "MATCHED_VESSEL", "sog": 0.0}
        for _, d in detections.head(5).iterrows()
    ]

    result = cutout.validate(detections=detections, ais_vessels=ais, threshold_m=100)
    assert "precision" in result
    assert "recall" in result
    assert result["matched_sar"] > 0  # at least the 5 we placed should match
