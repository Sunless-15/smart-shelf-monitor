"""YOLO Detection Wrapper for Smart Shelf Monitoring System.

Wraps Ultralytics YOLOv8 inference, converts outputs into normalized coordinates,
and reports inference latency.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from ultralytics import YOLO

from config import Config

logger = logging.getLogger(__name__)


class YOLODetector:
    """Wrapper around YOLO model for object detection."""

    def __init__(self, model_path: Optional[str] = None, conf_threshold: Optional[float] = None):
        self.model_path = model_path or Config.MODEL_PATH
        self.conf_threshold = conf_threshold if conf_threshold is not None else Config.CONFIDENCE_THRESHOLD
        self._lock = threading.Lock()
        self.model: Optional[YOLO] = None
        self._load_model()

    def _load_model(self):
        """Load YOLO model weights from local path or default."""
        try:
            p = Path(self.model_path)
            if not p.is_absolute():
                p = Config.BACKEND_DIR / self.model_path

            if not p.exists():
                if Config.MODEL_URL:
                    try:
                        logger.info(f"Downloading model weights from MODEL_URL: {Config.MODEL_URL}...")
                        import requests
                        p.parent.mkdir(parents=True, exist_ok=True)
                        resp = requests.get(Config.MODEL_URL, stream=True, timeout=60)
                        if resp.status_code == 200:
                            with open(p, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            logger.info(f"Model weights downloaded successfully to {p}")
                    except Exception as err:
                        logger.warning(f"Could not download model from MODEL_URL: {err}")

            if not p.exists():
                fallback_pt = Config.MODELS_DIR / "yolov8n.pt"
                if fallback_pt.exists():
                    p = fallback_pt
                else:
                    p = Path("yolov8n.pt")

            logger.info(f"Loading YOLO model from: {p}")
            self.model = YOLO(str(p))
            logger.info("YOLO model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")
            # Try loading default yolov8n
            try:
                self.model = YOLO("yolov8n.pt")
            except Exception as ex:
                logger.critical(f"Critical error loading fallback YOLO: {ex}")
                self.model = None

    def detect(self, frame: np.ndarray, conf: Optional[float] = None) -> Tuple[List[Dict[str, Any]], float]:
        """Run YOLO inference on a single frame.

        Args:
            frame: BGR image numpy array.
            conf: Optional override for confidence threshold.

        Returns:
            Tuple of:
            - List of detection dictionaries:
                {
                    "box": [x1, y1, x2, y2],        # normalized (0.0 - 1.0)
                    "pixel_box": [px1, py1, px2, py2],
                    "center": [cx, cy],             # normalized (0.0 - 1.0)
                    "confidence": float,
                    "class_id": int,
                    "class_name": str
                }
            - Inference latency in milliseconds.
        """
        if frame is None or frame.size == 0 or self.model is None:
            return [], 0.0

        threshold = conf if conf is not None else self.conf_threshold
        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return [], 0.0

        # Memory optimization: resize large frames to max width before inference
        max_w = Config.INFERENCE_MAX_WIDTH
        if w > max_w:
            scale = max_w / float(w)
            inf_w = max_w
            inf_h = max(1, int(h * scale))
            import cv2
            inf_frame = cv2.resize(frame, (inf_w, inf_h), interpolation=cv2.INTER_AREA)
        else:
            inf_frame = frame
            inf_w, inf_h = w, h

        start_time = time.perf_counter()
        
        with self._lock:
            try:
                results = self.model.predict(
                    source=inf_frame,
                    conf=threshold,
                    verbose=False,
                    device="cpu"
                )
            except Exception as e:
                logger.error(f"Inference error: {e}")
                return [], 0.0

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        detections: List[Dict[str, Any]] = []

        if not results or len(results) == 0:
            return detections, latency_ms

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return detections, latency_ms

        for box in boxes:
            xyxy = box.xyxy[0].tolist()  # [px1, py1, px2, py2]
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = result.names.get(class_id, str(class_id))

            px1, py1, px2, py2 = xyxy
            # Clamp to inference frame dimensions
            px1 = max(0.0, min(float(px1), float(inf_w)))
            py1 = max(0.0, min(float(py1), float(inf_h)))
            px2 = max(0.0, min(float(px2), float(inf_w)))
            py2 = max(0.0, min(float(py2), float(inf_h)))

            # Normalized coordinates (0.0 - 1.0)
            nx1 = round(px1 / inf_w, 4)
            ny1 = round(py1 / inf_h, 4)
            nx2 = round(px2 / inf_w, 4)
            ny2 = round(py2 / inf_h, 4)

            cx = round((nx1 + nx2) / 2.0, 4)
            cy = round((ny1 + ny2) / 2.0, 4)

            # Map pixel coordinates back to original frame dimensions
            orig_px1 = int(nx1 * w)
            orig_py1 = int(ny1 * h)
            orig_px2 = int(nx2 * w)
            orig_py2 = int(ny2 * h)

            detections.append({
                "box": [nx1, ny1, nx2, ny2],
                "pixel_box": [orig_px1, orig_py1, orig_px2, orig_py2],
                "center": [cx, cy],
                "confidence": round(confidence, 3),
                "class_id": class_id,
                "class_name": class_name.lower().strip()
            })

        return detections, latency_ms

    def reload_model(self, new_model_path: str):
        """Reload weights if model path is updated."""
        with self._lock:
            self.model_path = new_model_path
            self._load_model()


# Global detector instance
detector = YOLODetector()
