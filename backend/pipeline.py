"""Live Monitoring Background Pipeline.

Continuously runs in a daemon thread:
1. Grabs active photo from camera_manager (or fallback video sources)
2. Decodes image and runs YOLO detection (products and empty_slots)
3. Evaluates shelf zones (stock %, empty, low, ok, misplaced items)
4. Executes 3-photo confirmation state machine per zone to eliminate false alerts
5. Emits deduplicated alerts when transitions are confirmed across 3 consecutive frames
6. Automatically clears alerts when restocking to healthy is confirmed
7. Calculates depletion rate & time-to-depletion predictions
8. Annotates the frame and caches it in memory
9. Records time-series history tagged with simulated=true/false
10. Maintains a live Pipeline Trace card for UI visualization
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
from camera import camera_manager
from sources import source_manager

logger = logging.getLogger(__name__)


class MonitoringPipeline:
    """Thread-safe live monitoring pipeline feeding detection, zones, alerts, and predictions."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Cached latest states
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_zone_results: List[Dict[str, Any]] = []
        self.latest_detections: List[Dict[str, Any]] = []
        self.latest_camera_id: str = "simulated"
        self.latest_is_simulated: bool = True
        self.latest_photo_timestamp: float = time.time()
        self.last_photo_received_real_time: float = time.time()

        # Pipeline trace data for presentation & UI
        self.latest_pipeline_trace: Dict[str, Any] = {
            "photo_time": time.time(),
            "camera_id": "simulated",
            "simulated": True,
            "products_found": 0,
            "empty_slots_found": 0,
            "latency_ms": 0.0,
            "summary_caption": "Pipeline initializing...",
            "zones": []
        }

        # 3-photo confirmation state tracking per zone_id:
        self.zone_confirmations: Dict[str, Dict[str, Any]] = {}

        # Alert deduplication tracking
        self.alert_cooldowns: Dict[tuple, float] = {}
        self.last_zone_states: Dict[str, str] = {}
        self.alert_cooldown_seconds: float = 90.0

        # Performance metrics
        self.fps: float = 0.0
        self.latency_ms: float = 0.0
        self.processed_frames: int = 0
        self.start_time: float = time.time()

        # History recording interval (seconds)
        self.last_history_save: float = 0.0
        self.history_interval_seconds: float = float(Config.CAPTURE_INTERVAL_SECONDS)

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
                # 1. Fetch photo from unified camera manager
                jpeg_bytes, frame_time, camera_id, meta = camera_manager.get_photo()
                is_simulated = meta.get("simulated", True)

                frame = None
                if jpeg_bytes:
                    nparr = np.frombuffer(jpeg_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    success, frame = source_manager.get_frame()
                    if not success or frame is None:
                        time.sleep(0.1)
                        continue
                    frame_time = time.time()
                    camera_id = "fallback_source"
                    is_simulated = True

                now_real = time.time()

                # 2. Run YOLO Detection
                detections, latency = detector.detect(frame)

                products_found = sum(
                    1 for d in detections 
                    if str(d.get("class_name", "")).lower() == "product" or d.get("class_id") == 0
                )
                empty_slots_found = sum(
                    1 for d in detections 
                    if str(d.get("class_name", "")).lower() in ("empty_slot", "empty") or d.get("class_id") == 1
                )

                # 3. Retrieve defined zones from DB
                raw_zones = list(db.zones.find({}))
                zones = serialize_docs(raw_zones)

                # 4. Evaluate zones & misplaced items
                zone_evals = analyze_shelf_zones(zones, detections)

                # 5. Execute 3-Photo Confirmation per zone
                trace_zones = self._evaluate_3photo_confirmation(zone_evals, frame_time, is_simulated)

                # 6. Attach Shortage Predictions from history
                three_hours_ago = frame_time - (3 * 3600)
                for z in zone_evals:
                    zone_id = z["zone_id"]
                    history_records = list(
                        db.history.find(
                            {
                                "zone_id": zone_id,
                                "timestamp": {"$gte": three_hours_ago},
                                "simulated": is_simulated
                            },
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

                # 7. Annotate frame
                annotated = annotate_frame(frame, zone_evals, detections)

                # 8. Build Summary Caption
                caption = self._build_plain_caption(zone_evals, products_found, empty_slots_found)

                # 9. Update in-memory caches and trace
                fps_calc = 1.0 / max(0.001, (now_real - last_iter_time))
                last_iter_time = now_real

                with self._lock:
                    self.latest_raw_frame = frame
                    self.latest_annotated_frame = annotated
                    self.latest_zone_results = zone_evals
                    self.latest_detections = detections
                    self.latest_camera_id = camera_id
                    self.latest_is_simulated = is_simulated
                    self.latest_photo_timestamp = frame_time
                    self.last_photo_received_real_time = now_real
                    self.latency_ms = latency
                    self.fps = round(fps_calc, 1)
                    self.processed_frames += 1

                    self.latest_pipeline_trace = {
                        "photo_time": frame_time,
                        "real_received_time": now_real,
                        "seconds_ago": round(time.time() - now_real, 1),
                        "camera_id": camera_id,
                        "simulated": is_simulated,
                        "products_found": products_found,
                        "empty_slots_found": empty_slots_found,
                        "latency_ms": latency,
                        "summary_caption": caption,
                        "zones": trace_zones
                    }

                # 10. Periodic History Persistence
                if frame_time - self.last_history_save >= self.history_interval_seconds:
                    self._save_history_snapshot(zone_evals, frame_time, is_simulated)
                    self.last_history_save = frame_time

            except Exception as e:
                logger.error(f"Error in pipeline loop: {e}", exc_info=True)

            elapsed = time.time() - loop_start
            sleep_duration = max(0.01, target_interval - elapsed)
            time.sleep(sleep_duration)

    def _evaluate_3photo_confirmation(
        self, 
        zone_evals: List[Dict[str, Any]], 
        frame_time: float, 
        is_simulated: bool
    ) -> List[Dict[str, Any]]:
        """Run 3-photo confirmation state machine for each zone."""
        trace_list = []

        for z in zone_evals:
            zone_id = z["zone_id"]
            zone_name = z["name"]
            raw_state = z["state"]  # "ok", "low", "empty"
            state_label = "Healthy" if raw_state == "ok" else ("Low" if raw_state == "low" else "Empty")

            if zone_id not in self.zone_confirmations:
                self.zone_confirmations[zone_id] = {
                    "confirmed_state": raw_state,
                    "candidate_state": raw_state,
                    "consecutive_count": 0
                }

            conf_rec = self.zone_confirmations[zone_id]
            confirmed_state = conf_rec["confirmed_state"]
            alert_fired = False

            if raw_state == confirmed_state:
                conf_rec["candidate_state"] = raw_state
                conf_rec["consecutive_count"] = 0
                progress_text = f"{state_label} (confirmed)"
            else:
                if raw_state == conf_rec["candidate_state"]:
                    conf_rec["consecutive_count"] += 1
                else:
                    conf_rec["candidate_state"] = raw_state
                    conf_rec["consecutive_count"] = 1

                count = conf_rec["consecutive_count"]
                progress_text = f"{state_label} seen {count} of 3"

                if count >= 3:
                    old_confirmed = conf_rec["confirmed_state"]
                    conf_rec["confirmed_state"] = raw_state
                    conf_rec["consecutive_count"] = 0
                    progress_text = f"{state_label} confirmed (3 of 3)"

                    self._handle_alerts([z], frame_time, is_simulated=is_simulated)
                    alert_fired = True

                    if old_confirmed in ("low", "empty") and raw_state == "ok":
                        self._resolve_zone_alerts(zone_id, frame_time)

            misplaced_count = z.get("misplaced_count", 0)
            if misplaced_count > 0:
                self._handle_alerts([z], frame_time, is_simulated=is_simulated)

            trace_list.append({
                "zone_id": zone_id,
                "zone_name": zone_name,
                "raw_state": raw_state,
                "confirmed_state": conf_rec["confirmed_state"],
                "confirmation_progress": progress_text,
                "alert_triggered": alert_fired,
                "stock_percent": int(z["stock_percent"] * 100),
                "current_count": z["current_count"],
                "full_count": z["full_count"]
            })

        return trace_list

    def _handle_alerts(self, zone_evals: List[Dict[str, Any]], now: float, is_simulated: bool = False):
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
                if (prev_state != "empty") or (now - last_time > self.alert_cooldown_seconds):
                    self._create_alert(
                        zone_id=zone_id,
                        zone_name=zone_name,
                        alert_type="empty_shelf",
                        message=f"{zone_name} is completely EMPTY (0 items remaining).",
                        severity="critical",
                        timestamp=now,
                        simulated=is_simulated
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
                        timestamp=now,
                        simulated=is_simulated
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
                        timestamp=now,
                        simulated=is_simulated
                    )
                    self.alert_cooldowns[alert_key] = now

            self.last_zone_states[zone_id] = state

    def _resolve_zone_alerts(self, zone_id: str, timestamp: float):
        """Auto-resolve pending alerts when a shelf is refilled to healthy."""
        try:
            result = db.alerts.update_many(
                {"zone_id": zone_id, "acknowledged": False},
                {"$set": {"acknowledged": True, "acknowledged_at": timestamp, "auto_resolved": True}}
            )
            if result.modified_count > 0:
                logger.info(f"Auto-resolved {result.modified_count} alerts for restocked {zone_id}")
        except Exception as e:
            logger.error(f"Error auto-resolving alerts: {e}")

    def _build_plain_caption(self, zone_evals: List[Dict[str, Any]], products_found: int, empty_slots: int) -> str:
        """Generate human-readable caption explaining the current visual state."""
        if not zone_evals:
            return f"Detection identified {products_found} products in view. No shelf zones are currently configured."

        empty_zones = [z["name"] for z in zone_evals if z["state"] == "empty"]
        low_zones = [z["name"] for z in zone_evals if z["state"] == "low"]
        misplaced = [z["name"] for z in zone_evals if z.get("misplaced_count", 0) > 0]

        parts = []
        if empty_zones:
            parts.append(f"{', '.join(empty_zones)} completely empty")
        if low_zones:
            parts.append(f"{', '.join(low_zones)} running low")
        if misplaced:
            parts.append(f"misplaced items in {', '.join(misplaced)}")

        if parts:
            status_desc = "; ".join(parts) + "."
            return f"Detection identified {products_found} products and {empty_slots} empty slots across {len(zone_evals)} zones. Action required: {status_desc}"
        else:
            return f"All {len(zone_evals)} shelf zones are adequately stocked ({products_found} products detected, {empty_slots} empty slots observed). Stock levels healthy."

    def _create_alert(
        self, 
        zone_id: str, 
        zone_name: str, 
        alert_type: str, 
        message: str, 
        severity: str, 
        timestamp: float,
        simulated: bool = False
    ):
        """Insert a deduplicated alert document into the database."""
        alert_doc = {
            "id": str(uuid.uuid4()),
            "zone_id": zone_id,
            "zone_name": zone_name,
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": timestamp,
            "acknowledged": False,
            "simulated": simulated
        }
        try:
            db.alerts.insert_one(alert_doc)
            logger.info(f"Alert generated: [{severity.upper()}] {message} (simulated={simulated})")
        except Exception as e:
            logger.error(f"Failed to insert alert into database: {e}")

    def _save_history_snapshot(self, zone_evals: List[Dict[str, Any]], timestamp: float, simulated: bool = False):
        """Persist periodic stock metrics into history collection."""
        records = []
        for z in zone_evals:
            records.append({
                "id": str(uuid.uuid4()),
                "zone_id": z["zone_id"],
                "zone_name": z["name"],
                "timestamp": timestamp,
                "current_count": z["current_count"],
                "full_count": z["full_count"],
                "stock_percent": z["stock_percent"],
                "empty_slot_count": z.get("empty_slot_count", 0),
                "empty_slot_area": z.get("empty_slot_area", 0.0),
                "state": z["state"],
                "misplaced_count": z.get("misplaced_count", 0),
                "simulated": simulated
            })
        if records:
            try:
                db.history.insert_many(records)
            except Exception as e:
                logger.error(f"Failed to save history snapshot: {e}")

    def process_single_frame(self, frame: np.ndarray, is_simulated: bool = False) -> Dict[str, Any]:
        """Directly process an incoming frame (e.g. from /ingest-frame or camera agent)."""
        if frame is None or frame.size == 0:
            return {}

        detections, latency = detector.detect(frame)
        raw_zones = list(db.zones.find({}))
        zones = serialize_docs(raw_zones)
        zone_evals = analyze_shelf_zones(zones, detections)

        now = time.time()
        three_hours_ago = now - (3 * 3600)
        for z in zone_evals:
            zone_id = z["zone_id"]
            history_records = list(
                db.history.find(
                    {"zone_id": zone_id, "timestamp": {"$gte": three_hours_ago}, "simulated": is_simulated},
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
        self._handle_alerts(zone_evals, now, is_simulated=is_simulated)

        if now - self.last_history_save >= self.history_interval_seconds:
            self._save_history_snapshot(zone_evals, now, simulated=is_simulated)
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

    def get_latest_frame_jpeg(self, annotated: bool = True) -> Optional[bytes]:
        """Encode latest cached frame to JPEG bytes."""
        with self._lock:
            frame = self.latest_annotated_frame if annotated else self.latest_raw_frame
            if frame is None:
                return None
            success, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return enc.tobytes() if success else None

    def get_latest_annotated_jpeg(self) -> Optional[bytes]:
        """Alias for backward compatibility."""
        return self.get_latest_frame_jpeg(annotated=True)

    def get_status(self) -> Dict[str, Any]:
        """Return pipeline telemetry and diagnostics."""
        with self._lock:
            return {
                "running": self.is_running(),
                "is_running": self.is_running(),
                "fps": self.fps,
                "latency_ms": self.latency_ms,
                "processed_frames": self.processed_frames,
                "uptime_seconds": round(time.time() - self.start_time, 1),
                "latest_camera_id": self.latest_camera_id,
                "latest_is_simulated": self.latest_is_simulated,
                "latest_photo_timestamp": self.latest_photo_timestamp,
                "seconds_since_last_photo": round(time.time() - self.last_photo_received_real_time, 1),
                "pipeline_trace": self.latest_pipeline_trace
            }


# Singleton pipeline instance
pipeline = MonitoringPipeline()
