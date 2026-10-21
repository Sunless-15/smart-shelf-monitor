# Project Progress Tracker

## Project summary
We are building the "ShelfSense" (Intelligent Empty Shelf, Low Stock, and Misplaced Product Monitoring System) - a full-stack computer vision application detecting empty shelf slots, counting stock, flagging misplaced products, predicting upcoming shortages from historical trends, and providing a responsive modern bento-grid web dashboard. The tech stack is Python 3.10+ (Flask, Ultralytics YOLOv8, OpenCV, PyMongo) on the backend and React (Vite) on the frontend. Key decisions: no Raspberry Pi (all processing runs on the PC), MongoDB with automatic in-memory/JSON fallback, and a pluggable video source layer where an ESP32-CAM plugs in later via an HTTP/MJPEG stream URL with no code changes.

## How to resume (READ THIS FIRST)
1. Read this whole file.
2. Read the "Current task" and "Next steps" sections.
3. Run `git status` and `git log --oneline -10` to see the real state of the code.
4. Check that what is marked DONE actually exists and runs. Fix mismatches before moving on.
5. Continue from "Current task". Do not redo work marked DONE unless it is broken.

## Current task
Phase 9: YOLO training - Step 1: Get SKU-110K and build subset
- Step 0 completed: CUDA 12.6 PyTorch (2.14.1+cu126, torchvision 0.29.1+cu126) verified with NVIDIA GeForce RTX 4060 Laptop GPU (8 GB VRAM). Ultralytics 8.4.161 verified. Free disk space on drive D is 149.6 GB.
- Starting Step 1: Downloading SKU-110K via Ultralytics dataset loader into D:/project/smart shelf/datasets/SKU-110K.
- After download: Will construct dataset_sku_subset (1,500 train images, 300 val images, filtered for 10-100 boxes if applicable, seed 42) with single class 0: product, write data.yaml, validate, and generate docs/sku_subset_report.md.

## Next steps (in order)
- [x] Step 0: Install CUDA-enabled PyTorch into venv, verify GPU detection and ultralytics (DONE)
- [ ] Step 1: Download SKU-110K, build 1,500 train / 300 val subset with data.yaml, generate docs/sku_subset_report.md
- [ ] Step 2: Stage 1 training (products) on SKU-110K subset with yolov8s.pt in background, monitor & report metrics
- [ ] Step 3: Check custom shelf dataset for Stage 2 (classes: product, empty_slot); wait or configure splits
- [ ] Step 4: Stage 2 training (fine-tune shelf_v1 from Stage 1 best.pt)
- [ ] Step 5: Honest evaluation on test split, confusion matrix, sample predictions to docs/sample_predictions/ and docs/training_results.md
- [ ] Step 6: Plug shelf_v1.pt into backend, integrate empty_slot logic into stock engine, verify pytest suite
- [ ] Step 7: Update PROGRESS.md and project docs with final measured numbers

## Phase checklist
- [x] Phase 1: Backend skeleton, config, DB layer, video source layer (DONE)
- [x] Phase 2: YOLO detection, zone and stock logic, prediction, alerts, live pipeline (DONE)
- [x] Phase 3: All API endpoints including video upload jobs (DONE)
- [x] Phase 4: React dashboard (6 pages), responsive and PWA basics (DONE)
- [x] Phase 5: End-to-end integration testing (DONE)
- [x] Phase 6: README, dataset configuration, training helper, and final cleanup (DONE)
- [x] Phase 7: Public deployment (cloud-ready backend, camera agent, auth, Vercel/Render/Atlas configs, DEPLOYMENT.md) (DONE)
- [x] Phase 8: Bento Grid UI Redesign (Neon-Lime accent, floating sidebar, mixed white/lime/dark cards, half-donut & hatched bar charts, mobile pill bar) (DONE)
- [ ] Phase 9: YOLO training (Two-stage SKU-110K subset & shelf fine-tuning, evaluation, backend integration)

## Completed work log
- 2026-10-21 20:40: Completed Phase 9 Step 0: Verified hardware and environment. Resolved CPU PyTorch limitation by installing CUDA 12.6 PyTorch build (torch 2.14.1+cu126, torchvision 0.29.1+cu126) in d:\\project\\venv. Verified torch.cuda.is_available() == True, GPU name: NVIDIA GeForce RTX 4060 Laptop GPU (8188 MiB VRAM), Ultralytics 8.4.161. Verified 149.6 GB disk space available on drive D. Configured ultralytics datasets_dir to D:/project/smart shelf/datasets. (Files: PROGRESS.md)
- 2026-10-17 14:28: Resolved login connection issue: Terminated stale backend background process running pre-auth codebase, restarted Flask with live `/login` endpoint and JWT session token generation, relaxed local dev CORS policy (`origins: "*"`), and made `API_BASE` dynamically match current browser protocol & host. Verified 37/37 pytest test suite passes and login succeeds with HTTP 200. (Files: backend/app.py, backend/tests/test_e2e_live.py, dashboard/src/services/api.js, PROGRESS.md)
- 2026-10-17 14:15: Completed Phase 8 UI Redesign: Built dark-first bento grid dashboard with neon-lime (#E4FF1A) signature accent, mixed dark/white/lime card rhythm, 24-28px radius, pill buttons and segmented tabs, floating rounded sidebar with expandable Overview card, 4-row bento dashboard layout (greeting header with tall '+' button + white and lime stat cards, shelf status half-donut chart with lime total bubble, alerts bar chart with diagonal hatched bar on lime card, live annotated camera feed card with LIVE & FPS pills, wide white alert card with View Zone / Acknowledge pills, and dark rounded shelf zones table with route connector dots and pill filter tabs). Updated all secondary views and modals. Tested and confirmed 37/37 pytest test suite passes and Vite production build compiles with 0 errors. (Files: dashboard/src/index.css, dashboard/src/App.jsx, dashboard/src/pages/LiveDashboard.jsx, dashboard/src/components/Sidebar.jsx, dashboard/src/components/BottomNav.jsx, dashboard/src/components/Header.jsx, dashboard/src/components/LoginModal.jsx, dashboard/src/pages/AlertsView.jsx, dashboard/src/pages/AnalyticsView.jsx, dashboard/src/pages/VideoUploadView.jsx, dashboard/src/pages/ZonesSettingsView.jsx, dashboard/index.html, PROGRESS.md)
- 2026-10-17 13:40: Completed Phase 7: Made backend cloud-ready (dynamic PORT, Gunicorn 1 worker / 4 threads, opencv-python-headless in requirements-prod.txt, CPU PyTorch, frame resize to 640px, MODEL_URL auto-download, strict CORS_ORIGINS, uploads size & cleanup limits); created standalone camera agent (agent/camera_agent.py, agent/.env, scripts/run_agent.bat) with retry/backoff and POST /ingest-frame; implemented JWT authentication with 48-byte HMAC key, route protection with @require_auth, in-memory rate limiting, and safe path checks; upgraded React frontend with dynamic VITE_API_URL resolver, LoginModal, lock/logout action, cloud cold-start waking up banner, vercel.json SPA rewrite, and PWA service worker zero API caching; created backend/Dockerfile, .dockerignore, render.yaml blueprint, docker-compose.yml; authored comprehensive DEPLOYMENT.md; verified 37/37 pytest tests and Vite build succeed with zero errors.
- 2026-10-17 13:01: Completed Phase 6: Authored comprehensive project README.md, created dataset/dataset.yaml and dataset/LABELING_GUIDE.md, built automated YOLOv8 transfer learning script train.py with automatic best.pt model deployment.
- 2026-10-17 12:53: Completed Phase 5: Executed live end-to-end integration tests (backend port 5000 and frontend port 5173 running simultaneously).
- 2026-10-17 12:46: Completed Phase 4: Initialized React Vite app, built custom responsive design system, implemented all 6 pages, set up PWA manifest and service worker.
- 2026-10-17 12:35: Completed Phase 3: Implemented all API endpoints (/alerts, /alerts/<id>/ack, /zones CRUD, /history, /metrics, /upload-video, /job-status, /job-result, /outputs/<file>), built background video processing worker with FFmpeg H.264 transcoding.
- 2026-10-17 12:25: Created AGENT_RULES.md, PROGRESS.md, .gitignore and verified 21/21 pytest tests pass.
- 2026-10-17 12:20: Completed Phase 2: Live monitoring background pipeline with deduplicated alerts and history logging.
- 2026-10-17 12:17: Completed Phase 2: Shortage prediction engine estimating depletion rates, minutes to low stock, and minutes to empty via linear regression.
- 2026-10-17 12:16: Completed Phase 2: Stock counting, zone occupancy fallback, misplaced item detection, and visual frame annotation.
- 2026-10-17 12:15: Completed Phase 2: YOLOv8 detector wrapper with normalized coordinates, confidence thresholding, and latency measurement.
- 2026-10-17 12:12: Completed Phase 1: Backend skeleton, configuration with .env and defaults, MongoDB database manager with in-memory JSON fallback, pluggable video source layer.

## Known issues / bugs
- None. Backend passes all 37 unit tests and live end-to-end integration tests. Frontend builds with 0 errors.

## Decisions and notes
- Bento Grid Styling: Neon-lime `#E4FF1A` signature accent with pitch black text for WCAG AA compliance. Mixed color bento rhythm (dark `#161616`, solid white `#FFFFFF`, solid lime `#E4FF1A`).
- Typography: Plus Jakarta Sans with tabular figures for large numbers and metrics.
- Mobile Adaptation: Floating rounded bottom navigation bar on screens under 768px, single-column bento stacking, responsive table to cards.

## How to run and test
- Run all unit tests:
  `& "d:\project\venv\Scripts\python.exe" -m pytest -v "d:\project\smart shelf\backend\tests"`
- Build frontend:
  `cd "d:\project\smart shelf\dashboard" && npm.cmd run build`
- Run both Backend & Frontend simultaneously:
  `.\scripts\run_all.bat`
- Open dashboard:
  `http://localhost:5173`

