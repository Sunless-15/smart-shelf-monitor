"""Phase 7 Cloud-Readiness & Security Tests.

Tests:
1. Health check endpoint (public, returns 200)
2. Login endpoint: wrong password returns 401, correct password returns valid JWT
3. Route protection: accessing protected endpoint without token returns 401
4. Route protection: accessing with valid Bearer token returns 200
5. Token via query parameter: ?token=<token> returns 200
6. Ingest-frame endpoint: missing or wrong X-API-Key returns 401
7. Ingest-frame endpoint: valid X-API-Key and JPEG frame returns 200 and processes detections
8. Upload-video: rejects invalid extension (.exe, .txt) with 400
9. Path traversal protection on /outputs: ../etc/passwd rejected
"""

import io
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import cv2
import numpy as np
import pytest
from app import app
from config import Config


@pytest.fixture(autouse=True)
def enforce_auth(monkeypatch):
    """Enforce strict authentication for all Phase 7 security tests."""
    monkeypatch.setenv("DISABLE_AUTH", "false")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    res = client.post("/login", json={"password": Config.DASHBOARD_PASSWORD})
    assert res.status_code == 200
    data = res.get_json()
    assert "token" in data
    return data["token"]


def test_public_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "video_source" in data


def test_login_invalid_password(client):
    res = client.post("/login", json={"password": "wrong_password_xyz"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "Unauthorized"


def test_login_success(client):
    res = client.post("/login", json={"password": Config.DASHBOARD_PASSWORD})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "token" in data
    assert data["expires_in"] > 0


def test_protected_route_unauthorized(client):
    res = client.get("/shelf-status")
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "Unauthorized"


def test_protected_route_with_bearer_token(client, auth_token):
    res = client.get(
        "/shelf-status",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "total_zones" in data


def test_protected_route_with_query_token(client, auth_token):
    res = client.get(f"/shelf-status?token={auth_token}")
    assert res.status_code == 200


def test_ingest_frame_unauthorized(client):
    # No header
    res = client.post("/ingest-frame", data=b"fake-bytes")
    assert res.status_code == 401

    # Wrong header
    res = client.post(
        "/ingest-frame",
        headers={"X-API-Key": "wrong_key"},
        data=b"fake-bytes"
    )
    assert res.status_code == 401


def test_ingest_frame_success(client):
    # Generate a test image in memory
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "TEST FRAME", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    jpeg_bytes = encoded.tobytes()

    res = client.post(
        "/ingest-frame",
        headers={
            "X-API-Key": Config.AGENT_API_KEY,
            "X-Camera-ID": "test_cam_1",
            "Content-Type": "image/jpeg"
        },
        data=jpeg_bytes
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["camera_id"] == "test_cam_1"
    assert data["width"] == 640
    assert data["height"] == 480


def test_upload_video_invalid_format(client, auth_token):
    data = {
        "video": (io.BytesIO(b"not a video"), "script.exe")
    }
    res = client.post(
        "/upload-video",
        headers={"Authorization": f"Bearer {auth_token}"},
        content_type="multipart/form-data",
        data=data
    )
    assert res.status_code == 400
    assert "Invalid video file format" in res.get_json()["message"]


def test_outputs_path_traversal_protection(client, auth_token):
    res = client.get(
        "/outputs/../../etc/passwd",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code in (404, 403)
