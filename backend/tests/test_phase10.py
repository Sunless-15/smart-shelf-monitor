"""Unit and Integration Tests for Phase 10:

- Dynamic YOLO Model Info & Runtime Threshold Configuration
- Two-Class (product, empty_slot) Zone Stock Logic
- Demo Studio Endpoints (/demo/samples, /demo/analyze-sample, /analyze-image)
- Camera Abstraction Layer with Interchangeable Sources
- Simulated Scenarios with Virtual Clock Timing
- 3-Photo Confirmation Resilience (customer_blocking zero false alerts)
- Gradual Depletion Alerts & Shortage Predictions
- Restocking Alert Auto-Clearing
- ESP32 Ingestion & Fake ESP32 Pull Integration Test
"""

import io
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import pytest
import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from config import Config
from db import db
from inference.detect import detector
from inference.stock import analyze_shelf_zones
from camera import camera_manager
from pipeline import MonitoringPipeline


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_headers():
    return {
        "Authorization": f"Bearer {Config.JWT_SECRET_KEY}",
        "Content-Type": "application/json"
    }


def test_model_info_and_runtime_config(client):
    """Verify /model-info returns class names from model.names and device."""
    res = client.get("/model-info")
    assert res.status_code == 200
    data = res.get_json()
    assert "model_name" in data
    assert "class_names" in data
    assert "confidence_threshold" in data
    assert "device" in data
    assert "model_status" in data

    # Test updating thresholds at runtime
    update_res = client.post(
        "/model-config",
        json={"confidence_threshold": 0.40, "iou_threshold": 0.50}
    )
    assert update_res.status_code == 200
    info_updated = client.get("/model-info").get_json()
    assert info_updated["confidence_threshold"] == 0.40
    assert info_updated["iou_threshold"] == 0.50

    # Restore default
    detector.set_thresholds(0.35, 0.45)


def test_two_class_stock_logic():
    """Verify zone evaluation logic using both product and empty_slot classes."""
    zones = [
        {
            "id": "zone_test_two_class",
            "name": "Beverage Shelf",
            "coords": {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9},
            "expected_class": "product",
            "full_count": 10,
            "low_threshold": 0.30
        }
    ]

    # Scenario 1: Healthy Shelf (8 products, 1 empty slot)
    detections_healthy = [
        {"box": [0.2 + i * 0.08, 0.3, 0.26 + i * 0.08, 0.7], "center": [0.23 + i * 0.08, 0.5], "confidence": 0.9, "class_id": 0, "class_name": "product"}
        for i in range(8)
    ]
    detections_healthy.append({
        "box": [0.85, 0.3, 0.89, 0.7], "center": [0.87, 0.5], "confidence": 0.85, "class_id": 1, "class_name": "empty_slot"
    })

    eval_healthy = analyze_shelf_zones(zones, detections_healthy)
    assert len(eval_healthy) == 1
    zh = eval_healthy[0]
    assert zh["current_count"] == 8
    assert zh["stock_percent"] == 0.8
    assert zh["state"] == "ok"
    assert zh["empty_slot_count"] == 1

    # Scenario 2: Low Stock (2 products, 4 empty slots) -> below 30% threshold
    detections_low = [
        {"box": [0.2, 0.3, 0.28, 0.7], "center": [0.24, 0.5], "confidence": 0.9, "class_id": 0, "class_name": "product"},
        {"box": [0.3, 0.3, 0.38, 0.7], "center": [0.34, 0.5], "confidence": 0.9, "class_id": 0, "class_name": "product"}
    ]
    for i in range(4):
        detections_low.append({
            "box": [0.4 + i * 0.1, 0.3, 0.48 + i * 0.1, 0.7], "center": [0.44 + i * 0.1, 0.5], "confidence": 0.88, "class_id": 1, "class_name": "empty_slot"
        })

    eval_low = analyze_shelf_zones(zones, detections_low)
    zl = eval_low[0]
    assert zl["current_count"] == 2
    assert zl["stock_percent"] == 0.2
    assert zl["state"] == "low"
    assert zl["empty_slot_count"] == 4

    # Scenario 3: Completely Empty (0 products, 8 empty slots)
    detections_empty = [
        {"box": [0.15 + i * 0.09, 0.3, 0.22 + i * 0.09, 0.7], "center": [0.18 + i * 0.09, 0.5], "confidence": 0.85, "class_id": 1, "class_name": "empty_slot"}
        for i in range(8)
    ]
    eval_empty = analyze_shelf_zones(zones, detections_empty)
    ze = eval_empty[0]
    assert ze["current_count"] == 0
    assert ze["stock_percent"] == 0.0
    assert ze["state"] == "empty"
    assert ze["empty_slot_count"] == 8


def test_demo_samples_and_analysis_endpoints(client):
    """Verify GET /demo/samples, POST /demo/analyze-sample, and POST /analyze-image."""
    samples_res = client.get("/demo/samples")
    assert samples_res.status_code == 200
    samples = samples_res.get_json()
    assert isinstance(samples, list)
    assert len(samples) > 0

    first_sample = samples[0]
    sample_id = first_sample["id"]

    analyze_res = client.post(f"/demo/analyze-sample/{sample_id}", json={"confidence": 0.35})
    assert analyze_res.status_code == 200
    res_data = analyze_res.get_json()
    assert res_data["source"] == "demo_sample"
    assert "annotated_image" in res_data
    assert "original_image" in res_data
    assert "latency_ms" in res_data
    assert "caption" in res_data
    assert "zones" in res_data
    assert "detections" in res_data

    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(test_img, "DEMO UPLOAD", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    success, enc = cv2.imencode(".jpg", test_img)
    assert success

    upload_res = client.post(
        "/analyze-image",
        data={"image": (io.BytesIO(enc.tobytes()), "test_upload.jpg")},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200
    up_data = upload_res.get_json()
    assert up_data["source"] == "demo_upload"
    assert "annotated_image" in up_data
    assert "caption" in up_data


def test_simulated_scenario_virtual_clock():
    """Verify virtual clock spaces timestamps exactly by interval (5.0s) regardless of playback speed."""
    from camera.simulated import SimulatedSource
    sim = SimulatedSource(scenario_name="gradual_depletion")
    sim.reset()
    sim.interval_seconds = 5.0
    sim.set_speed(100.0)  # 100x speed: 5.0 / 100 = 0.05s real delay

    timestamps = []
    for _ in range(5):
        frame_bytes, v_time, cam_id, meta = sim.get_photo()
        timestamps.append(v_time)
        time.sleep(0.06)

    for i in range(1, len(timestamps)):
        diff = round(timestamps[i] - timestamps[i - 1], 1)
        assert diff == 5.0, f"Virtual clock mismatch at step {i}: {diff}s instead of 5.0s"


def test_3photo_confirmation_customer_blocking():
    """Verify customer_blocking scenario: 2 bad frames DO NOT trigger an alert."""
    test_zone_id = f"zone_cb_{uuid.uuid4().hex[:6]}"
    pipe = MonitoringPipeline()

    zone_healthy = [{"zone_id": test_zone_id, "name": "Shelf A", "state": "ok", "stock_percent": 1.0, "current_count": 10, "full_count": 10}]
    zone_blocked = [{"zone_id": test_zone_id, "name": "Shelf A", "state": "empty", "stock_percent": 0.0, "current_count": 0, "full_count": 10}]

    t = 1000.0
    for _ in range(4):
        pipe._evaluate_3photo_confirmation(zone_healthy, frame_time=t, is_simulated=True)
        t += 5.0

    alerts_before = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts_before) == 0

    t5_trace = pipe._evaluate_3photo_confirmation(zone_blocked, frame_time=t, is_simulated=True)
    t += 5.0
    assert "1 of 3" in t5_trace[0]["confirmation_progress"]
    assert len(list(db.alerts.find({"zone_id": test_zone_id}))) == 0

    t6_trace = pipe._evaluate_3photo_confirmation(zone_blocked, frame_time=t, is_simulated=True)
    t += 5.0
    assert "2 of 3" in t6_trace[0]["confirmation_progress"]
    assert len(list(db.alerts.find({"zone_id": test_zone_id}))) == 0

    t7_trace = pipe._evaluate_3photo_confirmation(zone_healthy, frame_time=t, is_simulated=True)
    assert "Healthy" in t7_trace[0]["confirmation_progress"]
    alerts_after = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts_after) == 0


def test_gradual_depletion_alerts_and_restocking_reset():
    """Verify gradual depletion triggers alerts upon 3-photo confirmation and restocking auto-resolves them."""
    test_zone_id = f"zone_gd_{uuid.uuid4().hex[:6]}"
    pipe = MonitoringPipeline()

    zone_healthy = [{"zone_id": test_zone_id, "name": "Depleting Shelf", "state": "ok", "stock_percent": 1.0, "current_count": 10, "full_count": 10}]
    zone_low = [{"zone_id": test_zone_id, "name": "Depleting Shelf", "state": "low", "stock_percent": 0.2, "current_count": 2, "full_count": 10}]

    t = 2000.0
    pipe._evaluate_3photo_confirmation(zone_healthy, frame_time=t, is_simulated=True)

    for i in range(1, 4):
        t += 5.0
        trace = pipe._evaluate_3photo_confirmation(zone_low, frame_time=t, is_simulated=True)
        if i < 3:
            assert f"{i} of 3" in trace[0]["confirmation_progress"]
            assert len(list(db.alerts.find({"zone_id": test_zone_id}))) == 0
        else:
            assert "confirmed" in trace[0]["confirmation_progress"]

    alerts = list(db.alerts.find({"zone_id": test_zone_id}))
    assert len(alerts) == 1
    assert alerts[0]["type"] == "low_stock"
    assert alerts[0]["acknowledged"] is False

    for i in range(1, 4):
        t += 5.0
        pipe._evaluate_3photo_confirmation(zone_healthy, frame_time=t, is_simulated=True)

    resolved_alert = db.alerts.find_one({"zone_id": test_zone_id})
    assert resolved_alert["acknowledged"] is True
    assert resolved_alert.get("auto_resolved") is True


def test_camera_mode_switching(client):
    """Verify switching between camera modes via API."""
    res = client.post("/camera/mode", json={"mode": "video_file"})
    assert res.status_code == 200
    status = client.get("/camera/status").get_json()
    assert status["camera_mode"] == "video_file"

    res2 = client.post("/camera/mode", json={"mode": "simulated", "scenario": "gradual_depletion"})
    assert res2.status_code == 200
    status2 = client.get("/camera/status").get_json()
    assert status2["camera_mode"] == "simulated"
    assert "gradual_depletion" in status2["badge_text"]


def test_ingest_photo_push_endpoint(client):
    """Verify /ingest-photo endpoint checks X-API-Key and accepts JPEGs."""
    res_bad = client.post("/ingest-photo", headers={"X-API-Key": "wrong_key"}, data=b"fake_jpeg")
    assert res_bad.status_code == 401

    test_img = np.zeros((240, 320, 3), dtype=np.uint8)
    success, enc = cv2.imencode(".jpg", test_img)
    assert success
    jpeg_bytes = enc.tobytes()

    res_ok = client.post(
        "/ingest-photo",
        headers={"X-API-Key": Config.CAMERA_API_KEY, "X-Camera-ID": "esp32_push_test"},
        data=jpeg_bytes
    )
    assert res_ok.status_code == 200
    assert res_ok.get_json()["status"] == "ok"


class FakeESP32Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/capture":
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(img, (100, 100), (300, 400), (0, 200, 0), -1)
            success, enc = cv2.imencode(".jpg", img)
            data = enc.tobytes() if success else b""

            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/status":
            resp = json.dumps({"status": "online", "uptime_seconds": 120, "rssi": -55}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def test_fake_esp32_pull_pipeline_integration(client):
    """Start a mock ESP32 HTTP server, point camera_manager to it, and verify pipeline processes frames."""
    server = HTTPServer(("127.0.0.1", 9876), FakeESP32Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        camera_manager.set_mode("esp32_pull", esp32_ip="127.0.0.1:9876")
        camera_manager.esp32_pull_source.interval = 0.05

        jpeg_bytes, frame_time, cam_id, meta = camera_manager.get_photo()
        assert jpeg_bytes is not None
        assert len(jpeg_bytes) > 500
        assert meta["simulated"] is False
        assert "127.0.0.1:9876" in cam_id

        nparr = np.frombuffer(jpeg_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        pipe = MonitoringPipeline()
        eval_res = pipe.process_single_frame(frame, is_simulated=False)
        assert "detections" in eval_res
        assert "latency_ms" in eval_res
        assert eval_res["latency_ms"] > 0

    finally:
        server.shutdown()
        camera_manager.set_mode("simulated", scenario="gradual_depletion")
