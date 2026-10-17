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
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # Database (MongoDB with Fallback)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "shelf_monitor")
    MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "2000"))
    
    # Storage Directories
    UPLOADS_DIR = BACKEND_DIR / "uploads"
    OUTPUTS_DIR = BACKEND_DIR / "outputs"
    MODELS_DIR = BACKEND_DIR / "models"
    SAMPLE_DATA_DIR = BACKEND_DIR / "sample_data"
    DATA_DIR = BACKEND_DIR / "data"
    
    # Model
    MODEL_PATH = os.getenv("MODEL_PATH", str(MODELS_DIR / "yolov8n.pt"))
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
    
    # Video Source Defaults
    # Types: "webcam", "video", "stream"
    DEFAULT_SOURCE_TYPE = os.getenv("DEFAULT_SOURCE_TYPE", "video")
    DEFAULT_SOURCE_VALUE = os.getenv(
        "DEFAULT_SOURCE_VALUE", 
        str(SAMPLE_DATA_DIR / "sample_shelf.mp4")
    )
    
    # Video Streaming & Pipeline
    STREAM_FPS = int(os.getenv("STREAM_FPS", "15"))
    PIPELINE_FPS = float(os.getenv("PIPELINE_FPS", "2.0"))
    
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
            cls.DATA_DIR
        ]:
            folder.mkdir(parents=True, exist_ok=True)

# Ensure directories exist on module import
Config.ensure_directories()
