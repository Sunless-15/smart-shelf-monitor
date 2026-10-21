"""Automated Dataset Collector for ESP32-CAM.

Saves a photo every N seconds into dataset/raw_esp32/ for model fine-tuning.
Real shelf photos from the physical camera account for real sensor noise, lens distortion,
and ambient store reflections.

Usage:
    python backend/tools/collect_images.py --ip 192.168.1.50 --count 300 --interval 3.0
"""

import argparse
import sys
import time
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "dataset" / "raw_esp32"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def collect_esp32_images(ip: str, count: int = 300, interval: float = 3.0):
    print("=" * 60)
    print(f" Collecting {count} real shelf photos from http://{ip}/capture")
    print(f" Saving to: {OUTPUT_DIR}")
    print(f" Interval: {interval} seconds")
    print(" Press Ctrl+C at any time to pause or stop.")
    print("=" * 60)

    success_count = 0
    url = f"http://{ip}/capture"

    for i in range(1, count + 1):
        try:
            t0 = time.time()
            resp = requests.get(url, timeout=5.0)
            if resp.status_code == 200 and len(resp.content) > 1000:
                filename = f"esp32_frame_{int(time.time())}_{i:04d}.jpg"
                save_path = OUTPUT_DIR / filename
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                success_count += 1
                lat = (time.time() - t0) * 1000.0
                print(f"[{i}/{count}] Saved {filename} ({len(resp.content)/1024:.1f} KB, {lat:.0f}ms)")
            else:
                print(f"[{i}/{count}] Error: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[{i}/{count}] Request failed: {e}")

        time.sleep(interval)

    print("=" * 60)
    print(f" Collection complete! Total saved: {success_count} / {count} photos.")
    print(f" Ready for labeling with labelme or Roboflow.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect training photos from ESP32-CAM")
    parser.add_argument("--ip", default="192.168.1.50", help="ESP32 IP address")
    parser.add_argument("--count", type=int, default=300, help="Number of photos to collect")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between snapshots")
    args = parser.parse_args()
    collect_esp32_images(args.ip, count=args.count, interval=args.interval)
