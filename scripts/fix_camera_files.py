from pathlib import Path

CAMERA_DIR = Path(r"D:\project\smart shelf\backend\camera")

push_code = """\"\"\"ESP32-CAM Push Mode Camera Source.

Receives photos pushed directly by the ESP32-CAM via POST /ingest-photo.
Maintains a thread-safe frame buffer for consumption by the monitoring pipeline.
\"\"\"

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

from camera.base import CameraSource

logger = logging.getLogger(__name__)


class ESP32PushSource(CameraSource):
    \"\"\"Camera source fed asynchronously by incoming HTTP POST snapshots.\"\"\"

    def __init__(self):
        self._lock = threading.Lock()
        self.cached_frame_bytes: Optional[bytes] = None
        self.last_push_time: float = 0.0
        self.camera_id: str = "esp32_push_unidentified"
        self.total_received: int = 0
        self.last_received_size: int = 0

    def receive_photo(self, jpeg_bytes: bytes, camera_id: str = "esp32_push") -> bool:
        \"\"\"Called by Flask endpoint POST /ingest-photo when a valid image arrives.\"\"\"
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
"""
(CAMERA_DIR / "esp32_push.py").write_text(push_code, encoding="utf-8")

video_code = """\"\"\"Video File Camera Source.

Replays a local MP4/AVI video file, sampling one frame every 5 seconds.
\"\"\"

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
    \"\"\"Camera source sampling frames from an existing video file.\"\"\"

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
"""
(CAMERA_DIR / "video_file.py").write_text(video_code, encoding="utf-8")

mgr_code = """\"\"\"Unified Camera Manager.

Instantiates and manages the active CameraSource based on CAMERA_MODE.
Exposes a thread-safe get_photo() method and runtime switching controls.
Ensures zero changes to downstream detection, zone analysis, alert, or prediction logic.
\"\"\"

import logging
import threading
from typing import Any, Dict, Optional, Tuple

from config import Config
from camera.base import CameraSource
from camera.simulated import SimulatedSource
from camera.esp32_pull import ESP32PullSource
from camera.esp32_push import ESP32PushSource
from camera.video_file import VideoFileSource

logger = logging.getLogger(__name__)


class CameraManager:
    \"\"\"Singleton managing active camera hardware/simulation source.\"\"\"

    def __init__(self):
        self._lock = threading.Lock()
        self.mode: str = Config.CAMERA_MODE.lower()

        self.simulated_source = SimulatedSource()
        self.esp32_pull_source = ESP32PullSource()
        self.esp32_push_source = ESP32PushSource()
        self.video_file_source = VideoFileSource()

        logger.info(f"CameraManager initialized in mode: {self.mode}")

    @property
    def active_source(self) -> CameraSource:
        \"\"\"Return the current active CameraSource instance.\"\"\"
        if self.mode == "esp32_pull":
            return self.esp32_pull_source
        elif self.mode == "esp32_push":
            return self.esp32_push_source
        elif self.mode == "video_file":
            return self.video_file_source
        else:
            return self.simulated_source

    def set_mode(self, mode: str, **kwargs) -> Dict[str, Any]:
        \"\"\"Switch camera mode at runtime.\"\"\"
        mode_clean = mode.strip().lower()
        valid_modes = ("simulated", "esp32_pull", "esp32_push", "video_file")
        if mode_clean not in valid_modes:
            raise ValueError(f"Invalid camera mode '{mode}'. Expected one of {valid_modes}")

        with self._lock:
            self.mode = mode_clean
            Config.CAMERA_MODE = mode_clean

            if mode_clean == "esp32_pull" and "esp32_ip" in kwargs:
                self.esp32_pull_source.set_ip(kwargs["esp32_ip"])
            elif mode_clean == "simulated":
                if "scenario" in kwargs:
                    self.simulated_source.set_scenario(kwargs["scenario"])
                if "speed" in kwargs:
                    self.simulated_source.set_speed(float(kwargs["speed"]))

            logger.info(f"CameraManager switched mode to: {self.mode}")
            return self.get_status()

    def control_simulated(self, action: str, **kwargs) -> Dict[str, Any]:
        \"\"\"Execute playback action on the simulated camera source.\"\"\"
        action_clean = action.strip().lower()
        if action_clean in ("start", "resume"):
            self.simulated_source.resume()
        elif action_clean == "pause":
            self.simulated_source.pause()
        elif action_clean == "reset":
            self.simulated_source.reset()
        elif action_clean == "set_scenario":
            if "scenario" in kwargs:
                self.simulated_source.set_scenario(kwargs["scenario"])
        elif action_clean == "set_speed":
            if "speed" in kwargs:
                self.simulated_source.set_speed(float(kwargs["speed"]))
        else:
            raise ValueError(f"Unknown simulated control action: {action}")

        return self.simulated_source.get_status()

    def get_photo(self) -> Tuple[Optional[bytes], float, str, Dict[str, Any]]:
        \"\"\"Fetch next photo from the active source.\"\"\"
        return self.active_source.get_photo()

    def get_status(self) -> Dict[str, Any]:
        \"\"\"Return unified status dictionary for UI banners and settings.\"\"\"
        with self._lock:
            is_sim = (self.mode in ("simulated", "video_file"))
            return {
                "camera_mode": self.mode,
                "is_simulated": is_sim,
                "badge_text": (
                    f"DEMO MODE: simulated camera (scenario: {self.simulated_source.scenario_name})"
                    if self.mode == "simulated"
                    else (
                        "DEMO MODE: simulated video file"
                        if self.mode == "video_file"
                        else f"LIVE CAMERA: ESP32-CAM ({getattr(self.active_source, 'esp32_ip', self.mode)})"
                    )
                ),
                "badge_color": "warning" if is_sim else "success",
                "source_status": self.active_source.get_status(),
                "simulated_details": self.simulated_source.get_status()
            }


camera_manager = CameraManager()
"""
(CAMERA_DIR / "manager.py").write_text(mgr_code, encoding="utf-8")

init_code = """\"\"\"ShelfSense Camera Abstraction Package.\"\"\"

from camera.base import CameraSource
from camera.simulated import SimulatedSource
from camera.esp32_pull import ESP32PullSource
from camera.esp32_push import ESP32PushSource
from camera.video_file import VideoFileSource
from camera.manager import camera_manager, CameraManager

__all__ = [
    "CameraSource",
    "SimulatedSource",
    "ESP32PullSource",
    "ESP32PushSource",
    "VideoFileSource",
    "CameraManager",
    "camera_manager",
]
"""
(CAMERA_DIR / "__init__.py").write_text(init_code, encoding="utf-8")
print("All camera files written cleanly.")
