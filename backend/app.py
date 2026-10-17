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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smart_shelf_backend")

app = Flask(__name__)
# Enable CORS for all routes and origins (allowing Vite dev server and mobile clients)
CORS(app, resources={r"/*": {"origins": "*"}})

# Start live monitoring pipeline in background
pipeline.start()

START_TIME = time.time()


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
def get_source():
    """Return the currently active video source and its health status."""
    return jsonify(source_manager.get_status()), 200


@app.route("/source", methods=["POST"])
def switch_source():
    """Switch the video source dynamically at runtime.

    Request JSON payload:
    {
        "type": "webcam" | "video" | "stream" | "synthetic",
        "value": 0 | "sample_data/sample_shelf.mp4" | "http://<ip>:81/stream"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    source_type = data.get("type")
    source_value = data.get("value")

    if not source_type:
        return jsonify({
            "success": False,
            "message": "Missing 'type' parameter. Must be 'webcam', 'video', or 'stream'."
        }), 400

    # Sensible defaults if value is omitted
    if source_value is None or source_value == "":
        if source_type == "webcam":
            source_value = 0
        elif source_type == "video":
            source_value = str(Config.SAMPLE_DATA_DIR / "sample_shelf.mp4")
        elif source_type in ("stream", "esp32"):
            source_value = "http://192.168.1.100:81/stream"
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
def get_zones():
    """Retrieve all defined shelf zones."""
    zones = list(db.zones.find({}))
    return jsonify(serialize_docs(zones)), 200


@app.route("/zones", methods=["POST"])
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
def update_zone(zone_id):
    """Update an existing shelf zone."""
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
def get_history():
    """Return historical stock percentages and counts for Recharts."""
    zone_id = request.args.get("zone")
    hours = float(request.args.get("hours", 24))
    since_ts = time.time() - (hours * 3600)

    filter_dict: Dict[str, Any] = {"timestamp": {"$gte": since_ts}}
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
def upload_video():
    """Upload a video file for asynchronous sampling, detection, and annotation."""
    file = request.files.get("video") or request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No video file provided"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"Invalid video file format. Supported: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        }), 400

    filename = secure_filename(file.filename)
    unique_prefix = uuid.uuid4().hex[:8]
    save_filename = f"{unique_prefix}_{filename}"
    save_path = Config.UPLOADS_DIR / save_filename
    file.save(str(save_path))

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
def get_output_file(filename):
    """Serve annotated video files and reports."""
    return send_from_directory(Config.OUTPUTS_DIR, filename)


# -----------------------------------------------------------------------------
# System Metrics Endpoint (Evaluation & Monitoring)
# -----------------------------------------------------------------------------

@app.route("/metrics", methods=["GET"])
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
