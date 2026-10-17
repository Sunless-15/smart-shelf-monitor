"""Unit tests for stock counting, zone occupancy, and misplaced item detection."""

import sys
from pathlib import Path
import pytest
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from inference.stock import is_point_in_zone, analyze_shelf_zones, annotate_frame


def test_is_point_in_zone():
    coords = {"x1": 0.1, "y1": 0.1, "x2": 0.5, "y2": 0.5}
    # Center inside
    assert is_point_in_zone([0.3, 0.3], coords) is True
    # Boundary points
    assert is_point_in_zone([0.1, 0.1], coords) is True
    assert is_point_in_zone([0.5, 0.5], coords) is True
    # Outside points
    assert is_point_in_zone([0.05, 0.3], coords) is False
    assert is_point_in_zone([0.3, 0.6], coords) is False


def test_analyze_shelf_zones_empty():
    """Verify that a zone with 0 detections is marked as 'empty' (occupancy fallback)."""
    zones = [
        {
            "id": "z1",
            "name": "Zone 1",
            "expected_class": "bottle",
            "full_count": 5,
            "low_threshold": 0.4,
            "coords": {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9}
        }
    ]
    detections = []  # No items detected

    results = analyze_shelf_zones(zones, detections)
    assert len(results) == 1
    r = results[0]
    assert r["current_count"] == 0
    assert r["stock_percent"] == 0.0
    assert r["state"] == "empty"
    assert r["is_empty"] is True
    assert r["misplaced_count"] == 0


def test_analyze_shelf_zones_low_and_ok():
    """Verify low stock and ok state transitions based on threshold."""
    zones = [
        {
            "id": "z1",
            "name": "Beverage Shelf",
            "expected_class": "bottle",
            "full_count": 5,
            "low_threshold": 0.35,  # 35% -> 1 item = 20% (low), 2 items = 40% (ok)
            "coords": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
        }
    ]

    # Test Low Stock: 1 bottle (20% <= 35%)
    det_low = [
        {"center": [0.3, 0.3], "class_name": "bottle", "confidence": 0.9, "pixel_box": [10, 10, 50, 50]}
    ]
    res_low = analyze_shelf_zones(zones, det_low)
    assert res_low[0]["current_count"] == 1
    assert res_low[0]["stock_percent"] == 0.2
    assert res_low[0]["state"] == "low"
    assert res_low[0]["is_low"] is True

    # Test OK Stock: 3 bottles (60% > 35%)
    det_ok = [
        {"center": [0.2, 0.2], "class_name": "bottle", "confidence": 0.9, "pixel_box": [10, 10, 50, 50]},
        {"center": [0.4, 0.4], "class_name": "bottle", "confidence": 0.85, "pixel_box": [60, 60, 100, 100]},
        {"center": [0.6, 0.6], "class_name": "bottle", "confidence": 0.88, "pixel_box": [110, 110, 150, 150]},
    ]
    res_ok = analyze_shelf_zones(zones, det_ok)
    assert res_ok[0]["current_count"] == 3
    assert res_ok[0]["stock_percent"] == 0.6
    assert res_ok[0]["state"] == "ok"
    assert res_ok[0]["is_ok"] is True


def test_analyze_shelf_zones_misplaced():
    """Verify misplaced product detection when an item of a different class is in the zone."""
    zones = [
        {
            "id": "z_mug",
            "name": "Mug Shelf",
            "expected_class": "cup",
            "full_count": 4,
            "low_threshold": 0.3,
            "coords": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
        }
    ]

    # Inside zone: 2 cups (matching) + 1 bottle (misplaced!)
    detections = [
        {"center": [0.2, 0.2], "class_name": "cup", "confidence": 0.9, "pixel_box": [10, 10, 50, 50]},
        {"center": [0.4, 0.4], "class_name": "cup", "confidence": 0.9, "pixel_box": [60, 60, 100, 100]},
        {"center": [0.7, 0.7], "class_name": "bottle", "confidence": 0.82, "pixel_box": [110, 110, 150, 150]},
    ]

    results = analyze_shelf_zones(zones, detections)
    r = results[0]
    assert r["current_count"] == 2
    assert r["misplaced_count"] == 1
    assert len(r["misplaced_items"]) == 1
    assert r["misplaced_items"][0]["class_name"] == "bottle"


def test_annotate_frame():
    """Verify frame annotation draws cleanly without error."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    zones = [
        {
            "id": "z1",
            "name": "Shelf 1",
            "expected_class": "bottle",
            "full_count": 5,
            "low_threshold": 0.35,
            "coords": {"x1": 0.1, "y1": 0.1, "x2": 0.5, "y2": 0.5}
        }
    ]
    detections = [
        {"center": [0.3, 0.3], "class_name": "bottle", "confidence": 0.9, "pixel_box": [100, 100, 150, 200]}
    ]
    evals = analyze_shelf_zones(zones, detections)
    annotated = annotate_frame(frame, evals, detections)
    
    assert annotated.shape == (480, 640, 3)
    # Check that drawing modified the frame pixels
    assert np.any(annotated > 0)
