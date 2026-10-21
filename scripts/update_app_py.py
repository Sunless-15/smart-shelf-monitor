from pathlib import Path

app_path = Path(r"D:\project\smart shelf\backend\app.py")
content = app_path.read_text(encoding="utf-8")

anchor = "@app.errorhandler(404)"
if anchor not in content:
    raise RuntimeError("Could not find anchor in app.py")

phase10_code = """
# -----------------------------------------------------------------------------
# Phase 10: Model Info & Threshold Configuration
# -----------------------------------------------------------------------------

@app.route("/model-info", methods=["GET"])
def get_model_info():
    \"\"\"Return model file name, class names, thresholds, image size, and device.\"\"\"
    from inference.detect import detector
    info = detector.get_model_info()
    return jsonify(info), 200


@app.route("/model-config", methods=["POST"])
@require_auth
def update_model_config():
    \"\"\"Adjust confidence and IoU thresholds from the Settings page (admin only).\"\"\"
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
    \"\"\"Encode OpenCV BGR image to base64 data URI string.\"\"\"
    import cv2
    import base64
    success, buffer = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        return ""
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


def _build_analysis_caption(zone_evals: list, products_count: int, empty_slots: int) -> str:
    \"\"\"Generate human-readable caption explaining the visual detection outcome.\"\"\"
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
    \"\"\"Retrieve gallery of ready-made sample images from test split.\"\"\"
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
    \"\"\"Serve demo sample images.\"\"\"
    clean_filename = secure_filename(os.path.basename(filename))
    base_dir = Config.DEMO_SAMPLES_DIR.resolve()
    target_path = (base_dir / clean_filename).resolve()
    
    if not str(target_path).startswith(str(base_dir)) or not target_path.exists():
        return jsonify({"error": "Sample image not found"}), 404
        
    return send_from_directory(str(base_dir), clean_filename)


@app.route("/demo/analyze-sample/<sample_id>", methods=["POST"])
@require_auth
def analyze_demo_sample(sample_id):
    \"\"\"Run detection and zone analysis on a selected demo sample image.\"\"\"
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
    \"\"\"Analyze a user-uploaded image (max 10MB, jpg/png/webp) without polluting live monitoring.\"\"\"
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
    \"\"\"Import an image into the demo gallery (dev/admin tool).\"\"\"
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
    \"\"\"Return unified camera layer status, mode, scenario info, and live pipeline trace.\"\"\"
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
    \"\"\"Switch active camera mode (simulated, esp32_pull, esp32_push, video_file).\"\"\"
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
    \"\"\"Control simulated playback (start, pause, reset, set_scenario, set_speed).\"\"\"
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
    \"\"\"Delete all simulated history and alert records from the database.\"\"\"
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
    \"\"\"ESP32-CAM Push Mode Ingestion Endpoint.\"\"\"
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

"""

new_content = content.replace(anchor, phase10_code + "\n" + anchor)
app_path.write_text(new_content, encoding="utf-8")
print("app.py updated with Phase 10 endpoints successfully!")
