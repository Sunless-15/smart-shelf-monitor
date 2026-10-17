"""Intelligent Empty Shelf and Low Stock Monitoring System - Flask Backend Entry Point.

Phase 1 Core: Server skeleton, configuration, database layer with fallback,
video source abstraction layer, and health verification endpoints.
"""

import logging
import os
import time
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from config import Config
from db import db
from sources import source_manager
from pipeline import pipeline

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
