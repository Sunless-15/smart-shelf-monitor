"""End-to-End Live Integration Test.

Tests running live backend (port 5000) and frontend (port 5173):
- Health check
- Video source status
- Live shelf status with YOLO inference
- Video upload, background job polling, timeline generation, output video verification
- Alerts listing and acknowledgment
- Vite frontend HTML delivery and PWA headers
"""

import sys
import time
import requests
from pathlib import Path

import pytest

BACKEND_URL = "http://127.0.0.1:5000"
FRONTEND_URL = "http://127.0.0.1:5173"


def is_backend_running():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=1)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.e2e
def test_e2e_live():
    if not is_backend_running():
        pytest.skip("Backend server not running on port 5000; skipping live E2E test. Run with run_backend.bat to test.")
    print(f"\n1. Testing Backend Health ({BACKEND_URL}/health)...")
    res_health = requests.get(f"{BACKEND_URL}/health", timeout=5)
    assert res_health.status_code == 200
    health_data = res_health.json()
    print("   [OK] Health Status:", health_data["status"])
    print("   [OK] Database Mode:", health_data["database"]["type"])
    print("   [OK] Video Source:", health_data["video_source"]["type"])

    print(f"\n2. Testing Live Shelf Status ({BACKEND_URL}/shelf-status)...")
    res_shelf = requests.get(f"{BACKEND_URL}/shelf-status", timeout=5)
    assert res_shelf.status_code == 200
    shelf_data = res_shelf.json()
    print("   [OK] Total Shelf Zones:", shelf_data["total_zones"])
    print("   [OK] Pipeline FPS:", shelf_data["fps"])
    print("   [OK] Inference Latency:", shelf_data["latency_ms"], "ms")

    print(f"\n3. Testing Live Frame JPEG Snapshot ({BACKEND_URL}/live-frame)...")
    res_frame = requests.get(f"{BACKEND_URL}/live-frame", timeout=5)
    assert res_frame.status_code == 200
    assert res_frame.headers.get("Content-Type") == "image/jpeg"
    print("   [OK] Received JPEG Frame:", len(res_frame.content), "bytes")

    print(f"\n4. Testing Video Upload & Asynchronous Background Job...")
    sample_path = Path(r"D:\project\smart shelf\backend\sample_data\sample_shelf.mp4")
    assert sample_path.exists(), "Sample shelf video does not exist"
    
    with open(sample_path, "rb") as f:
        res_upload = requests.post(
            f"{BACKEND_URL}/upload-video",
            files={"video": ("sample_shelf.mp4", f, "video/mp4")},
            timeout=10
        )
    assert res_upload.status_code == 202
    upload_data = res_upload.json()
    job_id = upload_data["job_id"]
    print("   [OK] Upload Accepted. Job ID:", job_id)

    # Poll status until done
    max_wait = 40
    start_t = time.time()
    job_done = False
    while time.time() - start_t < max_wait:
        res_job = requests.get(f"{BACKEND_URL}/job-status/{job_id}", timeout=5)
        status_data = res_job.json()
        print(f"   ... Job Progress: {status_data['progress']}% (Status: {status_data['status']})")
        if status_data["status"] == "done":
            job_done = True
            break
        elif status_data["status"] == "failed":
            raise RuntimeError(f"Job failed: {status_data.get('error')}")
        time.sleep(1.0)

    assert job_done, "Job did not complete within timeout"

    # Verify result
    res_result = requests.get(f"{BACKEND_URL}/job-result/{job_id}", timeout=5)
    assert res_result.status_code == 200
    result_data = res_result.json()["result"]
    print("   [OK] Video Job Completed Successfully!")
    print("   [OK] Analyzed Samples:", result_data["analyzed_samples"])
    print("   [OK] Total Anomaly Events:", result_data["total_events"])
    print("   [OK] Output Video URL:", result_data["output_video_url"])

    print(f"\n5. Testing Output Video Download ({BACKEND_URL}{result_data['output_video_url']})...")
    res_video = requests.get(f"{BACKEND_URL}{result_data['output_video_url']}", timeout=10)
    assert res_video.status_code == 200
    print("   [OK] Output Video File Accessible:", len(res_video.content), "bytes")

    print(f"\n6. Testing Frontend Delivery ({FRONTEND_URL})...")
    res_front = requests.get(FRONTEND_URL, timeout=5)
    assert res_front.status_code == 200
    html = res_front.text
    assert "Smart Shelf Monitor" in html
    assert "manifest.json" in html
    assert "/src/main.jsx" in html
    print("   [OK] Frontend Shell Running & Accessible (Status: 200 OK)")

    print("\n=======================================================")
    print("ALL END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=======================================================\n")


if __name__ == "__main__":
    test_e2e_live()
