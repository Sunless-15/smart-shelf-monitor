"""ShelfSense Camera Abstraction Package."""

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
