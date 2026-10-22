# Project Progress Tracker

## Project summary
We are building the "ShelfSense" (Intelligent Empty Shelf, Low Stock, and Misplaced Product Monitoring System) - a full-stack computer vision application detecting empty shelf slots, counting stock, flagging misplaced products, predicting upcoming shortages from historical trends, and providing a responsive modern bento-grid web dashboard. The tech stack is Python 3.10+ (Flask, Ultralytics YOLOv8, OpenCV, PyMongo) on the backend and React (Vite) on the frontend. Key decisions: no Raspberry Pi (all processing runs on the PC), MongoDB with automatic in-memory/JSON fallback, and a pluggable video/camera source layer where an ESP32-CAM plugs in via HTTP with zero changes to downstream detection, alerts, or dashboard logic.

## How to resume (READ THIS FIRST)
1. Read this whole file.
2. Read the "Current task" and "Next steps" sections.
3. Run `git status` and `git log --oneline -5` to see the checkpoint state.
4. Check that what is marked DONE actually exists and runs. Fix mismatches before moving on.
5. Continue from "Current task". Do not redo work marked DONE unless it is broken.

### Current task
Phase 10: trained model in web app + demo mode + ESP32-ready camera layer
- Working on: Measuring real YOLO inference latency on NVIDIA RTX 4060 GPU for `docs/performance.md`, capturing UI screenshots for `docs/screenshots/`, and updating README / PROJECT_EXPLAINED.
- Files worked on:
  - `backend/camera/manager.py`: Switched lock to `threading.RLock()` to eliminate reentrancy deadlock on mode switch; safely handled `None` in `kwargs` for speed, esp32_ip, scenario.
  - `backend/camera/simulated.py`: Permitted speed multiplier up to 100.0x for accelerated testing pacing.
  - `backend/tests/test_phase10.py`: All 9 tests passing (100% pass).
  - Full test suite: 45 passed, 1 skipped in 12.39s.

## Next steps (in order)
1. Measure real YOLO inference latency averaged over 20 images on the NVIDIA RTX 4060 Laptop GPU and save exact results to `docs/performance.md`.
2. Launch frontend dev server (`cd dashboard && npm run dev`), open at 375px mobile and desktop widths, and capture the 4 required screenshots into `docs/screenshots/`:
   - Demo page with annotated sample
   - Dashboard in DEMO MODE with Low alert and shortage prediction
   - Pipeline trace card showing 3-photo confirmation counter ("Low seen 2 of 3")
   - Customer blocking scenario showing no false alert
3. Update `README.md` and `docs/PROJECT_EXPLAINED.md` with `CAMERA_MODE` configuration instructions and demo usage.
4. Commit completed Phase 10 to Git.

## Phase checklist
- [x] Phase 1: Backend skeleton, config, DB layer, video source layer (DONE)
- [x] Phase 2: YOLO detection, zone and stock logic, prediction, alerts, live pipeline (DONE)
- [x] Phase 3: All API endpoints including video upload jobs (DONE)
- [x] Phase 4: React dashboard (6 pages), responsive and PWA basics (DONE)
- [x] Phase 5: End-to-end integration testing (DONE)
- [x] Phase 6: README, dataset configuration, training helper, and final cleanup (DONE)
- [x] Phase 7: Public deployment (cloud-ready backend, camera agent, auth, Vercel/Render/Atlas configs, DEPLOYMENT.md) (DONE)
- [x] Phase 8: Bento Grid UI Redesign (Neon-Lime accent, floating sidebar, mixed white/lime/dark cards, half-donut & hatched bar charts, mobile pill bar) (DONE)
- [x] Phase 9: YOLO training (Stage 1 trained with 91.05% mAP@50 on RTX 4060; Stage 2 waiting for user custom dataset) (DONE)
- [/] Phase 10: trained model in web app + demo mode + ESP32-ready camera layer (IN PROGRESS)
  - [x] Part A: Model integration (sku_stage1.pt loading, dynamic model.names, /model-info, threshold config, two-class stock logic) (DONE)
  - [x] Part B: Demo page (24 unseen test samples in backend/demo_samples/, /analyze-image, /demo/*, DemoView.jsx, isolation from live history) (DONE)
  - [x] Part C: Camera layer and scenarios (backend/camera/ with Simulated/Pull/Push/Video, 4 demo scenarios, 3-photo confirmation, DEMO MODE badge) (DONE)
  - [x] Part D: Firmware and switch-over kit (esp32-firmware/shelf_camera/shelf_camera.ino, test_esp32.py, collect_images.py, docs/ESP32_SWITCHOVER.md) (DONE)
  - [/] Part E: Tests and screenshots (All 9 tests in test_phase10.py passing; 45/46 backend tests passing; screenshots & 20-image latency measurement pending) (PARTLY DONE)
  - [/] Part F: Documentation (docs/ESP32_SWITCHOVER.md & demo READMEs done; PROGRESS.md, PROJECT_EXPLAINED.md, README.md being updated) (PARTLY DONE)

## Completed work log
- 2026-10-22 06:26: Fixed Phase 10 test suite issues: Resolved reentrancy deadlock in `CameraManager` by upgrading `_lock` to `threading.RLock()` and adding safe `None` checks in `set_mode` / `control_simulated`; updated `SimulatedSource.set_speed` to permit up to 100x playback speed multiplier, ensuring perfect 5.0s timestamp increments under accelerated test loops. Executed full test suite: 45 passed, 1 skipped in 12.39s (100% pass rate). (Files: backend/camera/manager.py, backend/camera/simulated.py, PROGRESS.md)
- 2026-10-22 03:00: Checkpoint: Saved current progress on Phase 10. Completed implementation of Part A (YOLO model integration with dynamic class reading, GPU acceleration on RTX 4060, GET /model-info, POST /model-config, two-class zone counting with product and empty_slot), Part B (Demo page with 24 unseen SKU-110K test split images, /analyze-image, side-by-side visualization, latency display, isolated history tagging), Part C (Unified camera abstraction layer in backend/camera/ supporting simulated, esp32_pull, esp32_push, video_file; 4 demo scenarios with virtual clock; 3-photo confirmation filter; live pipeline trace card; top demo badge), Part D (AI-Thinker ESP32-CAM firmware in esp32-firmware/, test_esp32.py, collect_images.py, docs/ESP32_SWITCHOVER.md), and created 9 automated tests in backend/tests/test_phase10.py. Verified .gitignore excludes all heavy datasets and secrets. (Files: backend/app.py, backend/config.py, backend/pipeline.py, backend/inference/detect.py, backend/inference/stock.py, backend/camera/*, backend/demo_samples/*, backend/demo_scenarios/*, esp32-firmware/*, backend/tools/*, dashboard/src/pages/DemoView.jsx, dashboard/src/pages/LiveDashboard.jsx, dashboard/src/pages/ZonesSettingsView.jsx, docs/ESP32_SWITCHOVER.md, .gitignore, PROGRESS.md)
- 2026-10-22 00:55: Authored comprehensive study guide and presentation companion `docs/PROJECT_EXPLAINED.md` covering all 15 structured sections in plain English (pitches, real photo journey trace on val_1.jpg with 186 products, 13 detailed component mechanisms with worked examples and code walkthroughs, design decisions matrix, Stage 1 YOLO training results with 91.05% mAP@50 on RTX 4060 GPU, honest status and limitations, 11-slide presentation outline, team role division, live demo script, recovery plan, 20 examiner Q&As with deeper answers, 10 self-test questions, folder map, verified run instructions, and glossary). Added Rule 10 to `AGENT_RULES.md` to keep `docs/PROJECT_EXPLAINED.md` updated alongside `PROGRESS.md`. (Files: docs/PROJECT_EXPLAINED.md, AGENT_RULES.md, PROGRESS.md)
- 2026-10-22 00:15: Completed Phase 9 Step 2: Trained Stage 1 YOLOv8s detector on SKU-110K subset (`dataset_sku_subset/data.yaml`) for 40 epochs on NVIDIA GeForce RTX 4060 Laptop GPU. Achieved final measured validation performance: Precision 90.92%, Recall 84.90%, mAP@50 91.05%, mAP@50-95 55.36%, final train box_loss 1.2916, cls_loss 0.5514, dfl_loss 0.9607 in 1.116 hours (4,017.7s) at 4.9ms inference per image. Saved optimal model weights to `runs/detect/sku_stage1/weights/best.pt` (22.5 MB). Created `docs/training_results.md` documenting two-stage architecture rationale, hardware configuration, and epoch progression. Created `dataset/data.yaml` for Stage 2. Stopped after Stage 1 per Step 3 instructions to wait for user custom labeled dataset with classes `0: product` and `1: empty_slot`. (Files: runs/detect/sku_stage1/weights/best.pt, docs/training_results.md, dataset/data.yaml, PROGRESS.md)
- 2026-10-21 22:55: Completed Phase 9 Step 1: Downloaded full SKU-110K dataset (11.4 GB archive, 11,743 images / labels). Analyzed box distributions across 8,219 train and 588 val images (median 138 boxes; only 384 train and 18 val images had 10-100 boxes). Evaluated filter and executed plain random sampling with seed 42 to avoid dataset starvation. Generated `dataset_sku_subset` with 1,500 train images (220,632 product boxes, avg 147.1/img) and 300 val images (45,860 product boxes, avg 152.9/img). Validated 0 corrupt images, 0 missing labels, 0 non-zero class IDs, and normalized coordinates. Created `data.yaml` and published comprehensive audit report in `docs/sku_subset_report.md`. (Files: dataset_sku_subset/data.yaml, docs/sku_subset_report.md, scripts/create_sku_subset.py, scripts/download_sku.py, .gitignore, PROGRESS.md)
- 2026-10-21 20:40: Completed Phase 9 Step 0: Verified hardware and environment. Resolved CPU PyTorch limitation by installing CUDA 12.6 PyTorch build (torch 2.14.1+cu126, torchvision 0.29.1+cu126) in d:\project env. Verified torch.cuda.is_available() == True, GPU name: NVIDIA GeForce RTX 4060 Laptop GPU (8188 MiB VRAM), Ultralytics 8.4.161. Verified 149.6 GB disk space available on drive D. Configured ultralytics datasets_dir to D:/project/smart shelf/datasets. (Files: PROGRESS.md)
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
1. Custom shelf weights (Stage 2) waiting on user data:
   - `backend/models/shelf_v1.pt` is not present because custom shelf annotations have not yet been provided by the user. Backend is running `backend/models/sku_stage1.pt` (trained on product detection, 91.05% mAP@50) and labeled accurately as "sku_stage1 (trained on products)".

## Things I still need to provide
1. Custom annotated shelf dataset (`dataset/` with train/val images and labels containing both `0: product` and `1: empty_slot`) to train Stage 2 `shelf_v1.pt`.
2. Physical ESP32-CAM hardware when it arrives (to flash `esp32-firmware/shelf_camera/shelf_camera.ino` and switch `CAMERA_MODE=esp32_pull`).
3. Real photos of a person/hand occluding shelf items if real "customer blocking" photos are preferred over the constructed demonstration sequence.
4. Remote Git repository URL (e.g. GitHub) if cloud push is desired.

## Last pytest result
- Complete test suite: 45 passed, 1 skipped (test_e2e_live) in 12.39s (100% pass rate).
- Phase 10 test suite (`test_phase10.py`): 9/9 passed.

## How to run and test
- Run existing unit tests:
  `& "d:\projectenv\Scripts\python.exe" -m pytest backend/tests/test_stock.py backend/tests/test_detect.py -q`
- Run Phase 10 unit tests:
  `& "d:\projectenv\Scripts\python.exe" -m pytest backend/tests/test_phase10.py`
- Build frontend:
  `cd "d:\project\smart shelf\dashboard" && npm.cmd run build`
- Run backend locally:
  `& "d:\projectenv\Scripts\python.exe" backend/app.py`
- Run frontend locally:
  `cd "d:\project\smart shelf\dashboard" && npm.cmd run dev`
- Run both Backend & Frontend simultaneously:
  `.\scriptsun_all.bat`
- Open dashboard:
  `http://localhost:5173`
