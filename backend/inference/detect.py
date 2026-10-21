"""YOLO Object Detector Module.

Wraps the Ultralytics YOLO model for inference, handling:
- Model loading from specified weights or default models
- Inference on CPU or GPU with confidence and IoU thresholding
- Normalizing bounding box coordinates (0.0 to 1.0) and pixel mapping
- Latency measurement in milliseconds
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from ultralytics import YOLO

from config import Config

logger = logging.getLogger(__name__)


class YOLODetector:
    """Thread-safe wrapper around Ultralytics YOLO model for object detection."""

    def __init__(
        self, 
        model_path: Optional[str] = None, 
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ):
        self.model_path = model_path or Config.MODEL_PATH
        self.conf_threshold = conf_threshold if conf_threshold is not None else Config.CONFIDENCE_THRESHOLD
        self.iou_threshold = iou_threshold if iou_threshold is not None else Config.IOU_THRESHOLD
        self._lock = threading.Lock()
        self.model: Optional[YOLO] = None
        self.resolved_model_path: Optional[Path] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _determine_status(self, path: Path) -> Tuple[str, bool]:
        name_lower = path.name.lower()
        if "shelf_v1" in name_lower:
            return "shelf_v1 (trained)", True
        elif "sku_stage1" in name_lower or "sku" in name_lower:
            return "sku_stage1 (trained on products)", True
        else:
            return "pretrained, not trained on this project", False

    def _load_model(self):
        """Load YOLO model weights from local path or fallback."""
        try:
            p = Path(self.model_path)
            if not p.is_absolute():
                p = Config.BACKEND_DIR / self.model_path

            # Auto-download if MODEL_URL provided and file missing
            if not p.exists() and Config.MODEL_URL:
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

            # If specified path does not exist, check available alternatives in models/
            if not p.exists():
                logger.warning(f"Model weights not found at requested path: {p}")
                candidates = [
                    Config.MODELS_DIR / "shelf_v1.pt",
                    Config.MODELS_DIR / "sku_stage1.pt",
                    Config.MODELS_DIR / "yolov8n.pt",
                    Path("yolov8n.pt")
                ]
                for cand in candidates:
                    if cand.exists():
                        p = cand
                        logger.info(f"Using alternative model found at: {p}")
                        break

            self.resolved_model_path = p
            logger.info(f"Loading YOLO model from: {p} onto device={self.device}...")
            self.model = YOLO(str(p))
            logger.info(f"YOLO model loaded successfully. Classes: {self.model.names}")

            # Warm-up inference
            try:
                dummy = np.zeros((640, 640, 3), dtype=np.uint8)
                self.model.predict(source=dummy, conf=0.3, verbose=False, device=self.device)
            except Exception as e:
                logger.warning(f"Warmup on {self.device} failed ({e}), falling back to cpu")
                self.device = "cpu"
                dummy = np.zeros((640, 640, 3), dtype=np.uint8)
                self.model.predict(source=dummy, conf=0.3, verbose=False, device="cpu")

        except Exception as e:
            logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")
            try:
                self.resolved_model_path = Path("yolov8n.pt")
                self.model = YOLO("yolov8n.pt")
            except Exception as ex:
                logger.critical(f"Critical error loading fallback YOLO: {ex}")
                self.model = None

    def get_model_info(self) -> Dict[str, Any]:
        """Return metadata about current model, classes, device, and thresholds."""
        with self._lock:
            model_name = self.resolved_model_path.name if self.resolved_model_path else "unknown"
            status, is_trained = self._determine_status(self.resolved_model_path) if self.resolved_model_path else ("unknown", False)
            
            class_dict = {}
            if self.model and hasattr(self.model, "names"):
                class_dict = {int(k): str(v) for k, v in self.model.names.items()}

            device_str = "cpu"
            vram_mb = None
            if torch.cuda.is_available() and self.device == "cuda":
                device_str = f"cuda ({torch.cuda.get_device_name(0)})"
                vram_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1)

            return {
                "model_name": model_name,
                "model_path": str(self.resolved_model_path) if self.resolved_model_path else str(self.model_path),
                "model_status": status,
                "is_trained": is_trained,
                "class_names": class_dict,
                "confidence_threshold": self.conf_threshold,
                "iou_threshold": self.iou_threshold,
                "imgsz": 640,
                "device": device_str,
                "vram_allocated_mb": vram_mb
            }

    def set_thresholds(self, conf: Optional[float] = None, iou: Optional[float] = None):
        """Update detection thresholds at runtime."""
        with self._lock:
            if conf is not None:
                self.conf_threshold = max(0.01, min(1.0, float(conf)))
            if iou is not None:
                self.iou_threshold = max(0.01, min(1.0, float(iou)))

    def detect(
        self, 
        frame: np.ndarray, 
        conf: Optional[float] = None,
        iou: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Run YOLO inference on a single frame.

        Args:
            frame: BGR image numpy array.
            conf: Optional override for confidence threshold.
            iou: Optional override for IoU threshold.

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
        iou_thresh = iou if iou is not None else self.iou_threshold
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
                    iou=iou_thresh,
                    verbose=False,
                    device=self.device
                )
            except Exception as e:
                logger.error(f"Inference error on device {self.device}: {e}. Falling back to cpu...")
                try:
                    self.device = "cpu"
                    results = self.model.predict(
                        source=inf_frame,
                        conf=threshold,
                        iou=iou_thresh,
                        verbose=False,
                        device="cpu"
                    )
                except Exception as ex2:
                    logger.error(f"CPU fallback inference failed: {ex2}")
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
            px1 = max(0.0, min(float(px1), float(inf_w)))
            py1 = max(0.0, min(float(py1), float(inf_h)))
            px2 = max(0.0, min(float(px2), float(inf_w)))
            py2 = max(0.0, min(float(py2), float(inf_h)))

            nx1 = round(px1 / inf_w, 4)
            ny1 = round(py1 / inf_h, 4)
            nx2 = round(px2 / inf_w, 4)
            ny2 = round(py2 / inf_h, 4)

            cx = round((nx1 + nx2) / 2.0, 4)
            cy = round((ny1 + ny2) / 2.0, 4)

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
