"""ESP32-CAM Push Mode Camera Source.

Receives photos pushed directly by the ESP32-CAM via POST /ingest-photo.
Maintains a thread-safe frame buffer for consumption by the monitoring pipeline.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

from camera.base import CameraSource

logger = logging.getLogger(__name__)


class ESP32PushSource(CameraSource):
    """Camera source fed asynchronously by incoming HTTP POST snapshots."""

    def __init__(self):
        self._lock = threading.Lock()
        self.cached_frame_bytes: Optional[bytes] = None
        self.last_push_time: float = 0.0
        self.camera_id: str = "esp32_push_unidentified"
        self.total_received: int = 0
        self.last_received_size: int = 0

    def receive_photo(self, jpeg_bytes: bytes, camera_id: str = "esp32_push") -> bool:
        """Called by Flask endpoint POST /ingest-photo when a valid image arrives."""
        with self._lock:
            if not jpeg_bytes:
                return False
            self.cached_frame_bytes = jpeg_bytes
            self.last_push_time = time.time()
            self.camera_id = camera_id
            self.total_received += 1
            self.last_received_size = len(jpeg_bytes)
            return True

    def get_photo(self) -> Tuple[Optional[bytes], float, str, Dict[str, Any]]:
        with self._lock:
            now = time.time()
            is_stale = (now - self.last_push_time) > 30.0 if self.last_push_time > 0 else True
            metadata = {
                "simulated": False,
                "source_type": "esp32_push",
                "camera_id": self.camera_id,
                "total_received": self.total_received,
                "last_push_time": self.last_push_time,
                "last_size_bytes": self.last_received_size,
                "is_stale": is_stale
            }
            return self.cached_frame_bytes, self.last_push_time or now, self.camera_id, metadata

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            return {
                "source_type": "esp32_push",
                "simulated": False,
                "camera_id": self.camera_id,
                "total_received": self.total_received,
                "last_push_time": self.last_push_time,
                "seconds_since_last_push": round(now - self.last_push_time, 1) if self.last_push_time > 0 else None,
                "is_active": (now - self.last_push_time) < 15.0 if self.last_push_time > 0 else False
            }
