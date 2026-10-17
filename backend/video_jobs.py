"""Background Video Processing Job Runner.

Processes uploaded videos (mp4, avi, mov) asynchronously:
- Samples frames every ~0.5s
- Runs YOLO detection and shelf zone evaluations
- Produces browser-playable annotated MP4 (H.264 via FFmpeg)
- Records detailed event timeline (empty slots, low stock, misplaced products)
- Updates job progress and results in DB
"""

import logging
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from config import Config
from db import db, serialize_doc, serialize_docs
from inference.detect import detector
from inference.stock import analyze_shelf_zones, annotate_frame

logger = logging.getLogger(__name__)


def transcode_to_h264_mp4(input_video_path: Path, output_mp4_path: Path) -> bool:
    """Transcode video to browser-playable H.264 AAC MP4 using FFmpeg if available."""
    ffmpeg_bin = Config.FFMPEG_PATH
    if not os.path.exists(ffmpeg_bin):
        logger.warning(f"FFmpeg binary not found at {ffmpeg_bin}. Using original output video.")
        return False

    temp_output = output_mp4_path.with_name(f"temp_h264_{output_mp4_path.name}")
    cmd = [
        str(ffmpeg_bin),
        "-y",
        "-i", str(input_video_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        str(temp_output)
    ]
    try:
        logger.info(f"Transcoding {input_video_path.name} to H.264 via FFmpeg...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if res.returncode == 0 and temp_output.exists():
            # Replace output_mp4_path with transcode
            if output_mp4_path.exists():
                output_mp4_path.unlink()
            temp_output.rename(output_mp4_path)
            logger.info(f"Successfully transcoded browser-playable video: {output_mp4_path}")
            return True
        else:
            logger.warning(f"FFmpeg transcode exited with code {res.returncode}: {res.stderr.decode('utf-8', errors='ignore')[:300]}")
    except Exception as e:
        logger.error(f"FFmpeg transcode error: {e}")
        if temp_output.exists():
            temp_output.unlink()
    return False


class VideoJobManager:
    """Manages asynchronous video processing jobs."""

    def __init__(self):
        self._lock = threading.Lock()

    def create_job(self, filename: str, filepath: str) -> str:
        """Register a new video job in the database."""
        job_id = str(uuid.uuid4())
        job_doc = {
            "_id": job_id,
            "job_id": job_id,
            "filename": filename,
            "filepath": filepath,
            "status": "queued",  # queued | processing | done | failed
            "progress": 0,       # 0 - 100
            "created_at": time.time(),
            "completed_at": None,
            "error": None,
            "result": None,
        }
        db.jobs.insert_one(job_doc)
        logger.info(f"Video job created: {job_id} ({filename})")
        return job_id

    def start_job(self, job_id: str):
        """Spawn background worker thread to process video."""
        thread = threading.Thread(
            target=self._process_video_worker,
            args=(job_id,),
            name=f"Job-{job_id[:8]}",
            daemon=True
        )
        thread.start()

    def _process_video_worker(self, job_id: str):
        """Worker function running detection, zone analysis, and rendering."""
        job = db.jobs.find_one({"job_id": job_id})
        if not job:
            logger.error(f"Job {job_id} not found in database.")
            return

        filepath = Path(job["filepath"])
        if not filepath.exists():
            db.jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "failed", "error": f"File {filepath} not found"}}
            )
            return

        # Mark job as processing
        db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "processing", "progress": 5}}
        )

        cap = cv2.VideoCapture(str(filepath))
        if not cap.isOpened():
            db.jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "failed", "error": "Unable to open video with OpenCV"}}
            )
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
        duration_sec = total_frames / max(1.0, video_fps)

        # Sample every ~0.5 seconds
        sample_step = max(1, int(video_fps * 0.5))
        output_filename = f"{job_id}_annotated.mp4"
        raw_output_path = Config.OUTPUTS_DIR / f"raw_{output_filename}"
        final_output_path = Config.OUTPUTS_DIR / output_filename

        # Video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        output_fps = max(2.0, min(video_fps, 15.0))
        out = cv2.VideoWriter(str(raw_output_path), fourcc, output_fps, (width, height))

        # Retrieve current shelf zones from DB
        zones = serialize_docs(list(db.zones.find({})))

        # Aggregated statistics
        timeline_events: List[Dict[str, Any]] = []
        class_counts: Dict[str, int] = {}
        zone_stock_samples: Dict[str, List[float]] = {
            str(z.get("zone_id", z.get("id", z.get("_id")))): [] for z in zones
        }
        processed_samples = 0
        current_frame_idx = 0

        logger.info(f"Processing job {job_id}: {total_frames} frames, {duration_sec:.1f}s duration...")

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                # Process every sample_step frame
                if current_frame_idx % sample_step == 0:
                    timestamp_sec = round(current_frame_idx / video_fps, 1)

                    # YOLO detection
                    detections, latency = detector.detect(frame)
                    
                    # Accumulate class counts
                    for d in detections:
                        cname = d.get("class_name", "unknown")
                        class_counts[cname] = class_counts.get(cname, 0) + 1

                    # Zone stock logic
                    evals = analyze_shelf_zones(zones, detections)
                    for z in evals:
                        zid = str(z.get("zone_id", z.get("id", z.get("_id", ""))))
                        zone_stock_samples.setdefault(zid, []).append(z["stock_percent"])

                        # Check for notable events
                        if z["state"] == "empty":
                            timeline_events.append({
                                "time_sec": timestamp_sec,
                                "zone_id": zid,
                                "zone_name": z["name"],
                                "type": "empty_shelf",
                                "severity": "critical",
                                "message": f"{z['name']} was EMPTY at {timestamp_sec}s"
                            })
                        elif z["state"] == "low":
                            timeline_events.append({
                                "time_sec": timestamp_sec,
                                "zone_id": zid,
                                "zone_name": z["name"],
                                "type": "low_stock",
                                "severity": "warning",
                                "message": f"{z['name']} was LOW ({int(z['stock_percent']*100)}%) at {timestamp_sec}s"
                            })

                        if z["misplaced_count"] > 0:
                            mis_names = ", ".join(m["class_name"] for m in z.get("misplaced_items", []))
                            timeline_events.append({
                                "time_sec": timestamp_sec,
                                "zone_id": zid,
                                "zone_name": z["name"],
                                "type": "misplaced_product",
                                "severity": "info",
                                "message": f"Misplaced {mis_names} detected in {z['name']} at {timestamp_sec}s"
                            })

                    # Annotate frame and write to output video
                    annotated = annotate_frame(frame, evals, detections)
                    out.write(annotated)
                    processed_samples += 1

                    # Update progress in DB (scaled 5% -> 85%)
                    pct = int(5 + (current_frame_idx / total_frames) * 80)
                    db.jobs.update_one(
                        {"job_id": job_id},
                        {"$set": {"progress": min(85, pct)}}
                    )

                current_frame_idx += 1

            cap.release()
            out.release()

            # Transcode to H.264 for universal browser playback
            db.jobs.update_one({"job_id": job_id}, {"$set": {"progress": 90}})
            transcode_success = transcode_to_h264_mp4(raw_output_path, final_output_path)
            if not transcode_success:
                # If transcode failed/skipped, rename raw output to final
                if raw_output_path.exists():
                    if final_output_path.exists():
                        final_output_path.unlink()
                    raw_output_path.rename(final_output_path)

            # Build summary statistics
            zone_averages = {}
            for z in zones:
                zid_candidates = [
                    str(z.get("zone_id", "")),
                    str(z.get("id", "")),
                    str(z.get("_id", ""))
                ]
                samples = []
                for cand in zid_candidates:
                    if cand and cand in zone_stock_samples:
                        samples = zone_stock_samples[cand]
                        break
                avg_pct = round(sum(samples) / max(1, len(samples)), 2) if samples else 0.0
                zone_averages[z.get("name", "Zone")] = {
                    "average_stock_percent": avg_pct,
                    "expected_class": z.get("expected_class"),
                    "full_count": z.get("full_count", 1)
                }

            result_payload = {
                "output_video_filename": output_filename,
                "output_video_url": f"/outputs/{output_filename}",
                "duration_seconds": round(duration_sec, 1),
                "total_frames": total_frames,
                "analyzed_samples": processed_samples,
                "class_counts": class_counts,
                "zone_summary": zone_averages,
                "total_events": len(timeline_events),
                "timeline": timeline_events[:100]  # Cap at 100 timeline events
            }

            db.jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": "done",
                        "progress": 100,
                        "completed_at": time.time(),
                        "result": result_payload
                    }
                }
            )
            logger.info(f"Video job {job_id} successfully completed!")

        except Exception as e:
            logger.error(f"Error processing video job {job_id}: {e}", exc_info=True)
            db.jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "failed", "error": str(e), "progress": 100}}
            )


# Global video job manager
job_manager = VideoJobManager()
