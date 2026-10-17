"""Unit tests for Phase 3 API Endpoints: Alerts, Zones CRUD, History, Metrics, and Video Jobs."""

import io
import json
import os
import sys
import time
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from db import db
from sources import generate_synthetic_shelf_video


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_alerts_endpoints(client):
    """Verify /alerts listing and /alerts/<id>/ack."""
    # Seed a fresh alert
    alert_id = f"test_ack_alert_{int(time.time()*1000)}"
    db.alerts.insert_one({
        "id": alert_id,
        "zone_id": "zone_test",
        "zone_name": "Test Zone",
        "type": "low_stock",
        "message": "Test low stock alert",
        "severity": "warning",
        "timestamp": time.time(),
        "acknowledged": False
    })

    # 1. Fetch unacknowledged alerts
    res = client.get("/alerts?unacknowledged=true")
    assert res.status_code == 200
    data = res.get_json()
    assert "alerts" in data
    assert any(a["id"] == alert_id for a in data["alerts"])

    # 2. Acknowledge alert
    ack_res = client.post(f"/alerts/{alert_id}/ack")
    assert ack_res.status_code == 200
    ack_data = ack_res.get_json()
    assert ack_data["success"] is True

    # 3. Check it is now acknowledged
    res_after = client.get("/alerts?unacknowledged=true")
    data_after = res_after.get_json()
    assert not any(a["id"] == alert_id for a in data_after["alerts"])


def test_zones_crud(client):
    """Verify complete CRUD lifecycle on /zones."""
    # 1. List zones
    res_get = client.get("/zones")
    assert res_get.status_code == 200
    initial_zones = res_get.get_json()
    assert isinstance(initial_zones, list)

    # 2. Create zone
    new_zone_payload = {
        "name": "Phase 3 Test Zone",
        "expected_class": "bottle",
        "full_count": 8,
        "low_threshold": 0.25,
        "coords": {"x1": 0.1, "y1": 0.1, "x2": 0.4, "y2": 0.6}
    }
    res_create = client.post("/zones", json=new_zone_payload)
    assert res_create.status_code == 201
    created = res_create.get_json()
    zone_id = created.get("id") or created.get("_id")
    assert zone_id is not None
    assert created["name"] == "Phase 3 Test Zone"
    assert created["full_count"] == 8

    # 3. Update zone
    res_update = client.put(f"/zones/{zone_id}", json={"full_count": 12, "name": "Updated Test Zone"})
    assert res_update.status_code == 200
    updated = res_update.get_json()
    assert updated["full_count"] == 12
    assert updated["name"] == "Updated Test Zone"

    # 4. Delete zone
    res_delete = client.delete(f"/zones/{zone_id}")
    assert res_delete.status_code == 200
    del_data = res_delete.get_json()
    assert del_data["success"] is True

    # Confirm deletion
    res_get_again = client.get("/zones")
    assert not any((z.get("id") == zone_id or z.get("_id") == zone_id) for z in res_get_again.get_json())


def test_history_endpoint(client):
    """Verify /history endpoint returns time series records."""
    test_zone = "zone_hist_test"
    now = time.time()
    db.history.insert_one({
        "zone_id": test_zone,
        "zone_name": "History Test",
        "timestamp": now,
        "count": 4,
        "full_count": 5,
        "stock_percent": 0.8,
        "state": "ok"
    })

    res = client.get(f"/history?zone={test_zone}&hours=1")
    assert res.status_code == 200
    data = res.get_json()
    assert "history" in data
    assert len(data["history"]) >= 1
    assert data["history"][0]["zone_id"] == test_zone


def test_metrics_endpoint(client):
    """Verify /metrics returns uptime, pipeline status, and alert counts."""
    res = client.get("/metrics")
    assert res.status_code == 200
    data = res.get_json()
    assert "uptime_seconds" in data
    assert "pipeline" in data
    assert "alerts" in data
    assert "video_source" in data
    assert "database" in data


def test_upload_video_and_job_execution(client, tmp_path):
    """Verify /upload-video, /job-status, /job-result, and /outputs file serving."""
    # 1. Create a quick synthetic test video
    test_video_path = tmp_path / "upload_sample.mp4"
    generate_synthetic_shelf_video(test_video_path, num_frames=12, fps=15)
    assert test_video_path.exists()

    # 2. Upload the video
    with open(test_video_path, "rb") as f:
        res = client.post(
            "/upload-video",
            data={"video": (f, "upload_sample.mp4")},
            content_type="multipart/form-data"
        )
    assert res.status_code == 202
    upload_data = res.get_json()
    assert upload_data["success"] is True
    job_id = upload_data["job_id"]
    assert job_id is not None

    # 3. Poll job status until done (timeout 25 seconds)
    max_wait = 25
    start_wait = time.time()
    status = "queued"
    while time.time() - start_wait < max_wait:
        res_status = client.get(f"/job-status/{job_id}")
        assert res_status.status_code == 200
        status_data = res_status.get_json()
        status = status_data["status"]
        if status in ("done", "failed"):
            break
        time.sleep(0.5)

    assert status == "done", f"Job failed or timed out: {status_data}"
    assert status_data["progress"] == 100

    # 4. Check job result
    res_result = client.get(f"/job-result/{job_id}")
    assert res_result.status_code == 200
    result_data = res_result.get_json()
    assert result_data["status"] == "done"
    res_payload = result_data["result"]
    assert "output_video_url" in res_payload
    assert "analyzed_samples" in res_payload
    assert res_payload["analyzed_samples"] > 0
    assert "timeline" in res_payload

    # 5. Check video output file serving
    output_filename = res_payload["output_video_filename"]
    res_output = client.get(f"/outputs/{output_filename}")
    assert res_output.status_code == 200
    assert len(res_output.data) > 1000  # valid video bytes
