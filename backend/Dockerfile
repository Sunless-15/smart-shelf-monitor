# =============================================================================
# Production Dockerfile for Smart Shelf Backend
# Optimized for free/low-resource cloud hosts (Render, Hugging Face, Railway)
# Uses Python 3.10-slim, CPU-only PyTorch, and headless OpenCV
# =============================================================================

FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    CLOUD_MODE=true

WORKDIR /app

# Install system dependencies:
# - ffmpeg: Required for H.264 browser-compatible video transcoding
# - libgl1, libglib2.0-0: Required by OpenCV
# - curl: Required for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight CPU-only PyTorch directly from official wheel index
# This reduces Docker image size by >2.5 GB compared to default CUDA PyTorch!
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cpu

# Install Python production requirements
COPY requirements-prod.txt /app/requirements-prod.txt
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application source code
COPY . /app

# Ensure storage directories exist
RUN mkdir -p /app/uploads /app/outputs /app/models /app/data /app/sample_data

# Expose port (Render sets $PORT dynamically)
EXPOSE 5000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

# Launch production Gunicorn server:
# NOTE ON WORKERS:
# Exactly 1 worker process is mandatory because the live CV pipeline thread,
# the video source state, in-memory frame cache, and fallback database
# must reside in a single process memory. 4 worker threads handle concurrent HTTP requests.
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - app:app
