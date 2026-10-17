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
All phases (1 through 6) completed, tested, and verified end-to-end!

## Next steps (in order)
- Project complete. Run `.\scripts\run_all.bat` to launch both servers.
- Optional: Collect custom dataset images, run `python train.py`, and update `backend/.env` with `MODEL_PATH=models/best.pt`.

## Phase checklist
- [x] Phase 1: Backend skeleton, config, DB layer, video source layer (DONE)
- [x] Phase 2: YOLO detection, zone and stock logic, prediction, alerts, live pipeline (DONE)
- [x] Phase 3: All API endpoints including video upload jobs (DONE)
- [x] Phase 4: React dashboard (6 pages), responsive and PWA basics (DONE)
- [x] Phase 5: End-to-end integration testing (DONE)
- [x] Phase 6: README, dataset configuration, training helper, and final cleanup (DONE)

## Completed work log
- 2026-10-17 13:01: Completed Phase 6: Authored comprehensive project README.md (team table, ASCII architecture diagram, quickstart, mobile WiFi setup, ESP32-CAM instructions, API table, testing commands, folder structure), created dataset/dataset.yaml and dataset/LABELING_GUIDE.md, built automated YOLOv8 transfer learning script train.py with automatic best.pt model deployment, registered pytest e2e markers, verified 26/26 unit tests and frontend production build pass cleanly. (Files: README.md, dataset/dataset.yaml, dataset/LABELING_GUIDE.md, train.py, pytest.ini, PROGRESS.md)
- 2026-10-17 12:53: Completed Phase 5: Executed live end-to-end integration tests (backend port 5000 and frontend port 5173 running simultaneously), verified real-time YOLO inference, JPEG snapshots, asynchronous video upload and FFmpeg H.264 transcoding job, and verified responsive web delivery. (Files: backend/tests/test_e2e_live.py, PROGRESS.md)
- 2026-10-17 12:46: Completed Phase 4: Initialized React Vite app, built custom responsive design system (dark/light themes, mobile-first bottom nav, desktop sidebar), implemented all 6 pages (Live Dashboard, Alerts Center, Analytics with Recharts, Video Upload Studio, Zones & Settings Editor, Demo Mode Toggle), set up PWA manifest and service worker, added Windows batch scripts (run_frontend.bat, run_all.bat, setup.bat), and confirmed zero-error production build. (Files: dashboard/, scripts/)
- 2026-10-17 12:35: Completed Phase 3: Implemented all API endpoints (/alerts, /alerts/<id>/ack, /zones CRUD, /history, /metrics, /upload-video, /job-status, /job-result, /outputs/<file>), built background video processing worker with FFmpeg H.264 transcoding and timeline generation, and verified 26/26 unit tests pass. (Files: backend/video_jobs.py, backend/app.py, backend/db.py, backend/tests/test_phase3.py)
- 2026-10-17 12:25: Created AGENT_RULES.md, PROGRESS.md, .gitignore and verified 21/21 pytest tests pass across detection, stock, prediction, pipeline, and sources. (Files: PROGRESS.md, AGENT_RULES.md, .gitignore)
- 2026-10-17 12:20: Completed Phase 2: Live monitoring background pipeline with deduplicated alerts and history logging, added /shelf-status and /live-stream endpoints, wrote 15 new unit tests. (Files: backend/pipeline.py, backend/app.py, backend/tests/test_pipeline.py)
- 2026-10-17 12:17: Completed Phase 2: Shortage prediction engine estimating depletion rates, minutes to low stock, and minutes to empty via linear regression. (Files: backend/inference/predict.py, backend/tests/test_predict.py)
- 2026-10-17 12:16: Completed Phase 2: Stock counting, zone occupancy fallback, misplaced item detection, and visual frame annotation. (Files: backend/inference/stock.py, backend/tests/test_stock.py)
- 2026-10-17 12:15: Completed Phase 2: YOLOv8 detector wrapper with normalized coordinates, confidence thresholding, and latency measurement. (Files: backend/inference/detect.py, backend/models/yolov8n.pt, backend/tests/test_detect.py)
- 2026-10-17 12:12: Completed Phase 1: Backend skeleton, configuration with .env and defaults, MongoDB database manager with in-memory JSON fallback and zone auto-seeding, pluggable video source layer (webcam, looped video, MJPEG stream, synthetic demo generator), /health, /source, /live-frame endpoints, and unit tests. (Files: backend/config.py, backend/.env, backend/.env.example, backend/db.py, backend/sources.py, backend/app.py, backend/tests/test_phase1.py, scripts/run_backend.bat)

## Known issues / bugs
- None. Backend passes all 26 unit tests and live end-to-end integration tests. Frontend builds with 0 errors.

## Decisions and notes
- Video Processing Jobs: Handled asynchronously in background worker threads. Sampled every ~0.5s for fast processing. Annotated output is transcoded to H.264 using FFmpeg (from `d:\project\ffmpeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe`) with fallback to raw mp4v, ensuring native playback in modern browsers.
- Universal ID Filter: Uses `id_filter` supporting both string IDs and MongoDB `ObjectId` seamlessly across FallbackDB and PyMongo.
- Pretrained model: `models/yolov8n.pt` downloaded and tested. Custom `best.pt` can be dropped in later.
- Normalized coordinates: Zone coordinates are normalized `0.0 - 1.0` so zones remain resolution-independent across webcam, 1080p uploads, and ESP32-CAM streams.
- Port allocations: Backend runs on `http://0.0.0.0:5000` with CORS enabled for all origins. Frontend Vite server runs on `http://0.0.0.0:5173` with `--host` enabled.

## How to run and test
- Run all unit tests:
  `& "d:\project\venv\Scripts\python.exe" -m pytest -v "d:\project\smart shelf\backend\tests"`
- Run live end-to-end integration test:
  `& "d:\project\venv\Scripts\python.exe" "d:\project\smart shelf\backend\tests\test_e2e_live.py"`
- Build frontend:
  `cd "d:\project\smart shelf\dashboard" && npm.cmd run build`
- Run both Backend & Frontend simultaneously:
  `.\scripts\run_all.bat`
- Run Backend only:
  `.\scripts\run_backend.bat`
- Run Frontend only:
  `.\scripts\run_frontend.bat`
- Open dashboard:
  PC Browser: `http://localhost:5173`
  Mobile Phone (same WiFi): `http://<your-pc-ip>:5173`

## Open questions for the user
- None. Ready for Phase 6 (Documentation, dataset yaml, training script, final cleanup).
