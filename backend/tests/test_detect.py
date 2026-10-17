"""Unit tests for YOLO detection wrapper."""

import sys
from pathlib import Path
import pytest
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from inference.detect import YOLODetector


def test_yolo_detector_initialization():
    """Verify YOLODetector initializes without error."""
    detector = YOLODetector()
    assert detector.model is not None


def test_yolo_detector_empty_frame():
    """Verify detector handles empty/invalid frames gracefully."""
    detector = YOLODetector()
    dets, latency = detector.detect(None)
    assert dets == []
    assert latency == 0.0

    empty_arr = np.zeros((0, 0, 3), dtype=np.uint8)
    dets, latency = detector.detect(empty_arr)
    assert dets == []


def test_yolo_detector_inference():
    """Verify inference runs on a synthetic frame and returns normalized coordinates."""
    detector = YOLODetector()
    # Create a 480x640 test frame
    frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    
    detections, latency = detector.detect(frame, conf=0.1)
    assert isinstance(detections, list)
    assert latency >= 0.0

    # If any detections, verify normalized coordinate structure
    for d in detections:
        assert "box" in d
        assert "center" in d
        assert "confidence" in d
        assert "class_name" in d
        x1, y1, x2, y2 = d["box"]
        assert 0.0 <= x1 <= 1.0
        assert 0.0 <= y1 <= 1.0
        assert 0.0 <= x2 <= 1.0
        assert 0.0 <= y2 <= 1.0
