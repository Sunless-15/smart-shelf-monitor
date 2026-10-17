"""Live Monitoring Background Pipeline.

Continuously runs in a daemon thread:
1. Grabs active frame from source_manager
2. Runs YOLO detection
3. Evaluates shelf zones (stock %, empty, low, ok, misplaced items)
4. Calculates depletion rate & time-to-depletion predictions
5. Annotates the frame and caches it in memory for live MJPEG/JPEG streams
6. Emits deduplicated alerts to database on low/empty/misplaced events
7. Records time-series history for analytics
"""

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from config import Config
from db import db, serialize_docs
from inference.detect import detector
from inference.predict import calculate_depletion_forecast
from inference.stock import analyze_shelf_zones, annotate_frame
from sources import source_manager

logger = logging.getLogger(__name__)


class MonitoringPipeline:
    """Thread-safe live monitoring pipeline."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Cached latest states
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_zone_results: List[Dict[str, Any]] = []
        self.latest_detections: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.fps: float = 0.0
        self.latency_ms: float = 0.0
        self.processed_frames: int = 0
        self.start_time: float = time.time()

        # Alert deduplication tracking
        # Key: (zone_id, alert_type) -> timestamp of last alert
        self.alert_cooldowns: Dict[tuple, float] = {}
        self.last_zone_states: Dict[str, str] = {}
        self.alert_cooldown_seconds: float = 90.0  # Cooldown between duplicate alerts

        # History recording interval (seconds)
        self.last_history_save: float = 0.0
        self.history_interval_seconds: float = 5.0

    def start(self):
        """Start the background pipeline thread."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.info("Pipeline already running.")
                return

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="PipelineThread", daemon=True)
            self._thread.start()
            logger.info("Live Monitoring Pipeline started.")

    def stop(self):
        """Stop the background pipeline thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Live Monitoring Pipeline stopped.")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set())

    def _run_loop(self):
        """Core pipeline loop running at Config.PIPELINE_FPS."""
        target_interval = 1.0 / max(0.5, Config.PIPELINE_FPS)
        last_iter_time = time.time()

        while not self._stop_event.is_set():
            loop_start = time.time()

            try:
                # 1. Grab frame from active source
                success, frame = source_manager.get_frame()
                if not success or frame is None:
                    time.sleep(0.1)
                    continue

                # 2. Run YOLO Detection
                detections, latency = detector.detect(frame)

                # 3. Retrieve defined zones from DB
                raw_zones = list(db.zones.find({}))
                zones = serialize_docs(raw_zones)

                # 4. Evaluate zones & misplaced items
                zone_evals = analyze_shelf_zones(zones, detections)

                # 5. Attach Shortage Predictions from history
                now = time.time()
                for z in zone_evals:
                    zone_id = z["zone_id"]
                    # Query recent history (last 3 hours)
                    three_hours_ago = now - (3 * 3600)
                    history_records = list(
                        db.history.find(
                            {"zone_id": zone_id, "timestamp": {"$gte": three_hours_ago}},
                            sort=[("timestamp", 1)],
                            limit=100
                        )
                    )
                    prediction = calculate_depletion_forecast(
                        history_points=history_records,
                        current_stock_percent=z["stock_percent"],
                        low_threshold=z["low_threshold"]
                    )
                    z["prediction"] = prediction

                # 6. Annotate frame
                annotated = annotate_frame(frame, zone_evals, detections)

                # 7. Update in-memory caches
                fps_calc = 1.0 / max(0.001, (time.time() - last_iter_time))
                last_iter_time = time.time()

                with self._lock:
                    self.latest_raw_frame = frame
                    self.latest_annotated_frame = annotated
                    self.latest_zone_results = zone_evals
                    self.latest_detections = detections
                    self.latency_ms = latency
                    self.fps = round(fps_calc, 1)
                    self.processed_frames += 1

                # 8. Trigger Deduplicated Alerts
                self._handle_alerts(zone_evals, now)

                # 9. Periodic History Persistence
                if now - self.last_history_save >= self.history_interval_seconds:
                    self._save_history_snapshot(zone_evals, now)
                    self.last_history_save = now

            except Exception as e:
                logger.error(f"Error in pipeline loop: {e}", exc_info=True)

            # Frame rate throttling
            elapsed = time.time() - loop_start
            sleep_duration = max(0.01, target_interval - elapsed)
            time.sleep(sleep_duration)

    def _handle_alerts(self, zone_evals: List[Dict[str, Any]], now: float):
        """Evaluate alert conditions with state-change detection and cooldown deduplication."""
        for z in zone_evals:
            zone_id = z["zone_id"]
            zone_name = z["name"]
            state = z["state"]
            prev_state = self.last_zone_states.get(zone_id)
            misplaced_count = z.get("misplaced_count", 0)

            # 1. Empty Shelf Alert
            if state == "empty":
                alert_key = (zone_id, "empty_shelf")
                last_time = self.alert_cooldowns.get(alert_key, 0.0)
                # Fire if state changed to empty OR cooldown expired
                if (prev_state != "empty") or (now - last_time > self.alert_cooldown_seconds):
                    self._create_alert(
                        zone_id=zone_id,
                        zone_name=zone_name,
                        alert_type="empty_shelf",
                        message=f"{zone_name} is completely EMPTY (0 items remaining).",
                        severity="critical",
                        timestamp=now
                    )
                    self.alert_cooldowns[alert_key] = now

            # 2. Low Stock Alert
            elif state == "low":
                alert_key = (zone_id, "low_stock")
                last_time = self.alert_cooldowns.get(alert_key, 0.0)
                if (prev_state != "low") or (now - last_time > self.alert_cooldown_seconds):
                    pct = int(z["stock_percent"] * 100)
                    self._create_alert(
                        zone_id=zone_id,
                        zone_name=zone_name,
                        alert_type="low_stock",
                        message=f"{zone_name} stock is LOW: {z['current_count']}/{z['full_count']} ({pct}%).",
                        severity="warning",
                        timestamp=now
                    )
                    self.alert_cooldowns[alert_key] = now

            # 3. Misplaced Item Alert
            if misplaced_count > 0:
                alert_key = (zone_id, "misplaced_item")
                last_time = self.alert_cooldowns.get(alert_key, 0.0)
                if now - last_time > self.alert_cooldown_seconds:
                    items_str = ", ".join(m["class_name"] for m in z.get("misplaced_items", []))
                    self._create_alert(
                        zone_id=zone_id,
                        zone_name=zone_name,
                        alert_type="misplaced_item",
                        message=f"Misplaced product ({items_str}) detected in {zone_name} (expected {z['expected_class']}).",
                        severity="info",
                        timestamp=now
                    )
                    self.alert_cooldowns[alert_key] = now

            self.last_zone_states[zone_id] = state

    def _create_alert(
        self,
        zone_id: str,
        zone_name: str,
        alert_type: str,
        message: str,
        severity: str,
        timestamp: float
    ):
        """Insert alert into database."""
        try:
            alert_doc = {
                "id": str(uuid.uuid4()),
                "zone_id": zone_id,
                "zone_name": zone_name,
                "type": alert_type,
                "message": message,
                "severity": severity,
                "timestamp": timestamp,
                "acknowledged": False
            }
            db.alerts.insert_one(alert_doc)
            logger.info(f"ALERT GENERATED: [{severity.upper()}] {message}")
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")

    def _save_history_snapshot(self, zone_evals: List[Dict[str, Any]], timestamp: float):
        """Append stock level snapshots to history collection for trend plotting."""
        try:
            for z in zone_evals:
                history_doc = {
                    "zone_id": z["zone_id"],
                    "zone_name": z["name"],
                    "timestamp": timestamp,
                    "count": z["current_count"],
                    "full_count": z["full_count"],
                    "stock_percent": z["stock_percent"],
                    "state": z["state"],
                    "misplaced_count": z.get("misplaced_count", 0),
                }
                db.history.insert_one(history_doc)
        except Exception as e:
            logger.error(f"Failed to save history snapshot: {e}")

    def process_single_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Directly process an incoming frame (e.g. from /ingest-frame)."""
        if frame is None or frame.size == 0:
            return {}

        detections, latency = detector.detect(frame)
        raw_zones = list(db.zones.find({}))
        zones = serialize_docs(raw_zones)
        zone_evals = analyze_shelf_zones(zones, detections)

        now = time.time()
        for z in zone_evals:
            zone_id = z["zone_id"]
            three_hours_ago = now - (3 * 3600)
            history_records = list(
                db.history.find(
                    {"zone_id": zone_id, "timestamp": {"$gte": three_hours_ago}},
                    sort=[("timestamp", 1)],
                    limit=100
                )
            )
            z["prediction"] = calculate_depletion_forecast(
                history_points=history_records,
                current_stock_percent=z["stock_percent"],
                low_threshold=z["low_threshold"]
            )

        annotated = annotate_frame(frame, zone_evals, detections)
        self._handle_alerts(zone_evals, now)

        if now - self.last_history_save >= self.history_interval_seconds:
            self._save_history_snapshot(zone_evals, now)
            self.last_history_save = now

        with self._lock:
            self.latest_raw_frame = frame
            self.latest_annotated_frame = annotated
            self.latest_zone_results = zone_evals
            self.latest_detections = detections
            self.latency_ms = latency
            self.processed_frames += 1

        return {
            "detections": detections,
            "latency_ms": latency,
            "zones": zone_evals,
            "total_items": sum(z.get("current_count", 0) for z in zone_evals)
        }

    def get_latest_annotated_jpeg(self) -> Optional[bytes]:
        """Encode the cached annotated frame as JPEG bytes."""
        with self._lock:
            frame = self.latest_annotated_frame
            if frame is None:
                frame = self.latest_raw_frame

        if frame is None:
            # Placeholder frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "INITIALIZING PIPELINE...", (160, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return encoded.tobytes() if success else None

    def get_status(self) -> Dict[str, Any]:
        """Return metrics and evaluated zone status for API."""
        with self._lock:
            return {
                "is_running": self.is_running(),
                "fps": self.fps,
                "latency_ms": self.latency_ms,
                "processed_frames": self.processed_frames,
                "zones": self.latest_zone_results,
                "detection_count": len(self.latest_detections),
            }


# Global monitoring pipeline instance
pipeline = MonitoringPipeline()
