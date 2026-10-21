import os
from pathlib import Path
from dotenv import load_dotenv

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BACKEND_DIR / ".env")

class Config:
    """Application configuration with sensible defaults."""
    
    BACKEND_DIR = BACKEND_DIR
    
    # Server & Cloud
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    IS_CLOUD = bool(os.getenv("RENDER") or os.getenv("CLOUD_MODE") or os.getenv("PORT") and os.getenv("PORT") != "5000")

    # Security & Authentication
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
    SECRET_KEY = os.getenv("SECRET_KEY", "smart_shelf_secret_jwt_key_2026_super_secure_32b")
    AGENT_API_KEY = os.getenv("AGENT_API_KEY", "shelf_agent_secret_key_2026")

    # CORS Origins (Comma-separated from env, plus local dev origins)
    _raw_cors = os.getenv("CORS_ORIGINS", "")
    _custom_origins = [o.strip() for o in _raw_cors.split(",") if o.strip()]
    DEFAULT_DEV_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    CORS_ORIGINS = list(set(DEFAULT_DEV_ORIGINS + _custom_origins)) if _custom_origins else DEFAULT_DEV_ORIGINS

    # Database (MongoDB with Fallback)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "shelf_monitor")
    MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "2000"))
    
    # Storage Directories & Limits
    UPLOADS_DIR = BACKEND_DIR / "uploads"
    OUTPUTS_DIR = BACKEND_DIR / "outputs"
    MODELS_DIR = BACKEND_DIR / "models"
    SAMPLE_DATA_DIR = BACKEND_DIR / "sample_data"
    DATA_DIR = BACKEND_DIR / "data"
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
    FILE_CLEANUP_HOURS = int(os.getenv("FILE_CLEANUP_HOURS", "6"))
    
    # Model & Inference Memory Constraints
    MODEL_PATH = os.getenv("MODEL_PATH", str(MODELS_DIR / "yolov8n.pt"))
    MODEL_URL = os.getenv("MODEL_URL", "")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
    INFERENCE_MAX_WIDTH = int(os.getenv("INFERENCE_MAX_WIDTH", "640"))
    
    # Video Source Defaults
    # Types: "agent", "webcam", "video", "stream"
    # Detection Thresholds & Model Customization
    IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))
    
    # Camera Layer & ESP32 Configuration
    # Modes: "simulated", "esp32_pull", "esp32_push", "video_file"
    CAMERA_MODE = os.getenv("CAMERA_MODE", "simulated").lower().strip()
    ESP32_IP = os.getenv("ESP32_IP", "192.168.1.100")
    CAPTURE_INTERVAL_SECONDS = float(os.getenv("CAPTURE_INTERVAL_SECONDS", "5.0"))
    CAMERA_API_KEY = os.getenv("CAMERA_API_KEY", os.getenv("AGENT_API_KEY", "shelf_agent_secret_key_2026"))
    ACTIVE_SCENARIO = os.getenv("ACTIVE_SCENARIO", "gradual_depletion")
    PLAYBACK_SPEED = float(os.getenv("PLAYBACK_SPEED", "1.0"))

    # Demo Directories
    DEMO_SAMPLES_DIR = BACKEND_DIR / "demo_samples"
    DEMO_SCENARIOS_DIR = BACKEND_DIR / "demo_scenarios"

    DEFAULT_SOURCE_TYPE = os.getenv(
        "DEFAULT_SOURCE_TYPE", 
        "agent" if IS_CLOUD else "video"
    )
    DEFAULT_SOURCE_VALUE = os.getenv(
        "DEFAULT_SOURCE_VALUE", 
        "remote_push" if (IS_CLOUD or os.getenv("DEFAULT_SOURCE_TYPE") == "agent") else str(SAMPLE_DATA_DIR / "sample_shelf.mp4")
    )
    
    # Video Streaming & Pipeline
    STREAM_FPS = int(os.getenv("STREAM_FPS", "15"))
    PIPELINE_FPS = float(os.getenv("PIPELINE_FPS", "2.0"))
    FRAME_SAMPLE_RATE = float(os.getenv("FRAME_SAMPLE_RATE", "2.0"))
    
    # FFmpeg executable path (auto-detects project ffmpeg if present)
    PROJECT_FFMPEG = Path(r"D:\project\ffmpeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe")
    FFMPEG_PATH = os.getenv(
        "FFMPEG_PATH", 
        str(PROJECT_FFMPEG) if PROJECT_FFMPEG.exists() else "ffmpeg"
    )

    @classmethod
    def ensure_directories(cls):
        """Ensure all required folders exist."""
        for folder in [
            cls.UPLOADS_DIR, 
            cls.OUTPUTS_DIR, 
            cls.MODELS_DIR, 
            cls.SAMPLE_DATA_DIR, 
            cls.DATA_DIR,
            cls.DEMO_SAMPLES_DIR,
            cls.DEMO_SCENARIOS_DIR
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    @classmethod
    def cleanup_old_files(cls):
        """Clean up uploaded and output videos older than FILE_CLEANUP_HOURS to conserve disk space."""
        import time
        max_age_seconds = cls.FILE_CLEANUP_HOURS * 3600
        now = time.time()
        for folder in [cls.UPLOADS_DIR, cls.OUTPUTS_DIR]:
            try:
                for file_path in folder.iterdir():
                    if file_path.is_file() and not file_path.name.startswith("."):
                        if now - file_path.stat().st_mtime > max_age_seconds:
                            try:
                                file_path.unlink()
                            except Exception:
                                pass
            except Exception:
                pass

# Ensure directories exist on module import
Config.ensure_directories()
