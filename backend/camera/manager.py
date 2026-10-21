"""Unified Camera Manager.

Instantiates and manages the active CameraSource based on CAMERA_MODE.
Exposes a thread-safe get_photo() method and runtime switching controls.
Ensures zero changes to downstream detection, zone analysis, alert, or prediction logic.
"""

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
    """Singleton managing active camera hardware/simulation source."""

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
        """Return the current active CameraSource instance."""
        if self.mode == "esp32_pull":
            return self.esp32_pull_source
        elif self.mode == "esp32_push":
            return self.esp32_push_source
        elif self.mode == "video_file":
            return self.video_file_source
        else:
            return self.simulated_source

    def set_mode(self, mode: str, **kwargs) -> Dict[str, Any]:
        """Switch camera mode at runtime."""
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
        """Execute playback action on the simulated camera source."""
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
        """Fetch next photo from the active source."""
        return self.active_source.get_photo()

    def get_status(self) -> Dict[str, Any]:
        """Return unified status dictionary for UI banners and settings."""
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
