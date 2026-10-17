# Project Progress Tracker

## Project summary
We are building the "Intelligent Empty Shelf and Low Stock Monitoring System" - a full-stack computer vision application detecting empty shelf slots, counting stock, flagging misplaced products, predicting upcoming shortages from historical trends, and providing a responsive web dashboard. The tech stack is Python 3.10+ (Flask, Ultralytics YOLOv8, OpenCV, PyMongo) on the backend and React (Vite) on the frontend. Key decisions: no Raspberry Pi (all processing runs on the PC), MongoDB with automatic in-memory/JSON fallback, and a pluggable video source layer where an ESP32-CAM plugs in later via an HTTP/MJPEG stream URL with no code changes.

## How to resume (READ THIS FIRST)
1. Read this whole file.
2. Read the "Current task" and "Next steps" sections.
3. Run `git status` and `git log --oneline -10` to see the real state of the code.
4. Check that what is marked DONE actually exists and runs. Fix mismatches before moving on.
5. Continue from "Current task". Do not redo work marked DONE unless it is broken.

## Current task
Phase 3: building the remaining API endpoints, starting with POST /upload-video and the background video-processing job.

## Next steps (in order)
- [ ] Phase 3: all API endpoints including video upload jobs (/upload-video, /job-status, /job-result, /outputs, /metrics, zones CRUD, alerts list/ack, history, source switching)
- [ ] Phase 4: React dashboard (6 pages), responsive and PWA basics
- [ ] Phase 5: End-to-end integration testing
- [ ] Phase 6: README, scripts, cleanup

## Phase checklist
- [x] Phase 1: Backend skeleton, config, DB layer, video source layer (DONE)
- [x] Phase 2: YOLO detection, zone and stock logic, prediction, alerts, live pipeline (DONE)
- [ ] Phase 3: All API endpoints including video upload jobs
- [ ] Phase 4: React dashboard (6 pages), responsive and PWA basics
- [ ] Phase 5: End-to-end integration testing
- [ ] Phase 6: README, scripts, cleanup

## Completed work log
- 2026-10-17 12:25: Created AGENT_RULES.md, PROGRESS.md, .gitignore and verified 21/21 pytest tests pass across detection, stock, prediction, pipeline, and sources. (Files: PROGRESS.md, AGENT_RULES.md, .gitignore)
- 2026-10-17 12:20: Completed Phase 2: Live monitoring background pipeline with deduplicated alerts and history logging, added /shelf-status and /live-stream endpoints, wrote 15 new unit tests. (Files: backend/pipeline.py, backend/app.py, backend/tests/test_pipeline.py)
- 2026-10-17 12:17: Completed Phase 2: Shortage prediction engine estimating depletion rates, minutes to low stock, and minutes to empty via linear regression. (Files: backend/inference/predict.py, backend/tests/test_predict.py)
- 2026-10-17 12:16: Completed Phase 2: Stock counting, zone occupancy fallback, misplaced item detection, and visual frame annotation. (Files: backend/inference/stock.py, backend/tests/test_stock.py)
- 2026-10-17 12:15: Completed Phase 2: YOLOv8 detector wrapper with normalized coordinates, confidence thresholding, and latency measurement. (Files: backend/inference/detect.py, backend/models/yolov8n.pt, backend/tests/test_detect.py)
- 2026-10-17 12:12: Completed Phase 1: Backend skeleton, configuration with .env and defaults, MongoDB database manager with in-memory JSON fallback and zone auto-seeding, pluggable video source layer (webcam, looped video, MJPEG stream, synthetic demo generator), /health, /source, /live-frame endpoints, and unit tests. (Files: backend/config.py, backend/.env, backend/.env.example, backend/db.py, backend/sources.py, backend/app.py, backend/tests/test_phase1.py, scripts/run_backend.bat)

## Known issues / bugs
- None currently. All 21 unit tests are passing.

## Decisions and notes
- Project location: Main git repo is located at `d:\project\smart shelf`. A directory junction `d:\project\smart-shelf-monitor` <<===>> `d:\project\smart shelf` is created so both path styles work identically.
- Virtual environment: Located at `d:\project\venv` (Python 3.14.7) containing Flask, Ultralytics, PyMongo, OpenCV, Torch.
- FFmpeg: Local binary auto-detected at `d:\project\ffmpeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe`.
- MongoDB: Running on `mongodb://localhost:27017` with database `shelf_monitor`. In-memory JSON store acts as automatic fallback at `backend/data/fallback_store.json`.
- Pretrained model: `models/yolov8n.pt` downloaded and tested. Custom `best.pt` can be dropped in later.
- Normalized coordinates: Zone coordinates are normalized `0.0 - 1.0` so zones remain resolution-independent across webcam, 1080p uploads, and ESP32-CAM streams.
- Port allocations: Backend runs on `http://0.0.0.0:5000` with CORS enabled for all origins. Frontend Vite server runs on `http://0.0.0.0:5173`.

## How to run and test
- Run all unit tests:
  `& "d:\project\venv\Scripts\python.exe" -m pytest -v "d:\project\smart shelf\backend\tests"`
- Run backend server:
  `.\scripts\run_backend.bat`
  or
  `& "d:\project\venv\Scripts\python.exe" "d:\project\smart shelf\backend\app.py"`
- Test Health API:
  `Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" | ConvertTo-Json -Depth 5`
- Test Shelf Status API:
  `Invoke-RestMethod -Uri "http://127.0.0.1:5000/shelf-status" | ConvertTo-Json -Depth 6`
- View live stream in browser:
  Open `http://127.0.0.1:5000/live-stream` in any browser.

## Open questions for the user
- None. Ready for Phase 3.
