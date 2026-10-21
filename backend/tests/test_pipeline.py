"""Unit tests for Live Monitoring Pipeline and alert deduplication."""

import sys
import time
import uuid
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pipeline import MonitoringPipeline
from db import db


def test_pipeline_alert_deduplication():
    """Verify that alerts are deduplicated and not spammed on every frame."""
    pipeline = MonitoringPipeline()
    pipeline.alert_cooldown_seconds = 10.0  # 10s cooldown for testing

    # Use unique zone ID for isolation
    test_zone_id = f"test_zone_dedup_{uuid.uuid4().hex[:8]}"

    # Fake evaluated zone (Empty)
    zone_empty = [
        {
            "zone_id": test_zone_id,
            "name": "Test Snack Shelf",
            "state": "empty",
            "stock_percent": 0.0,
            "current_count": 0,
            "full_count": 5,
            "misplaced_count": 0,
            "expected_class": "bottle"
        }
    ]

    now = 1000.0
    # First frame -> should generate alert
    pipeline._handle_alerts(zone_empty, now=now)
    alerts_1 = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts_1) == 1
    assert alerts_1[0]["type"] == "empty_shelf"

    # Second frame 1 second later (same state) -> MUST NOT duplicate alert!
    pipeline._handle_alerts(zone_empty, now=now + 1.0)
    alerts_2 = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts_2) == 1  # Still 1, deduplicated!

    # Cooldown expires 15 seconds later -> can re-alert
    pipeline._handle_alerts(zone_empty, now=now + 15.0)
    alerts_3 = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts_3) == 2


def test_pipeline_misplaced_alert():
    """Verify alert generation for misplaced products."""
    pipeline = MonitoringPipeline()
    pipeline.alert_cooldown_seconds = 60.0

    test_zone_id = f"test_zone_misplaced_{uuid.uuid4().hex[:8]}"

    zone_misplaced = [
        {
            "zone_id": test_zone_id,
            "name": "Coffee Cups",
            "state": "ok",
            "stock_percent": 0.8,
            "current_count": 4,
            "full_count": 5,
            "misplaced_count": 1,
            "expected_class": "cup",
            "misplaced_items": [{"class_name": "bottle"}]
        }
    ]

    now = 2000.0
    pipeline._handle_alerts(zone_misplaced, now=now)
    alerts = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts) == 1
    assert alerts[0]["type"] == "misplaced_item"
    assert "bottle" in alerts[0]["message"]


def test_pipeline_start_stop():
    """Verify background pipeline starts, processes frames, and stops gracefully."""
    pipeline = MonitoringPipeline()
    pipeline.start()
    assert pipeline.is_running() is True

    # Allow it to process frames (wait up to 4s)
    t0 = time.time()
    while time.time() - t0 < 4.0:
        if pipeline.processed_frames >= 1:
            break
        time.sleep(0.2)

    status = pipeline.get_status()
    assert status["is_running"] is True
    assert status["processed_frames"] >= 1

    # Check JPEG generation
    jpeg = pipeline.get_latest_annotated_jpeg()
    assert jpeg is not None
    assert len(jpeg) > 1000

    pipeline.stop()
    assert pipeline.is_running() is False
