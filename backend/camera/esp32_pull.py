"""ESP32-CAM Pull Mode Camera Source.

Pulls JPEG frames from the ESP32-CAM via HTTP GET http://<ESP32_IP>/capture.
Features:
- Configurable capture interval (default 5.0 seconds).
- Robust HTTP client with configurable timeout and exponential backoff retry on failure.
- Non-blocking lock pattern: network I/O executed outside lock.
- Detailed telemetry: response time, error counts, connection status.
- Fully implemented and ready to activate as soon as hardware is flashed and connected.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

import requests

from config import Config
from camera.base import CameraSource

logger = logging.getLogger(__name__)


class ESP32PullSource(CameraSource):
    """Camera source pulling snapshots from an ESP32-CAM HTTP endpoint."""

    def __init__(self, esp32_ip: Optional[str] = None, interval: Optional[float] = None, timeout: float = 2.0):
        self.esp32_ip = esp32_ip or Config.ESP32_IP
        self.interval = interval or float(Config.CAPTURE_INTERVAL_SECONDS)
        self.timeout = timeout
        self._lock = threading.Lock()

        # Telemetry & status
        self.last_fetch_time: float = 0.0
        self.cached_frame_bytes: Optional[bytes] = None
        self.consecutive_errors: int = 0
        self.total_captures: int = 0
        self.last_latency_ms: float = 0.0
        self.last_error_message: str = ""
        self.is_connected: bool = False
        self.backoff_delay: float = 1.0

    def set_ip(self, ip: str):
        with self._lock:
            self.esp32_ip = ip.strip()
            self.consecutive_errors = 0
            self.backoff_delay = 1.0

    def get_photo(self) -> Tuple[Optional[bytes], float, str, Dict[str, Any]]:
        with self._lock:
            now = time.time()
            if (now - self.last_fetch_time) < self.interval and self.cached_frame_bytes is not None:
                return self.cached_frame_bytes, self.last_fetch_time, f"esp32_{self.esp32_ip}", self._build_metadata()
            
            ip = self.esp32_ip
            timeout = self.timeout

        if not ip:
            with self._lock:
                self.last_error_message = "ESP32_IP is not configured"
                return None, now, "esp32_unconfigured", self._build_metadata(error=self.last_error_message)

        url = f"http://{ip}/capture"
        t_start = time.time()
        try:
            resp = requests.get(url, timeout=timeout)
            fetch_latency = (time.time() - t_start) * 1000.0

            if resp.status_code == 200 and resp.content:
                content_type = resp.headers.get("Content-Type", "")
                if "image" in content_type or resp.content[:2] == b"\xff\xd8":
                    with self._lock:
                        self.cached_frame_bytes = resp.content
                        self.last_fetch_time = time.time()
                        self.total_captures += 1
                        self.consecutive_errors = 0
                        self.backoff_delay = 1.0
                        self.last_latency_ms = round(fetch_latency, 1)
                        self.last_error_message = ""
                        self.is_connected = True
                        return self.cached_frame_bytes, self.last_fetch_time, f"esp32_{ip}", self._build_metadata()
                else:
                    raise ValueError(f"Unexpected response content type: {content_type}")
            else:
                raise IOError(f"HTTP {resp.status_code} returned by ESP32 at {url}")

        except Exception as e:
            with self._lock:
                self.consecutive_errors += 1
                self.is_connected = False
                self.last_error_message = str(e)
                self.backoff_delay = min(10.0, self.backoff_delay * 1.5)
                self.last_fetch_time = time.time() + self.backoff_delay - self.interval
                return self.cached_frame_bytes, time.time(), f"esp32_{ip}", self._build_metadata(error=str(e))

    def _build_metadata(self, error: str = "") -> Dict[str, Any]:
        return {
            "simulated": False,
            "source_type": "esp32_pull",
            "esp32_ip": self.esp32_ip,
            "connected": self.is_connected,
            "latency_ms": self.last_latency_ms,
            "total_captures": self.total_captures,
            "consecutive_errors": self.consecutive_errors,
            "error": error or self.last_error_message
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "source_type": "esp32_pull",
                "simulated": False,
                "esp32_ip": self.esp32_ip,
                "interval_seconds": self.interval,
                "is_connected": self.is_connected,
                "total_captures": self.total_captures,
                "consecutive_errors": self.consecutive_errors,
                "last_latency_ms": self.last_latency_ms,
                "last_error": self.last_error_message
            }
