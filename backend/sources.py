"""Pluggable Video Source Layer.

Supports interchangeable video inputs:
1. Laptop webcam (cv2.VideoCapture(0 or index))
2. Video file on disk (looped for demos and testing)
3. HTTP / MJPEG stream URL (for ESP32-CAM at http://<ip>:81/stream)
4. Built-in synthetic shelf generator when no external media is available.
"""

import abc
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
from config import Config

logger = logging.getLogger(__name__)


def generate_synthetic_shelf_video(output_path: Union[str, Path], num_frames: int = 300, fps: int = 20) -> str:
    """Generate a clean synthetic retail shelf video with bottles and cups to test detection and alerts."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    if not out.isOpened():
        # Fallback to XVID/AVI if mp4v is not supported
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        alt_path = output_path.with_suffix(".avi")
        out = cv2.VideoWriter(str(alt_path), fourcc, fps, (width, height))
        output_path = alt_path

    logger.info(f"Generating synthetic shelf demo video at {output_path} ({num_frames} frames)...")

    for f in range(num_frames):
        frame = np.full((height, width, 3), (35, 30, 30), dtype=np.uint8)  # Store wall background
        
        # Draw background store tiles
        for y in range(0, height, 40):
            cv2.line(frame, (0, y), (width, y), (45, 40, 40), 1)
        for x in range(0, width, 40):
            cv2.line(frame, (x, 0), (x, height), (45, 40, 40), 1)

        # Draw Shelf 1 (Top)
        cv2.rectangle(frame, (30, 230), (610, 245), (70, 90, 120), -1)
        cv2.rectangle(frame, (30, 245), (610, 252), (50, 65, 90), -1)
        # Shelf support brackets
        cv2.rectangle(frame, (40, 245), (55, 270), (90, 90, 90), -1)
        cv2.rectangle(frame, (585, 245), (600, 270), (90, 90, 90), -1)

        # Draw Shelf 2 (Bottom)
        cv2.rectangle(frame, (30, 440), (610, 455), (70, 90, 120), -1)
        cv2.rectangle(frame, (30, 455), (610, 462), (50, 65, 90), -1)
        cv2.rectangle(frame, (40, 455), (55, 475), (90, 90, 90), -1)
        cv2.rectangle(frame, (585, 455), (600, 475), (90, 90, 90), -1)

        # Label shelves
        cv2.putText(frame, "SHELF A (BOTTLES)", (45, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 180, 200), 1)
        cv2.putText(frame, "SHELF B (CUPS)", (370, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 180, 200), 1)
        cv2.putText(frame, "SHELF C (BEVERAGES)", (180, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 180, 200), 1)

        # Helper to draw a bottle (realistic silhouette)
        def draw_bottle(img, cx, base_y, b_width=32, b_height=85, color=(60, 170, 70), label=""):
            x1, y1 = cx - b_width // 2, base_y - b_height
            x2, y2 = cx + b_width // 2, base_y
            neck_w = b_width // 3
            neck_h = b_height // 4
            # Body
            cv2.rectangle(img, (x1, y1 + neck_h), (x2, y2), color, -1)
            cv2.rectangle(img, (x1, y1 + neck_h), (x2, y2), (255, 255, 255), 1)
            # Neck
            cv2.rectangle(img, (cx - neck_w // 2, y1), (cx + neck_w // 2, y1 + neck_h), color, -1)
            # Cap
            cv2.rectangle(img, (cx - neck_w // 2 - 2, y1 - 6), (cx + neck_w // 2 + 2, y1), (0, 0, 220), -1)
            # Label
            if label:
                cv2.putText(img, label[:3], (x1 + 4, y1 + neck_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Helper to draw a cup
        def draw_cup(img, cx, base_y, c_width=36, c_height=55, color=(200, 140, 50)):
            x1, y1 = cx - c_width // 2, base_y - c_height
            x2, y2 = cx + c_width // 2, base_y
            # Cup body
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
            # Handle
            cv2.ellipse(img, (x2 + 4, y1 + c_height // 2), (8, 14), 0, 0, 360, (255, 255, 255), 2)
            # Steam line
            cv2.circle(img, (cx, y1 - 6), 2, (200, 200, 200), -1)

        # Simulation timeline:
        # 0-80: fully stocked
        # 81-160: 2 bottles taken from Zone A
        # 161-230: 1 misplaced bottle placed in Zone B (cup zone)
        # 231-300: Zone A completely empty
        
        # Zone A Bottles (Max 4): cx at 70, 130, 190, 250
        zone_a_count = 4
        if 80 <= f < 160:
            zone_a_count = 2
        elif 160 <= f < 220:
            zone_a_count = 1
        elif f >= 220:
            zone_a_count = 0  # Empty zone

        bot_positions = [70, 130, 190, 250]
        for i in range(zone_a_count):
            draw_bottle(frame, bot_positions[i], 230, color=(60, 180, 80), label="OIL")

        # Zone B Cups (Max 4): cx at 380, 440, 500, 560
        cup_positions = [380, 440, 500, 560]
        for i in range(3 if f > 160 else 4):
            draw_cup(frame, cup_positions[i], 230, color=(220, 160, 60))
            
        # Misplaced item in Zone B between frame 150 and 260
        if 150 <= f < 260:
            # Misplaced bottle sitting in Zone B!
            draw_bottle(frame, 560, 230, color=(200, 40, 40), label="MIS")

        # Zone C (Bottom Shelf: 6 items)
        for i, cx in enumerate([100, 175, 250, 325, 400, 475]):
            draw_bottle(frame, cx, 440, b_width=38, b_height=95, color=(50, 120, 220), label="SODA")

        # Overlay timestamp
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"LIVE DEMO | {timestamp_str} | F:{f+1}/{num_frames}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        out.write(frame)

    out.release()
    logger.info(f"Generated synthetic shelf video at {output_path}")
    return str(output_path)


class BaseVideoSource(abc.ABC):
    """Abstract interface for all video sources."""

    def __init__(self, source_type: str, source_value: Any):
        self.source_type = source_type
        self.source_value = source_value
        self.is_active = False
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        self.error_message: Optional[str] = None
        self.fps = 15.0
        self.width = 640
        self.height = 480

    @abc.abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read and return next frame: (success, frame)."""
        pass

    @abc.abstractmethod
    def release(self):
        """Release underlying camera or file handle."""
        pass

    @abc.abstractmethod
    def is_opened(self) -> bool:
        """Check if source is successfully connected/opened."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Return status information for UI and health check."""
        return {
            "type": self.source_type,
            "value": str(self.source_value),
            "is_active": self.is_active,
            "is_opened": self.is_opened(),
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 1),
            "frame_count": self.frame_count,
            "error": self.error_message,
        }


class WebcamSource(BaseVideoSource):
    """Video source for local laptop/USB webcam (cv2.VideoCapture(index))."""

    def __init__(self, device_index: Union[int, str] = 0):
        try:
            self.index = int(device_index)
        except ValueError:
            self.index = 0
        super().__init__(source_type="webcam", source_value=self.index)
        self.cap: Optional[cv2.VideoCapture] = None
        self._init_camera()

    def _init_camera(self):
        try:
            # DirectShow on Windows for fastest camera initialization
            self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback to standard capture
                self.cap = cv2.VideoCapture(self.index)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
                self.is_active = True
                self.error_message = None
            else:
                self.is_active = False
                self.error_message = f"Webcam at index {self.index} could not be opened."
        except Exception as e:
            self.is_active = False
            self.error_message = f"Error opening webcam: {e}"

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap or not self.cap.isOpened():
            return False, None
        success, frame = self.cap.read()
        if success and frame is not None:
            self.last_frame = frame
            self.frame_count += 1
            return True, frame
        return False, None

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.is_active = False

    def is_opened(self) -> bool:
        return bool(self.cap and self.cap.isOpened())


class VideoFileSource(BaseVideoSource):
    """Video source for a looped video file on disk (for demos & testing)."""

    def __init__(self, file_path: str, loop: bool = True):
        # Resolve path relative to backend if needed
        p = Path(file_path)
        if not p.is_absolute():
            p = Config.BACKEND_DIR / file_path
        super().__init__(source_type="video", source_value=str(p))
        self.file_path = p
        self.loop = loop
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_read_time = 0.0
        self._init_file()

    def _init_file(self):
        # If the file does not exist, automatically generate a synthetic demo video!
        if not self.file_path.exists():
            logger.info(f"Video file {self.file_path} not found. Creating synthetic demo video...")
            generate_synthetic_shelf_video(self.file_path)

        try:
            self.cap = cv2.VideoCapture(str(self.file_path))
            if self.cap.isOpened():
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.fps = fps if (fps and fps > 0) else 20.0
                self.is_active = True
                self.error_message = None
            else:
                self.is_active = False
                self.error_message = f"Failed to open video file at {self.file_path}"
        except Exception as e:
            self.is_active = False
            self.error_message = f"Error opening video file: {e}"

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap or not self.cap.isOpened():
            return False, None

        # Pacing to maintain realistic playback FPS
        frame_interval = 1.0 / max(self.fps, 1.0)
        now = time.time()
        elapsed = now - self.last_read_time
        if elapsed < frame_interval:
            time.sleep(frame_interval - elapsed)
        self.last_read_time = time.time()

        success, frame = self.cap.read()
        if not success:
            if self.loop:
                # Loop back to frame 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self.cap.read()
            else:
                return False, None

        if success and frame is not None:
            self.last_frame = frame
            self.frame_count += 1
            return True, frame
        return False, None

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.is_active = False

    def is_opened(self) -> bool:
        return bool(self.cap and self.cap.isOpened())


class MJPEGStreamSource(BaseVideoSource):
    """Video source for an HTTP/MJPEG stream (ESP32-CAM at http://<ip>:81/stream)."""

    def __init__(self, stream_url: str):
        super().__init__(source_type="stream", source_value=stream_url)
        self.stream_url = stream_url.strip()
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_reconnect_attempt = 0.0
        self._init_stream()

    def _init_stream(self):
        try:
            self.cap = cv2.VideoCapture(self.stream_url)
            if self.cap.isOpened():
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.fps = fps if (fps and fps > 0) else 15.0
                self.is_active = True
                self.error_message = None
            else:
                self.is_active = False
                self.error_message = f"Could not connect to MJPEG stream at {self.stream_url}"
        except Exception as e:
            self.is_active = False
            self.error_message = f"Error connecting to stream: {e}"

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap or not self.cap.isOpened():
            # Attempt reconnect every 5 seconds
            now = time.time()
            if now - self.last_reconnect_attempt > 5.0:
                self.last_reconnect_attempt = now
                self._init_stream()
            return False, None

        success, frame = self.cap.read()
        if success and frame is not None:
            self.last_frame = frame
            self.frame_count += 1
            return True, frame
        else:
            self.error_message = "Stream frame dropped or connection lost."
            return False, None

    def release(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.is_active = False

    def is_opened(self) -> bool:
        return bool(self.cap and self.cap.isOpened())


class SyntheticShelfSource(BaseVideoSource):
    """Dynamic in-memory synthetic source for guaranteed zero-dependency demos."""

    def __init__(self):
        super().__init__(source_type="synthetic", source_value="internal_generator")
        self.is_active = True
        self.fps = 20.0
        self.width = 640
        self.height = 480
        self._frame_idx = 0
        self.last_read_time = 0.0

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        frame_interval = 1.0 / self.fps
        now = time.time()
        elapsed = now - self.last_read_time
        if elapsed < frame_interval:
            time.sleep(frame_interval - elapsed)
        self.last_read_time = time.time()

        frame = np.full((self.height, self.width, 3), (35, 30, 30), dtype=np.uint8)
        
        # Shelves
        cv2.rectangle(frame, (30, 230), (610, 245), (70, 90, 120), -1)
        cv2.rectangle(frame, (30, 440), (610, 455), (70, 90, 120), -1)
        
        # Draw products
        f = self._frame_idx % 300
        # Bottles in Zone A
        zone_a_count = 4 if f < 100 else (2 if f < 200 else 0)
        for i in range(zone_a_count):
            cx = 70 + i * 60
            cv2.rectangle(frame, (cx - 16, 160), (cx + 16, 230), (60, 180, 80), -1)
            cv2.rectangle(frame, (cx - 5, 140), (cx + 5, 160), (60, 180, 80), -1)
            cv2.rectangle(frame, (cx - 7, 134), (cx + 7, 140), (0, 0, 220), -1)
            
        # Cups in Zone B
        for i in range(4):
            cx = 380 + i * 60
            cv2.rectangle(frame, (cx - 18, 175), (cx + 18, 230), (220, 160, 60), -1)

        # Bottom shelf
        for i in range(6):
            cx = 100 + i * 75
            cv2.rectangle(frame, (cx - 18, 345), (cx + 18, 440), (50, 120, 220), -1)

        cv2.putText(frame, f"SYNTHETIC FEED | F:{self._frame_idx}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 200), 1)
        self._frame_idx += 1
        self.last_frame = frame
        self.frame_count += 1
        return True, frame

    def release(self):
        self.is_active = False

    def is_opened(self) -> bool:
        return self.is_active


class AgentSource(BaseVideoSource):
    """Video source receiving frames pushed from a remote camera agent via POST /ingest-frame."""

    def __init__(self):
        super().__init__(source_type="agent", source_value="remote_push")
        self.is_active = True
        self.fps = 1.0
        self.width = 640
        self.height = 480
        self.last_pushed_time = 0.0
        self.camera_id = "default"
        self._lock = threading.Lock()

    def push_frame(self, frame: np.ndarray, camera_id: str = "default"):
        with self._lock:
            self.last_frame = frame
            self.camera_id = camera_id
            self.last_pushed_time = time.time()
            self.frame_count += 1
            h, w = frame.shape[:2]
            self.width = w
            self.height = h
            self.is_active = True
            self.error_message = None

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self.last_frame is None:
                # Placeholder frame waiting for agent
                ph = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                cv2.putText(ph, "WAITING FOR CAMERA AGENT...", (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
                cv2.putText(ph, "POST /ingest-frame with X-API-Key", (90, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)
                return True, ph

            # Check if frame is stale (> 30s)
            elapsed = time.time() - self.last_pushed_time
            if elapsed > 30.0:
                frame_copy = self.last_frame.copy()
                cv2.putText(frame_copy, f"STALE FEED ({int(elapsed)}s AGO)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                return True, frame_copy

            return True, self.last_frame.copy()

    def release(self):
        self.is_active = False

    def is_opened(self) -> bool:
        return self.is_active

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            status = super().get_status()
            status["camera_id"] = self.camera_id
            status["last_pushed_ago_sec"] = round(time.time() - self.last_pushed_time, 1) if self.last_pushed_time > 0 else None
            return status


class VideoSourceManager:
    """Thread-safe singleton managing the active video source."""

    def __init__(self):
        self._lock = threading.Lock()
        self.current_source: Optional[BaseVideoSource] = None
        self._init_default_source()

    def _init_default_source(self):
        src_type = Config.DEFAULT_SOURCE_TYPE
        src_val = Config.DEFAULT_SOURCE_VALUE
        logger.info(f"Initializing default video source: {src_type} ({src_val})")
        self.set_source(src_type, src_val)

    def set_source(self, source_type: str, source_value: Any) -> Tuple[bool, str]:
        """Switch video source dynamically at runtime."""
        with self._lock:
            # Release previous source
            if self.current_source:
                try:
                    self.current_source.release()
                except Exception as e:
                    logger.warning(f"Error releasing previous source: {e}")

            source_type = str(source_type).lower().strip()
            
            try:
                if source_type == "agent":
                    source = AgentSource()
                elif source_type == "webcam":
                    source = WebcamSource(device_index=source_value)
                elif source_type == "video":
                    source = VideoFileSource(file_path=str(source_value))
                elif source_type in ("stream", "mjpeg", "esp32"):
                    source = MJPEGStreamSource(stream_url=str(source_value))
                elif source_type == "synthetic":
                    source = SyntheticShelfSource()
                else:
                    return False, f"Unknown source type: {source_type}. Valid options: agent, webcam, video, stream."

                if not source.is_opened():
                    # Fallback to synthetic if requested source fails
                    logger.warning(f"Requested source '{source_type}' failed to open ({source.error_message}). Falling back to synthetic source.")
                    fallback = SyntheticShelfSource()
                    self.current_source = fallback
                    return True, f"Source '{source_type}' could not open ({source.error_message}). Using synthetic fallback."

                self.current_source = source
                logger.info(f"Active video source switched to: {source_type} -> {source_value}")
                return True, f"Successfully switched to {source_type} source."
            except Exception as e:
                logger.error(f"Error initializing source {source_type}: {e}")
                self.current_source = SyntheticShelfSource()
                return False, f"Exception creating source: {e}"

    def push_agent_frame(self, frame: np.ndarray, camera_id: str = "default") -> bool:
        """Push a frame from an external camera agent."""
        with self._lock:
            if not isinstance(self.current_source, AgentSource):
                # Auto-switch to AgentSource when receiving agent frames
                logger.info(f"Auto-switching active video source to 'agent' upon receiving ingest frame from camera '{camera_id}'")
                agent_src = AgentSource()
                if self.current_source:
                    try:
                        self.current_source.release()
                    except Exception:
                        pass
                self.current_source = agent_src

            self.current_source.push_frame(frame, camera_id)
            return True

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Fetch next frame from current active source."""
        with self._lock:
            if not self.current_source:
                return False, None
            return self.current_source.read()

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the most recently buffered frame."""
        with self._lock:
            if self.current_source and self.current_source.last_frame is not None:
                return self.current_source.last_frame.copy()
            return None

    def get_jpeg_frame(self, frame: Optional[np.ndarray] = None) -> Optional[bytes]:
        """Encode given frame or latest frame as JPEG bytes."""
        if frame is None:
            frame = self.get_latest_frame()
        if frame is None:
            # Return placeholder black frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "NO SIGNAL", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if success:
            return encoded.tobytes()
        return None

    def get_status(self) -> Dict[str, Any]:
        """Return status of current video source."""
        with self._lock:
            if self.current_source:
                return self.current_source.get_status()
            return {
                "type": "none",
                "value": "",
                "is_active": False,
                "is_opened": False,
                "error": "No source initialized",
            }


# Global video source manager
source_manager = VideoSourceManager()
