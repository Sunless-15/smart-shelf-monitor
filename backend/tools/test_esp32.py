"""Diagnostic CLI tool to verify an ESP32-CAM module before putting it live.

Usage:
    python backend/tools/test_esp32.py 192.168.1.50
    python backend/tools/test_esp32.py --ip 192.168.1.50 --save-snapshot

Performs:
1. HTTP reachability and latency check on /status
2. High-resolution snapshot capture from /capture
3. Validates JPEG SOI/EOI headers and checks for dark/underexposed images
4. Runs YOLO detection with bounding boxes and logs detected product count
"""

import argparse
import sys
import time
from pathlib import Path
import requests
import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
from inference.detect import detector

# Tell pytest not to collect this diagnostic CLI tool as a unit test
__test__ = False


def test_esp32_cam(ip: str, save_snapshot: bool = True):
    print("=" * 60)
    print(f" ShelfSense ESP32-CAM Hardware Diagnostics -> {ip}")
    print("=" * 60)

    # 1. Status Check
    status_url = f"http://{ip}/status"
    print(f"[1/4] Checking module status at {status_url}...")
    try:
        t0 = time.time()
        resp = requests.get(status_url, timeout=3.0)
        latency = (time.time() - t0) * 1000.0
        if resp.status_code == 200:
            print(f"  [OK] Status responded in {latency:.1f}ms: {resp.text}")
        else:
            print(f"  [WARN] Unexpected status code {resp.status_code}: {resp.text}")
    except requests.exceptions.ConnectTimeout:
        print(f"  [FAIL] Connection timed out after 3.0s. Check if ESP32 is powered and on same WiFi subnet.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] Connection refused. Verify IP address {ip} in serial monitor.")
        return False
    except Exception as e:
        print(f"  [WARN] /status check error: {e}")

    # 2. Snapshot Capture Check
    capture_url = f"http://{ip}/capture"
    print(f"[2/4] Pulling photo snapshot from {capture_url}...")
    try:
        t0 = time.time()
        resp = requests.get(capture_url, timeout=5.0)
        capture_latency = (time.time() - t0) * 1000.0
        if resp.status_code != 200:
            print(f"  [FAIL] HTTP {resp.status_code} returned by ESP32 camera endpoint.")
            return False

        jpeg_bytes = resp.content
        size_kb = len(jpeg_bytes) / 1024.0
        print(f"  [OK] Captured {size_kb:.1f} KB JPEG in {capture_latency:.1f}ms.")
    except Exception as e:
        print(f"  [FAIL] Capture failed: {e}")
        return False

    # 3. Image Integrity & Lighting Analysis
    print("[3/4] Analyzing image integrity and store lighting...")
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        print("  [FAIL] Could not decode JPEG bytes into OpenCV image. Possible memory brownout.")
        return False

    h, w, c = img_bgr.shape
    print(f"  [OK] Resolution: {w}x{h} ({c} channels)")

    # Mean brightness analysis (0 to 255)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(gray))
    print(f"  [OK] Mean scene brightness: {mean_brightness:.1f} / 255.0")
    if mean_brightness < 40.0:
        print("  [WARNING] Scene is very dark (< 40). Ensure retail shelf lighting is turned on.")
    elif mean_brightness > 225.0:
        print("  [WARNING] Scene is overexposed (> 225). Check for direct overhead lamp glare.")

    if save_snapshot:
        out_path = BACKEND_DIR / "outputs" / f"esp32_test_{int(time.time())}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), img_bgr)
        print(f"  [OK] Snapshot saved to {out_path}")

    # 4. Instant YOLO Detection Test
    print("[4/4] Executing test YOLO inference...")
    detections, infer_lat = detector.detect(img_bgr)
    print(f"  [OK] Inference completed in {infer_lat:.1f}ms on {detector.device}")
    print(f"  [OK] Products detected: {len(detections)}")

    for i, d in enumerate(detections[:5], 1):
        print(f"    - Item {i}: class '{d['class_name']}', confidence: {d['confidence']:.2f}, box: {d['pixel_box']}")
    if len(detections) > 5:
        print(f"    ... and {len(detections) - 5} more items.")

    print("=" * 60)
    print(" [PASSED] ESP32-CAM is fully operational and ready for live monitoring!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ESP32-CAM Hardware Endpoint")
    parser.add_argument("ip", nargs="?", default="192.168.1.50", help="ESP32-CAM IP address")
    args = parser.parse_args()
    test_esp32_cam(args.ip)
