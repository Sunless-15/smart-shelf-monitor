"""Simulated Camera Source with Scenario Playback and Virtual Clock.

Replays ordered JPEG image sequences from backend/demo_scenarios/<scenario_name>/.
Features:
- Virtual Clock: Each simulated photo gets a timestamp spaced exactly `interval` seconds apart
  (default 5s), preserving accurate linear regression prediction regardless of real-time playback speed.
- Playback controls: start, pause, reset, set_speed (1x, 5x, 10x), switch scenario.
- Loop control: Configurable via scenario.json.
- Full honest telemetry: Tags all outputs with simulated=True.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from camera.base import CameraSource

logger = logging.getLogger(__name__)


class SimulatedSource(CameraSource):
    """Simulated camera replaying scenario sequences with an independent virtual clock."""

    def __init__(self, scenario_name: str = "gradual_depletion", scenarios_dir: Optional[Path] = None):
        self.scenarios_dir = scenarios_dir or Config.DEMO_SCENARIOS_DIR
        self.scenario_name = scenario_name
        self._lock = threading.Lock()

        # Playback configuration
        self.interval_seconds: float = float(Config.CAPTURE_INTERVAL_SECONDS)  # default 5.0s
        self.speed_multiplier: float = 1.0  # 1.0x, 5.0x, 10.0x
        self.is_paused: bool = False
        self.loop: bool = True

        # Scenario files
        self.image_files: List[Path] = []
        self.scenario_title: str = ""
        self.scenario_description: str = ""
        self.current_index: int = 0

        # Virtual clock state
        # Initial virtual time anchors to when the scenario was initialized / reset
        self.base_virtual_time: float = time.time()
        self.virtual_step_count: int = 0
        self.last_fetch_real_time: float = 0.0
        self.cached_current_frame_bytes: Optional[bytes] = None

        self._load_scenario(self.scenario_name)

    def _load_scenario(self, name: str):
        """Load scenario metadata and list of JPEG images."""
        scenario_path = self.scenarios_dir / name
        if not scenario_path.exists():
            logger.warning(f"Scenario directory {scenario_path} not found. Searching for available scenarios...")
            available = [d.name for d in self.scenarios_dir.glob("*/") if d.is_dir()]
            if available:
                scenario_path = self.scenarios_dir / available[0]
                name = available[0]
            else:
                logger.error(f"No scenario directories found in {self.scenarios_dir}")
                self.scenario_name = name
                self.image_files = []
                return

        self.scenario_name = name
        meta_file = scenario_path / "scenario.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self.scenario_title = meta.get("title", name)
                    self.scenario_description = meta.get("description", "")
                    self.interval_seconds = float(meta.get("interval", Config.CAPTURE_INTERVAL_SECONDS))
                    self.loop = bool(meta.get("loop", True))
            except Exception as e:
                logger.warning(f"Could not parse {meta_file}: {e}")
                self.scenario_title = name
                self.scenario_description = ""
        else:
            self.scenario_title = name
            self.scenario_description = "Simulated test scenario"

        exts = ("*.jpg", "*.jpeg", "*.png")
        files = []
        for ext in exts:
            files.extend(list(scenario_path.glob(ext)))
        self.image_files = sorted(files, key=lambda p: p.name)
        self.current_index = 0
        self.virtual_step_count = 0
        self.base_virtual_time = time.time()
        self.cached_current_frame_bytes = None
        logger.info(f"Loaded scenario '{name}' ({len(self.image_files)} frames, interval={self.interval_seconds}s)")

    def set_scenario(self, name: str):
        """Switch active scenario and reset playback state."""
        with self._lock:
            self._load_scenario(name)

    def set_speed(self, multiplier: float):
        """Update playback speed multiplier (e.g. 1.0, 5.0, 10.0, 100.0)."""
        with self._lock:
            self.speed_multiplier = max(0.1, min(100.0, float(multiplier)))

    def pause(self):
        """Pause scenario progression."""
        with self._lock:
            self.is_paused = True

    def resume(self):
        """Resume scenario progression."""
        with self._lock:
            self.is_paused = False

    def reset(self):
        """Reset scenario index and virtual clock."""
        with self._lock:
            self.current_index = 0
            self.virtual_step_count = 0
            self.base_virtual_time = time.time()
            self.last_fetch_real_time = 0.0
            self.cached_current_frame_bytes = None

    def get_photo(self) -> Tuple[Optional[bytes], float, str, Dict[str, Any]]:
        """Fetch current frame according to virtual clock pacing."""
        with self._lock:
            if not self.image_files:
                return None, time.time(), f"simulated_{self.scenario_name}", {
                    "simulated": True,
                    "error": "No images in scenario"
                }

            now_real = time.time()
            real_interval_needed = self.interval_seconds / max(0.1, self.speed_multiplier)

            if not self.is_paused:
                if self.last_fetch_real_time == 0.0 or (now_real - self.last_fetch_real_time) >= real_interval_needed:
                    if self.last_fetch_real_time != 0.0:
                        self.current_index += 1
                        self.virtual_step_count += 1
                        if self.current_index >= len(self.image_files):
                            if self.loop:
                                self.current_index = 0
                            else:
                                self.current_index = len(self.image_files) - 1

                    self.last_fetch_real_time = now_real
                    img_path = self.image_files[self.current_index]
                    try:
                        with open(img_path, "rb") as f:
                            self.cached_current_frame_bytes = f.read()
                    except Exception as e:
                        logger.error(f"Error reading scenario image {img_path}: {e}")

            virtual_timestamp = self.base_virtual_time + (self.virtual_step_count * self.interval_seconds)

            metadata = {
                "simulated": True,
                "source_type": "simulated",
                "scenario": self.scenario_name,
                "scenario_title": self.scenario_title,
                "frame_index": self.current_index + 1,
                "total_frames": len(self.image_files),
                "speed_multiplier": self.speed_multiplier,
                "is_paused": self.is_paused,
                "interval_seconds": self.interval_seconds,
                "virtual_timestamp": virtual_timestamp,
                "current_file": self.image_files[self.current_index].name if self.image_files else ""
            }

            return self.cached_current_frame_bytes, virtual_timestamp, f"simulated_{self.scenario_name}", metadata

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "source_type": "simulated",
                "simulated": True,
                "scenario_name": self.scenario_name,
                "scenario_title": self.scenario_title,
                "scenario_description": self.scenario_description,
                "current_frame": self.current_index + 1 if self.image_files else 0,
                "total_frames": len(self.image_files),
                "is_paused": self.is_paused,
                "speed_multiplier": self.speed_multiplier,
                "interval_seconds": self.interval_seconds,
                "loop": self.loop,
                "available_scenarios": [d.name for d in self.scenarios_dir.glob("*/") if d.is_dir()]
            }
