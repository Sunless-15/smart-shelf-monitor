"""Unit tests for Phase 1: Config, DB layer with fallback, Video Sources, and Flask Endpoints."""

import pytest
import os
import sys
import json
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import Config
from db import Database, FallbackDB, FallbackCollection
from sources import (
    VideoFileSource, 
    SyntheticShelfSource, 
    VideoSourceManager, 
    generate_synthetic_shelf_video
)
from app import app


def test_config():
    """Verify configuration loads properly and paths exist."""
    assert Config.PORT == 5000
    assert Config.HOST == "0.0.0.0"
    assert Config.UPLOADS_DIR.exists()
    assert Config.OUTPUTS_DIR.exists()
    assert Config.DATA_DIR.exists()
    assert Config.SAMPLE_DATA_DIR.exists()


def test_fallback_db(tmp_path):
    """Verify in-memory fallback database operations with JSON persistence."""
    json_path = tmp_path / "test_fallback.json"
    fallback_db = FallbackDB(file_path=str(json_path))
    col = fallback_db["test_items"]

    # Insert
    res = col.insert_one({"name": "item1", "count": 10, "state": "ok"})
    assert res.inserted_id is not None
    assert col.count_documents() == 1

    # Find one
    doc = col.find_one({"name": "item1"})
    assert doc is not None
    assert doc["count"] == 10

    # Query with operators
    res_gte = col.find({"count": {"$gte": 5}})
    assert len(res_gte) == 1
    res_gt20 = col.find({"count": {"$gt": 20}})
    assert len(res_gt20) == 0

    # Update
    col.update_one({"name": "item1"}, {"$set": {"count": 2}})
    updated_doc = col.find_one({"name": "item1"})
    assert updated_doc["count"] == 2

    # Verify JSON file on disk
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert "test_items" in saved_data
        assert saved_data["test_items"][0]["count"] == 2

    # Delete
    del_res = col.delete_one({"name": "item1"})
    assert del_res.deleted_count == 1
    assert col.count_documents() == 0


def test_database_connection_and_zones():
    """Verify Database instance connects (to MongoDB or Fallback) and seeds default zones."""
    db = Database()
    status = db.get_status()
    assert status["connected"] is True
    assert status["type"] in ("mongodb", "in_memory_fallback")

    # Check that default zones exist
    zones = list(db.zones.find({}))
    assert len(zones) >= 3
    zone_names = [z["name"] for z in zones]
    assert any("Top Left" in n for n in zone_names)


def test_synthetic_video_and_file_source(tmp_path):
    """Verify synthetic video generation and VideoFileSource looping."""
    video_path = tmp_path / "test_shelf.mp4"
    generated_path = generate_synthetic_shelf_video(video_path, num_frames=10, fps=20)
    assert os.path.exists(generated_path)

    source = VideoFileSource(generated_path, loop=True)
    assert source.is_opened() is True

    # Read frames
    success, frame = source.read()
    assert success is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)

    source.release()
    assert source.is_active is False


def test_source_manager_switching():
    """Verify dynamic switching between sources in VideoSourceManager."""
    mgr = VideoSourceManager()
    
    # Switch to synthetic
    success, msg = mgr.set_source("synthetic", "synthetic")
    assert success is True
    status = mgr.get_status()
    assert status["type"] == "synthetic"
    assert status["is_opened"] is True

    # Grab frame & JPEG bytes
    success, frame = mgr.get_frame()
    assert success is True
    assert frame is not None
    
    jpeg_bytes = mgr.get_jpeg_frame(frame)
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 1000  # valid JPEG binary


def test_flask_endpoints():
    """Verify Flask /health, /source, and /live-frame endpoints."""
    client = app.test_client()

    # /health
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "database" in data
    assert "video_source" in data

    # /source GET
    res_src = client.get("/source")
    assert res_src.status_code == 200
    src_data = res_src.get_json()
    assert "type" in src_data

    # /source POST switch
    res_switch = client.post("/source", json={"type": "synthetic", "value": "internal"})
    assert res_switch.status_code == 200
    switch_data = res_switch.get_json()
    assert switch_data["success"] is True

    # /live-frame GET
    res_frame = client.get("/live-frame")
    assert res_frame.status_code == 200
    assert res_frame.content_type == "image/jpeg"
    assert len(res_frame.data) > 1000
