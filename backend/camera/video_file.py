"""Video File Camera Source.

Replays a local MP4/AVI video file, sampling one frame every 5 seconds.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2

from config import Config
from camera.base import CameraSource

logger = logging.getLogger(__name__)


class VideoFileSource(CameraSource):
    """Camera source sampling frames from an existing video file."""

    def __init__(self, video_path: Optional[str] = None, sample_interval: float = 5.0):
        self.video_path = video_path or str(Config.DATA_DIR / "synthetic_shelf.mp4")
        self.sample_interval = sample_interval
        self._lock = threading.Lock()
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_sample_time: float = 0.0
        self.cached_jpeg_bytes: Optional[bytes] = None
        self.frame_number: int = 0
        self._open_capture()

    def _open_capture(self):
        p = Path(self.video_path)
        if not p.exists():
            p = Config.DATA_DIR / "synthetic_shelf.mp4"
        if p.exists():
            self.cap = cv2.VideoCapture(str(p))
            logger.info(f"VideoFileSource opened: {p}")
        else:
            logger.warning(f"Video file not found at {self.video_path}")
            self.cap = None

    def get_photo(self) -> Tuple[Optional[bytes], float, str, Dict[str, Any]]:
        with self._lock:
            now = time.time()
            if self.cap is None or not self.cap.isOpened():
                self._open_capture()
                if self.cap is None:
                    return None, now, "video_file", {"simulated": True, "error": "Cannot open video"}

            if (now - self.last_sample_time) >= self.sample_interval or self.cached_jpeg_bytes is None:
                ret, frame = self.cap.read()
                if not ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()

                if ret and frame is not None:
                    self.frame_number += 1
                    success, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if success:
                        self.cached_jpeg_bytes = enc.tobytes()
                        self.last_sample_time = now

            metadata = {
                "simulated": True,
                "source_type": "video_file",
                "video_path": self.video_path,
                "frame_number": self.frame_number
            }
            return self.cached_jpeg_bytes, self.last_sample_time or now, "video_file", metadata

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "source_type": "video_file",
                "simulated": True,
                "video_path": self.video_path,
                "is_open": bool(self.cap and self.cap.isOpened()),
                "frame_number": self.frame_number
            }
