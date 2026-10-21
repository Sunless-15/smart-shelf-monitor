"""Intelligent Empty Shelf and Low Stock Monitoring System - Flask Backend Entry Point.

Phase 1 Core: Server skeleton, configuration, database layer with fallback,
video source abstraction layer, and health verification endpoints.
"""

import logging
import os
import time
import uuid
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from db import db, id_filter, serialize_doc, serialize_docs
from sources import source_manager
from pipeline import pipeline
from video_jobs import job_manager

import jwt
import threading
from functools import wraps

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smart_shelf_backend")

app = Flask(__name__)
# Enable CORS for all origins in development (supports localhost, 127.0.0.1, LAN, and Vercel)
CORS(app, resources={r"/*": {"origins": "*" if not Config.IS_CLOUD else Config.CORS_ORIGINS}})

# Clean up old upload/output files on startup
Config.cleanup_old_files()

# Start live monitoring pipeline in background
pipeline.start()

START_TIME = time.time()


class SimpleRateLimiter:
    """Thread-safe in-memory rate limiter per IP/key."""
    def __init__(self):
        self._records = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: float) -> bool:
        now = time.time()
        with self._lock:
            timestamps = self._records.get(key, [])
            timestamps = [t for t in timestamps if now - t < window_seconds]
            if len(timestamps) >= max_requests:
                self._records[key] = timestamps
                return False
            timestamps.append(now)
            self._records[key] = timestamps
            return True


rate_limiter = SimpleRateLimiter()


def require_auth(f):
    """Decorator to require JWT authentication header or token query parameter."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow disabling auth explicitly via environment for headless/internal tests if specified
        if os.getenv("DISABLE_AUTH", "false").lower() in ("true", "1", "yes"):
            return f(*args, **kwargs)

        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "token" in request.args:
            token = request.args.get("token")

        if not token:
            return jsonify({
                "error": "Unauthorized",
                "message": "Authentication token required. Please login."
            }), 401

        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({
                "error": "Unauthorized",
                "message": "Token has expired. Please login again."
            }), 401
        except Exception as e:
            return jsonify({
                "error": "Unauthorized",
                "message": f"Invalid authentication token: {e}"
            }), 401

        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["POST"])
def login():
    """Authenticate dashboard administrator and return signed JWT."""
    client_ip = request.remote_addr or "127.0.0.1"
    if not rate_limiter.is_allowed(f"login_{client_ip}", max_requests=10, window_seconds=60):
        return jsonify({
            "error": "Too Many Requests",
            "message": "Too many failed login attempts. Please wait 1 minute."
        }), 429

    data = request.get_json(force=True, silent=True) or {}
    password = data.get("password", "")

    if not password:
        return jsonify({"error": "Bad Request", "message": "Password is required"}), 400

    if password != Config.DASHBOARD_PASSWORD:
        return jsonify({"error": "Unauthorized", "message": "Invalid dashboard password"}), 401

    token = jwt.encode(
        {
            "user": "admin",
            "iat": time.time(),
            "exp": time.time() + (30 * 86400)  # 30 days valid
        },
        Config.SECRET_KEY,
        algorithm="HS256"
    )
    return jsonify({
        "status": "ok",
        "token": token,
        "expires_in": 30 * 86400
    }), 200


@app.route("/ingest-frame", methods=["POST"])
def ingest_frame():
    """Ingest camera frame from remote camera agent."""
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != Config.AGENT_API_KEY:
        return jsonify({"error": "Unauthorized", "message": "Invalid X-API-Key"}), 401

    client_ip = request.remote_addr or "127.0.0.1"
    if not rate_limiter.is_allowed(f"ingest_{client_ip}", max_requests=120, window_seconds=60):
        return jsonify({"error": "Too Many Requests", "message": "Rate limit exceeded"}), 429

    # Max 5MB payload
    if request.content_length and request.content_length > 5 * 1024 * 1024:
        return jsonify({"error": "Payload Too Large", "message": "Frame exceeds 5MB limit"}), 413

    camera_id = request.headers.get("X-Camera-ID") or request.args.get("camera_id") or "camera_1"

    frame_bytes = None
    if "frame" in request.files:
        frame_bytes = request.files["frame"].read()
    elif "image" in request.files:
        frame_bytes = request.files["image"].read()
    else:
        frame_bytes = request.get_data()

    if not frame_bytes:
        return jsonify({"error": "Bad Request", "message": "No frame data received"}), 400

    import cv2
    import numpy as np
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        return jsonify({"error": "Bad Request", "message": "Could not decode JPEG frame"}), 400

    # Push to source manager (sets AgentSource and updates latest buffer)
    source_manager.push_agent_frame(frame, camera_id=camera_id)

    # Immediately run pipeline step on this frame so stats/alerts are instantly live
    evaluation = pipeline.process_single_frame(frame)

    return jsonify({
        "status": "ok",
        "camera_id": camera_id,
        "width": frame.shape[1],
        "height": frame.shape[0],
        "detections": len(evaluation.get("detections", [])),
        "total_items": evaluation.get("total_items", 0),
        "zones_evaluated": len(evaluation.get("zones", []))
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint reporting system uptime, DB status, and video source state."""
    uptime = round(time.time() - START_TIME, 2)
    db_status = db.get_status()
    source_status = source_manager.get_status()
    
    return jsonify({
        "status": "ok",
        "service": "smart-shelf-monitor-api",
        "uptime_seconds": uptime,
        "database": db_status,
        "video_source": source_status,
        "config": {
            "model_path": Config.MODEL_PATH,
            "confidence_threshold": Config.CONFIDENCE_THRESHOLD,
            "ffmpeg_available": os.path.exists(Config.FFMPEG_PATH),
        }
    }), 200


@app.route("/source", methods=["GET"])
@require_auth
def get_source():
    """Return the currently active video source and its health status."""
    return jsonify(source_manager.get_status()), 200


@app.route("/source", methods=["POST"])
@require_auth
def switch_source():
    """Switch the video source dynamically at runtime.

    Request JSON payload:
    {
        "type": "agent" | "webcam" | "video" | "stream" | "synthetic",
        "value": 0 | "sample_data/sample_shelf.mp4" | "http://<ip>:81/stream"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    source_type = data.get("type")
    source_value = data.get("value")

    if not source_type:
        return jsonify({
            "success": False,
            "message": "Missing 'type' parameter. Must be 'agent', 'webcam', 'video', or 'stream'."
        }), 400

    # Sensible defaults if value is omitted
    if source_value is None or source_value == "":
        if source_type == "webcam":
            source_value = 0
        elif source_type == "video":
            source_value = str(Config.SAMPLE_DATA_DIR / "sample_shelf.mp4")
        elif source_type in ("stream", "esp32"):
            source_value = "http://192.168.1.100:81/stream"
        elif source_type == "agent":
            source_value = "remote_push"
        elif source_type == "synthetic":
            source_value = "synthetic"

    success, message = source_manager.set_source(source_type, source_value)
    status = source_manager.get_status()

    return jsonify({
        "success": success,
        "message": message,
        "source": status
    }), (200 if success else 400)


@app.route("/live-frame", methods=["GET"])
@require_auth
def get_live_frame():
    """Return a single JPEG snapshot from the active video source."""
    # Read fresh frame or latest buffered frame
    success, frame = source_manager.get_frame()
    if not success or frame is None:
        frame = source_manager.get_latest_frame()

    jpeg_bytes = source_manager.get_jpeg_frame(frame)
    if not jpeg_bytes:
        return jsonify({"error": "Unable to capture frame from video source"}), 503

    return Response(jpeg_bytes, mimetype="image/jpeg")


@app.route("/shelf-status", methods=["GET"])
@require_auth
def get_shelf_status():
    """Return the latest evaluated shelf status, counts, percentages, and shortage predictions."""
    status_data = pipeline.get_status()
    zones = status_data.get("zones", [])

    low_count = sum(1 for z in zones if z.get("state") == "low")
    empty_count = sum(1 for z in zones if z.get("state") == "empty")
    misplaced_total = sum(z.get("misplaced_count", 0) for z in zones)

    return jsonify({
        "timestamp": time.time(),
        "is_pipeline_running": status_data.get("is_running", False),
        "fps": status_data.get("fps", 0.0),
        "latency_ms": status_data.get("latency_ms", 0.0),
        "processed_frames": status_data.get("processed_frames", 0),
        "total_zones": len(zones),
        "summary": {
            "low_stock_zones": low_count,
            "empty_zones": empty_count,
            "total_misplaced_items": misplaced_total,
            "total_items": sum(z.get("current_count", 0) for z in zones),
        },
        "zones": zones
    }), 200


@app.route("/live-stream", methods=["GET"])
@require_auth
def live_stream():
    """Stream continuous MJPEG feed of annotated frames for HTML <img> tags."""
    def generate_mjpeg():
        frame_interval = 1.0 / max(1, Config.STREAM_FPS)
        while True:
            t0 = time.time()
            jpeg_bytes = pipeline.get_latest_annotated_jpeg()
            if jpeg_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
                )
            elapsed = time.time() - t0
            sleep_time = max(0.01, frame_interval - elapsed)
            time.sleep(sleep_time)

    return Response(
        generate_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# -----------------------------------------------------------------------------
# Alerts Endpoints
# -----------------------------------------------------------------------------

@app.route("/alerts", methods=["GET"])
@require_auth
def get_alerts():
    """List recorded alerts with optional unacknowledged filter."""
    unack_only = request.args.get("unacknowledged", "").lower() in ("true", "1")
    limit = min(200, int(request.args.get("limit", 50)))

    filter_dict = {"acknowledged": False} if unack_only else {}
    alerts = list(db.alerts.find(filter_dict, sort=[("timestamp", -1)], limit=limit))
    return jsonify({
        "count": len(alerts),
        "alerts": serialize_docs(alerts)
    }), 200


@app.route("/alerts/<alert_id>/ack", methods=["POST"])
@require_auth
def acknowledge_alert(alert_id):
    """Mark an alert as acknowledged."""
    res = db.alerts.update_one(
        id_filter(alert_id),
        {"$set": {"acknowledged": True, "acknowledged_at": time.time()}}
    )

    if res.matched_count == 0:
        return jsonify({"success": False, "message": "Alert not found"}), 404

    return jsonify({"success": True, "message": "Alert acknowledged successfully"}), 200


# -----------------------------------------------------------------------------
# Shelf Zone CRUD Endpoints
# -----------------------------------------------------------------------------

@app.route("/zones", methods=["GET"])
@require_auth
def get_zones():
    """Retrieve all defined shelf zones."""
    zones = list(db.zones.find({}))
    return jsonify(serialize_docs(zones)), 200


@app.route("/zones", methods=["POST"])
@require_auth
def create_zone():
    """Create a new shelf zone definition.

    Payload:
    {
        "name": "Snack Rack",
        "expected_class": "bottle",
        "full_count": 5,
        "low_threshold": 0.35,
        "coords": {"x1": 0.1, "y1": 0.1, "x2": 0.5, "y2": 0.5}
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    expected_class = data.get("expected_class")
    if not name or not expected_class:
        return jsonify({"error": "Missing required fields: 'name' and 'expected_class'"}), 400

    coords = data.get("coords", {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9})
    zone_doc = {
        "id": str(uuid.uuid4()),
        "name": str(name).strip(),
        "expected_class": str(expected_class).lower().strip(),
        "full_count": max(1, int(data.get("full_count", 5))),
        "low_threshold": float(data.get("low_threshold", 0.35)),
        "coords": {
            "x1": round(float(coords.get("x1", 0.0)), 4),
            "y1": round(float(coords.get("y1", 0.0)), 4),
            "x2": round(float(coords.get("x2", 1.0)), 4),
            "y2": round(float(coords.get("y2", 1.0)), 4),
        },
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    insert_res = db.zones.insert_one(zone_doc)
    zone_doc["_id"] = str(insert_res.inserted_id)

    return jsonify(serialize_doc(zone_doc)), 201


@app.route("/zones/<zone_id>", methods=["PUT"])
@require_auth
def update_zone(zone_id):
    """Update a shelf zone's configuration."""
    data = request.get_json(force=True, silent=True) or {}
    update_fields = {}
    if "name" in data:
        update_fields["name"] = str(data["name"]).strip()
    if "expected_class" in data:
        update_fields["expected_class"] = str(data["expected_class"]).lower().strip()
    if "full_count" in data:
        update_fields["full_count"] = max(1, int(data["full_count"]))
    if "low_threshold" in data:
        update_fields["low_threshold"] = float(data["low_threshold"])
    if "coords" in data and isinstance(data["coords"], dict):
        c = data["coords"]
        update_fields["coords"] = {
            "x1": round(float(c.get("x1", 0.0)), 4),
            "y1": round(float(c.get("y1", 0.0)), 4),
            "x2": round(float(c.get("x2", 1.0)), 4),
            "y2": round(float(c.get("y2", 1.0)), 4),
        }
    update_fields["updated_at"] = time.time()

    res = db.zones.update_one(id_filter(zone_id), {"$set": update_fields})
    if res.matched_count == 0:
        return jsonify({"error": "Zone not found"}), 404

    updated = db.zones.find_one(id_filter(zone_id))
    return jsonify(serialize_doc(updated)), 200


@app.route("/zones/<zone_id>", methods=["DELETE"])
@require_auth
def delete_zone(zone_id):
    """Delete a shelf zone."""
    res = db.zones.delete_one(id_filter(zone_id))
    if res.deleted_count == 0:
        return jsonify({"error": "Zone not found"}), 404

    return jsonify({"success": True, "message": f"Zone {zone_id} deleted"}), 200


# -----------------------------------------------------------------------------
# Time-Series History Endpoint (for Charts)
# -----------------------------------------------------------------------------

@app.route("/history", methods=["GET"])
@require_auth
def get_history():
    """Return historical stock percentages and counts for Recharts."""
    zone_id = request.args.get("zone")
    hours = float(request.args.get("hours", 24))
    since_ts = time.time() - (hours * 3600)

    filter_dict = {"timestamp": {"$gte": since_ts}}
    if zone_id:
        filter_dict["zone_id"] = zone_id

    history_records = list(
        db.history.find(
            filter_dict,
            sort=[("timestamp", 1)],
            limit=500
        )
    )
    return jsonify({
        "count": len(history_records),
        "history": serialize_docs(history_records)
    }), 200


# -----------------------------------------------------------------------------
# Video Upload & Background Processing Job Endpoints
# -----------------------------------------------------------------------------

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


@app.route("/upload-video", methods=["POST"])
@require_auth
def upload_video():
    """Upload a video file for asynchronous sampling, detection, and annotation."""
    client_ip = request.remote_addr or "127.0.0.1"
    if not rate_limiter.is_allowed(f"upload_{client_ip}", max_requests=20, window_seconds=60):
        return jsonify({
            "error": "Too Many Requests",
            "message": "Upload rate limit exceeded. Please wait a minute."
        }), 429

    Config.cleanup_old_files()

    max_bytes = Config.MAX_UPLOAD_MB * 1024 * 1024
    if request.content_length and request.content_length > max_bytes:
        return jsonify({
            "error": "Payload Too Large",
            "message": f"File size exceeds maximum upload limit of {Config.MAX_UPLOAD_MB}MB."
        }), 413

    file = request.files.get("video") or request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "Bad Request", "message": "No video file provided"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid video file format. Supported: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        }), 400

    filename = secure_filename(file.filename)
    unique_prefix = uuid.uuid4().hex[:8]
    save_filename = f"{unique_prefix}_{filename}"
    save_path = Config.UPLOADS_DIR / save_filename
    file.save(str(save_path))

    # Verify actual saved file size
    if save_path.stat().st_size > max_bytes:
        try:
            save_path.unlink()
        except Exception:
            pass
        return jsonify({
            "error": "Payload Too Large",
            "message": f"File size exceeds maximum upload limit of {Config.MAX_UPLOAD_MB}MB."
        }), 413

    # Register and trigger job
    job_id = job_manager.create_job(filename=filename, filepath=str(save_path))
    job_manager.start_job(job_id)

    return jsonify({
        "success": True,
        "job_id": job_id,
        "filename": filename,
        "status": "queued",
        "message": "Video uploaded successfully. Processing started in background."
    }), 202


@app.route("/job-status/<job_id>", methods=["GET"])
@require_auth
def get_job_status(job_id):
    """Check processing status and completion percentage of an uploaded video job."""
    job = db.jobs.find_one(id_filter(job_id))
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "job_id": job.get("job_id", job_id),
        "filename": job.get("filename"),
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at"),
    }), 200


@app.route("/job-result/<job_id>", methods=["GET"])
@require_auth
def get_job_result(job_id):
    """Retrieve the summary metrics, event timeline, and annotated video URL for a completed job."""
    job = db.jobs.find_one(id_filter(job_id))
    if not job:
        return jsonify({"error": "Job not found"}), 404

    status = job.get("status")
    if status != "done":
        return jsonify({
            "job_id": job_id,
            "status": status,
            "progress": job.get("progress", 0),
            "message": f"Job is currently {status}. Check back once progress reaches 100%."
        }), 200

    return jsonify({
        "job_id": job_id,
        "status": "done",
        "progress": 100,
        "result": job.get("result", {})
    }), 200


@app.route("/outputs/<path:filename>", methods=["GET"])
@require_auth
def get_output_file(filename):
    """Serve annotated video files and reports securely."""
    clean_filename = secure_filename(os.path.basename(filename))
    base_dir = Config.OUTPUTS_DIR.resolve()
    target_path = (base_dir / clean_filename).resolve()

    if not str(target_path).startswith(str(base_dir)) or not target_path.exists():
        return jsonify({"error": "File not found or access denied"}), 404

    return send_from_directory(str(base_dir), clean_filename)


# -----------------------------------------------------------------------------
# System Metrics Endpoint (Evaluation & Monitoring)
# -----------------------------------------------------------------------------

@app.route("/metrics", methods=["GET"])
@require_auth
def get_metrics():
    """Return performance and monitoring metrics."""
    uptime = round(time.time() - START_TIME, 1)
    status_data = pipeline.get_status()

    total_alerts = db.alerts.count_documents({})
    unack_alerts = db.alerts.count_documents({"acknowledged": False})

    return jsonify({
        "uptime_seconds": uptime,
        "pipeline": {
            "is_running": status_data.get("is_running", False),
            "fps": status_data.get("fps", 0.0),
            "avg_inference_latency_ms": status_data.get("latency_ms", 0.0),
            "processed_frames": status_data.get("processed_frames", 0),
        },
        "alerts": {
            "total_count": total_alerts,
            "unacknowledged_count": unack_alerts,
        },
        "video_source": source_manager.get_status(),
        "database": db.get_status(),
    }), 200



# -----------------------------------------------------------------------------
# Phase 10: Model Info & Threshold Configuration
# -----------------------------------------------------------------------------

@app.route("/model-info", methods=["GET"])
def get_model_info():
    """Return model file name, class names, thresholds, image size, and device."""
    from inference.detect import detector
    info = detector.get_model_info()
    return jsonify(info), 200


@app.route("/model-config", methods=["POST"])
@require_auth
def update_model_config():
    """Adjust confidence and IoU thresholds from the Settings page (admin only)."""
    from inference.detect import detector
    data = request.get_json(force=True, silent=True) or {}
    conf = data.get("confidence_threshold")
    iou = data.get("iou_threshold")
    
    detector.set_thresholds(conf=conf, iou=iou)
    return jsonify({
        "status": "success",
        "message": "Model thresholds updated successfully",
        "model_info": detector.get_model_info()
    }), 200


# -----------------------------------------------------------------------------
# Phase 10: Demo Gallery & Single Image Analysis
# -----------------------------------------------------------------------------

def _encode_image_base64(img_bgr) -> str:
    """Encode OpenCV BGR image to base64 data URI string."""
    import cv2
    import base64
    success, buffer = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        return ""
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


def _build_analysis_caption(zone_evals: list, products_count: int, empty_slots: int) -> str:
    """Generate human-readable caption explaining the visual detection outcome."""
    if not zone_evals:
        return f"Detection identified {products_count} products and {empty_slots} empty slots across the view."
    
    empty_zones = [z["name"] for z in zone_evals if z["state"] == "empty"]
    low_zones = [z["name"] for z in zone_evals if z["state"] == "low"]
    misplaced = [z["name"] for z in zone_evals if z.get("misplaced_count", 0) > 0]
    
    parts = []
    if empty_zones:
        parts.append(f"{', '.join(empty_zones)} is completely empty")
    if low_zones:
        parts.append(f"{', '.join(low_zones)} is running low on stock")
    if misplaced:
        parts.append(f"misplaced items detected in {', '.join(misplaced)}")
        
    if parts:
        desc = "; ".join(parts) + "."
        return f"Detection identified {products_count} products and {empty_slots} empty slots. Status: {desc}"
    else:
        return f"All {len(zone_evals)} shelf zones are adequately stocked ({products_count} products detected). Stock levels are healthy."


@app.route("/demo/samples", methods=["GET"])
@require_auth
def get_demo_samples():
    """Retrieve gallery of ready-made sample images from test split."""
    samples_file = Config.DEMO_SAMPLES_DIR / "samples.json"
    if not samples_file.exists():
        return jsonify([]), 200
        
    try:
        import json
        with open(samples_file, "r", encoding="utf-8") as f:
            samples = json.load(f)
            
        for s in samples:
            s["image_url"] = f"/demo/samples/image/{s['filename']}"
            
        return jsonify(samples), 200
    except Exception as e:
        logger.error(f"Error loading demo samples: {e}")
        return jsonify({"error": "Failed to load demo samples"}), 500


@app.route("/demo/samples/image/<path:filename>", methods=["GET"])
def get_demo_sample_image(filename):
    """Serve demo sample images."""
    clean_filename = secure_filename(os.path.basename(filename))
    base_dir = Config.DEMO_SAMPLES_DIR.resolve()
    target_path = (base_dir / clean_filename).resolve()
    
    if not str(target_path).startswith(str(base_dir)) or not target_path.exists():
        return jsonify({"error": "Sample image not found"}), 404
        
    return send_from_directory(str(base_dir), clean_filename)


@app.route("/demo/analyze-sample/<sample_id>", methods=["POST"])
@require_auth
def analyze_demo_sample(sample_id):
    """Run detection and zone analysis on a selected demo sample image."""
    import cv2
    import json
    from inference.detect import detector
    from inference.stock import analyze_shelf_zones, annotate_frame
    
    samples_file = Config.DEMO_SAMPLES_DIR / "samples.json"
    target_sample = None
    if samples_file.exists():
        try:
            with open(samples_file, "r", encoding="utf-8") as f:
                samples = json.load(f)
                for s in samples:
                    if s["id"] == sample_id or s["filename"] == sample_id:
                        target_sample = s
                        break
        except Exception as e:
            logger.warning(f"Error parsing samples.json: {e}")
            
    img_path = Config.DEMO_SAMPLES_DIR / (target_sample["filename"] if target_sample else f"{sample_id}.jpg")
    if not img_path.exists():
        for p in Config.DEMO_SAMPLES_DIR.glob(f"*{sample_id}*"):
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                img_path = p
                break
                
    if not img_path.exists():
        return jsonify({"error": f"Demo sample '{sample_id}' not found"}), 404
        
    img_bgr = cv2.imread(str(img_path))
    if img_bgr is None:
        return jsonify({"error": "Could not read sample image"}), 400
        
    data = request.get_json(force=True, silent=True) or {}
    conf_override = data.get("confidence") or request.args.get("confidence", type=float)
    iou_override = data.get("iou") or request.args.get("iou", type=float)
    
    detections, latency_ms = detector.detect(img_bgr, conf=conf_override, iou=iou_override)
    raw_zones = list(db.zones.find({}))
    zones = serialize_docs(raw_zones)
    zone_evals = analyze_shelf_zones(zones, detections)
    
    annotated = annotate_frame(img_bgr, zone_evals, detections)
    annotated_b64 = _encode_image_base64(annotated)
    original_b64 = _encode_image_base64(img_bgr)
    
    products_count = sum(1 for d in detections if str(d.get("class_name", "")).lower() == "product" or d.get("class_id") == 0)
    empty_slots = sum(1 for d in detections if str(d.get("class_name", "")).lower() in ("empty_slot", "empty") or d.get("class_id") == 1)
    
    caption = _build_analysis_caption(zone_evals, products_count, empty_slots)
    
    return jsonify({
        "sample_id": sample_id,
        "source": "demo_sample",
        "latency_ms": latency_ms,
        "products_count": products_count,
        "empty_slots_count": empty_slots,
        "caption": caption,
        "zones": zone_evals,
        "detections": detections,
        "annotated_image": annotated_b64,
        "original_image": original_b64,
        "sample_meta": target_sample
    }), 200


@app.route("/analyze-image", methods=["POST"])
@require_auth
def analyze_uploaded_image():
    """Analyze a user-uploaded image (max 10MB, jpg/png/webp) without polluting live monitoring."""
    import cv2
    import numpy as np
    import base64
    from inference.detect import detector
    from inference.stock import analyze_shelf_zones, annotate_frame
    
    max_bytes = 10 * 1024 * 1024
    if request.content_length and request.content_length > max_bytes:
        return jsonify({"error": "Payload Too Large", "message": "Image exceeds 10MB limit"}), 413
        
    img_bytes = None
    if "image" in request.files:
        img_bytes = request.files["image"].read()
    elif "file" in request.files:
        img_bytes = request.files["file"].read()
    else:
        data = request.get_json(force=True, silent=True) or {}
        if "image_base64" in data:
            raw_b64 = data["image_base64"]
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(raw_b64)
            except Exception:
                return jsonify({"error": "Bad Request", "message": "Invalid base64 image data"}), 400
        else:
            img_bytes = request.get_data()
            
    if not img_bytes or len(img_bytes) == 0:
        return jsonify({"error": "Bad Request", "message": "No image payload received"}), 400
        
    if len(img_bytes) > max_bytes:
        return jsonify({"error": "Payload Too Large", "message": "Image exceeds 10MB limit"}), 413
        
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return jsonify({"error": "Bad Request", "message": "Could not decode image (supported: JPG, PNG, WebP)"}), 400
        
    conf_override = request.args.get("confidence", type=float)
    iou_override = request.args.get("iou", type=float)
    if not conf_override and request.form.get("confidence"):
        try:
            conf_override = float(request.form.get("confidence"))
        except ValueError:
            pass
            
    detections, latency_ms = detector.detect(img_bgr, conf=conf_override, iou=iou_override)
    raw_zones = list(db.zones.find({}))
    zones = serialize_docs(raw_zones)
    zone_evals = analyze_shelf_zones(zones, detections)
    
    annotated = annotate_frame(img_bgr, zone_evals, detections)
    annotated_b64 = _encode_image_base64(annotated)
    original_b64 = _encode_image_base64(img_bgr)
    
    products_count = sum(1 for d in detections if str(d.get("class_name", "")).lower() == "product" or d.get("class_id") == 0)
    empty_slots = sum(1 for d in detections if str(d.get("class_name", "")).lower() in ("empty_slot", "empty") or d.get("class_id") == 1)
    
    caption = _build_analysis_caption(zone_evals, products_count, empty_slots)
    
    return jsonify({
        "source": "demo_upload",
        "latency_ms": latency_ms,
        "products_count": products_count,
        "empty_slots_count": empty_slots,
        "caption": caption,
        "zones": zone_evals,
        "detections": detections,
        "annotated_image": annotated_b64,
        "original_image": original_b64
    }), 200


@app.route("/demo/import", methods=["POST"])
@require_auth
def import_demo_sample():
    """Import an image into the demo gallery (dev/admin tool)."""
    import json
    import uuid
    from werkzeug.utils import secure_filename
    
    file = request.files.get("image") or request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No image file provided"}), 400
        
    title = request.form.get("title", "Imported Test Sample")
    category = request.form.get("category", "custom_test")
    
    clean_name = f"imported_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    save_path = Config.DEMO_SAMPLES_DIR / clean_name
    file.save(str(save_path))
    
    samples_file = Config.DEMO_SAMPLES_DIR / "samples.json"
    samples = []
    if samples_file.exists():
        try:
            with open(samples_file, "r", encoding="utf-8") as f:
                samples = json.load(f)
        except Exception:
            samples = []
            
    sample_id = f"sample_{len(samples) + 1:02d}"
    entry = {
        "id": sample_id,
        "filename": clean_name,
        "title": title,
        "category": category,
        "source": "Imported by User (Admin)"
    }
    samples.append(entry)
    with open(samples_file, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2)
        
    return jsonify({
        "status": "success",
        "message": "Demo sample imported successfully",
        "sample": entry
    }), 201


# -----------------------------------------------------------------------------
# Phase 10: Camera Abstraction & Controls
# -----------------------------------------------------------------------------

@app.route("/camera/status", methods=["GET"])
@require_auth
def get_camera_status():
    """Return unified camera layer status, mode, scenario info, and live pipeline trace."""
    from camera import camera_manager
    cam_status = camera_manager.get_status()
    pipe_status = pipeline.get_status()
    
    return jsonify({
        **cam_status,
        "pipeline": pipe_status
    }), 200


@app.route("/camera/mode", methods=["POST"])
@require_auth
def switch_camera_mode():
    """Switch active camera mode (simulated, esp32_pull, esp32_push, video_file)."""
    from camera import camera_manager
    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode") or data.get("camera_mode")
    if not mode:
        return jsonify({"error": "Bad Request", "message": "Missing 'mode' parameter"}), 400
        
    try:
        updated = camera_manager.set_mode(
            mode=mode,
            esp32_ip=data.get("esp32_ip"),
            scenario=data.get("scenario"),
            speed=data.get("speed")
        )
        return jsonify({
            "status": "success",
            "message": f"Camera mode switched to {mode}",
            "camera_status": updated
        }), 200
    except ValueError as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400


@app.route("/camera/control", methods=["POST"])
@require_auth
def control_camera():
    """Control simulated playback (start, pause, reset, set_scenario, set_speed)."""
    from camera import camera_manager
    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action")
    if not action:
        return jsonify({"error": "Bad Request", "message": "Missing 'action' parameter"}), 400
        
    try:
        updated = camera_manager.control_simulated(
            action=action,
            scenario=data.get("scenario"),
            speed=data.get("speed")
        )
        return jsonify({
            "status": "success",
            "action": action,
            "simulated_status": updated
        }), 200
    except ValueError as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400


@app.route("/camera/clear-simulated", methods=["POST"])
@require_auth
def clear_simulated_data():
    """Delete all simulated history and alert records from the database."""
    h_res = db.history.delete_many({"simulated": True})
    a_res = db.alerts.delete_many({"simulated": True})
    
    return jsonify({
        "status": "success",
        "message": "Simulated records cleared successfully",
        "deleted_history_count": h_res.deleted_count,
        "deleted_alerts_count": a_res.deleted_count
    }), 200


@app.route("/ingest-photo", methods=["POST"])
def ingest_esp32_photo():
    """ESP32-CAM Push Mode Ingestion Endpoint."""
    from camera import camera_manager
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != Config.CAMERA_API_KEY:
        return jsonify({"error": "Unauthorized", "message": "Invalid X-API-Key"}), 401
        
    max_bytes = 5 * 1024 * 1024
    if request.content_length and request.content_length > max_bytes:
        return jsonify({"error": "Payload Too Large", "message": "Photo exceeds 5MB limit"}), 413
        
    camera_id = request.headers.get("X-Camera-ID") or "esp32_cam_default"
    
    jpeg_bytes = None
    if "photo" in request.files:
        jpeg_bytes = request.files["photo"].read()
    elif "image" in request.files:
        jpeg_bytes = request.files["image"].read()
    else:
        jpeg_bytes = request.get_data()
        
    if not jpeg_bytes:
        return jsonify({"error": "Bad Request", "message": "No photo data received"}), 400
        
    if len(jpeg_bytes) > max_bytes:
        return jsonify({"error": "Payload Too Large", "message": "Photo exceeds 5MB limit"}), 413
        
    camera_manager.esp32_push_source.receive_photo(jpeg_bytes, camera_id=camera_id)
    
    return jsonify({
        "status": "ok",
        "camera_id": camera_id,
        "received_bytes": len(jpeg_bytes)
    }), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500


if __name__ == "__main__":
    logger.info(f"Starting Smart Shelf Monitor API on {Config.HOST}:{Config.PORT}...")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, threaded=True)
