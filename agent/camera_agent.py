"""Smart Shelf Camera Agent.

Runs on a local machine adjacent to the camera hardware (laptop webcam, demo video, or local ESP32-CAM),
captures frames every ~1-2 seconds, compresses to 640px JPEG, and pushes to the backend's
POST /ingest-frame endpoint with X-API-Key authentication.

Designed to be resilient: auto-reconnects, handles network timeouts with exponential backoff,
and never crashes on dropped Wi-Fi connections.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import requests
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CameraAgent]: %(message)s"
)
logger = logging.getLogger("camera_agent")

# Load environment
AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(AGENT_DIR / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "shelf_agent_secret_key_2026")
CAMERA_ID = os.getenv("CAMERA_ID", "shelf_camera_1")
SOURCE_TYPE = os.getenv("SOURCE_TYPE", "video").lower().strip()
SOURCE_VALUE = os.getenv("SOURCE_VALUE", "../backend/sample_data/sample_shelf.mp4")
INTERVAL_SECONDS = float(os.getenv("INTERVAL_SECONDS", "1.5"))
MAX_WIDTH = int(os.getenv("MAX_WIDTH", "640"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "70"))


class CameraCapture:
    """Manages video capture across webcam, video files, and ESP32-CAM HTTP streams."""

    def __init__(self, source_type: str, source_value: str):
        self.source_type = source_type
        self.source_value = source_value
        self.cap: Optional[cv2.VideoCapture] = None
        self._init_source()

    def _init_source(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

        logger.info(f"Connecting to video source: {self.source_type} ({self.source_value})...")
        try:
            if self.source_type == "webcam":
                try:
                    idx = int(self.source_value)
                except ValueError:
                    idx = 0
                self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(idx)

            elif self.source_type == "video":
                vpath = Path(self.source_value)
                if not vpath.is_absolute():
                    # Check relative to agent directory, then backend
                    cand1 = AGENT_DIR / vpath
                    cand2 = AGENT_DIR.parent / "backend" / "sample_data" / vpath.name
                    cand3 = AGENT_DIR.parent / vpath
                    if cand1.exists():
                        vpath = cand1
                    elif cand2.exists():
                        vpath = cand2
                    elif cand3.exists():
                        vpath = cand3
                self.cap = cv2.VideoCapture(str(vpath))

            elif self.source_type in ("stream", "esp32", "mjpeg"):
                self.cap = cv2.VideoCapture(str(self.source_value))

            else:
                logger.error(f"Unknown source type: {self.source_type}. Defaulting to webcam index 0.")
                self.cap = cv2.VideoCapture(0)

            if self.cap and self.cap.isOpened():
                logger.info(f"[OK] Video capture initialized successfully from {self.source_type}.")
            else:
                logger.warning(f"Could not open source {self.source_type} ({self.source_value}). Will retry in loop.")
        except Exception as e:
            logger.error(f"Error opening source: {e}")

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a frame, handling looping for video files and reconnects for streams."""
        if not self.cap or not self.cap.isOpened():
            self._init_source()
            if not self.cap or not self.cap.isOpened():
                return False, None

        success, frame = self.cap.read()
        if not success:
            if self.source_type == "video":
                # Looping demo video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self.cap.read()
            else:
                # Stream or webcam dropped, re-open
                self._init_source()
                return False, None

        return success, frame

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None


def run_agent():
    """Main loop capturing and pushing frames to backend."""
    logger.info("=================================================================")
    logger.info("   Smart Shelf Camera Agent Starting")
    logger.info("=================================================================")
    logger.info(f"Target Backend URL : {BACKEND_URL}/ingest-frame")
    logger.info(f"Camera ID          : {CAMERA_ID}")
    logger.info(f"Source Type        : {SOURCE_TYPE} ({SOURCE_VALUE})")
    logger.info(f"Push Interval      : {INTERVAL_SECONDS} seconds")
    logger.info(f"Max Width / Quality: {MAX_WIDTH}px / Q{JPEG_QUALITY}")
    logger.info("=================================================================\n")

    capture = CameraCapture(SOURCE_TYPE, SOURCE_VALUE)
    backoff = 1.0
    max_backoff = 15.0
    success_count = 0

    try:
        while True:
            t0 = time.time()
            success, frame = capture.read_frame()

            if not success or frame is None:
                logger.warning(f"Failed to grab frame from source. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff = min(backoff * 1.5, max_backoff)
                continue

            # Resize to MAX_WIDTH while keeping aspect ratio
            h, w = frame.shape[:2]
            if w > MAX_WIDTH:
                scale = MAX_WIDTH / float(w)
                new_w = MAX_WIDTH
                new_h = max(1, int(h * scale))
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Compress to JPEG
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            ok, encoded = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                logger.warning("Failed to encode frame to JPEG. Skipping.")
                time.sleep(INTERVAL_SECONDS)
                continue

            jpeg_bytes = encoded.tobytes()

            # Push frame to backend
            try:
                headers = {
                    "X-API-Key": AGENT_API_KEY,
                    "X-Camera-ID": CAMERA_ID,
                    "Content-Type": "image/jpeg"
                }
                res = requests.post(
                    f"{BACKEND_URL}/ingest-frame",
                    data=jpeg_bytes,
                    headers=headers,
                    timeout=8.0
                )

                if res.status_code == 200:
                    data = res.json()
                    success_count += 1
                    backoff = 1.0  # Reset backoff on success
                    logger.info(
                        f"[OK #{success_count}] Pushed frame ({frame.shape[1]}x{frame.shape[0]}, "
                        f"{len(jpeg_bytes)//1024} KB) -> Detections: {data.get('detections', 0)} | "
                        f"Items: {data.get('total_items', 0)}"
                    )
                elif res.status_code == 401:
                    logger.error(f"[AUTH ERROR] Backend rejected API key: {res.text}. Check AGENT_API_KEY.")
                    time.sleep(5.0)
                elif res.status_code == 429:
                    logger.warning("[RATE LIMIT] Backend rate limit hit. Slowing down...")
                    time.sleep(backoff)
                    backoff = min(backoff * 1.5, max_backoff)
                else:
                    logger.warning(f"[HTTP {res.status_code}] Backend response: {res.text}")
                    time.sleep(backoff)

            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"[CONN ERROR] Cannot reach backend at {BACKEND_URL}. "
                    f"Is the server waking up or running? Retrying in {backoff:.1f}s..."
                )
                time.sleep(backoff)
                backoff = min(backoff * 1.5, max_backoff)

            except requests.exceptions.Timeout:
                logger.warning(f"[TIMEOUT] Request to {BACKEND_URL} timed out. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff = min(backoff * 1.5, max_backoff)

            except Exception as ex:
                logger.error(f"[ERROR] Unexpected exception while pushing frame: {ex}")
                time.sleep(backoff)

            # Sleep remaining time to preserve cadence
            elapsed = time.time() - t0
            sleep_time = max(0.05, INTERVAL_SECONDS - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\nStopping camera agent gracefully...")
    finally:
        capture.release()
        logger.info("Camera agent stopped.")


if __name__ == "__main__":
    run_agent()
