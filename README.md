# Intelligent Empty Shelf and Low Stock Monitoring System

A full-stack computer vision system that detects empty shelf spaces, counts inventory stock in real time, flags misplaced retail products, predicts upcoming stock shortages from historical trends, and delivers live insights on a responsive PC and mobile web dashboard.

Built for **Project Phase I, Department of Computer Science & Engineering, St. Thomas College of Engineering & Technology**.

---

## 👥 Team & Roles

| Name | Reg No | Role |
|---|---|---|
| **Shobin Bobby** | STC23CS075 | Team Lead — Architecture, Full-Stack Backend & Pipeline |
| **Sachu Sreejith** | STC23CS071 | Camera/Hardware Setup, Model Integration & Sources |
| **Vrinda T Vinod** | STC23CS083 | Dataset Preprocessing, Model Training & Verification |
| **Aiswarya M S** | MZW23CS002 | Dashboard / UI, GitHub Repository, Project Diary |

**Supervisor:** Prof. Teena M Thomas, Assistant Professor, Dept. of CSE

---

## 🌐 Live Cloud Deployment Guide
> 📖 **Deploying to the public internet?** Follow the complete, beginner-friendly step-by-step guide in [DEPLOYMENT.md](file:///d:/project/smart%20shelf/DEPLOYMENT.md) to launch the Frontend on **Vercel**, the Backend on **Render (Docker)**, Database on **MongoDB Atlas**, and stream local video via the **Camera Agent** for 100% free!

---

## 🏛️ System Architecture

### 1. Public Cloud Architecture (Vercel + Render + Atlas + Camera Agent)
```
 ┌────────────────────────┐
 │   Local Hardware (PC)  │
 │  • Laptop Webcam /     │
 │    ESP32-CAM stream    │
 │  • camera_agent.py     │
 └───────────┬────────────┘
             │ (POST /ingest-frame with X-API-Key)
             ▼
 ┌────────────────────────────────────────────────────────┐
 │         Render Web Service (Docker Container)          │
 │  • Gunicorn (1 worker, 4 threads)                      │
 │  • YOLOv8 Inference (CPU PyTorch, max 640px)           │
 │  • Zone Evaluation, Predictions, Alert Engine          │
 │  • REST API & Admin Authentication (/login)            │
 └───────────┬────────────────────────────────┬───────────┘
             │                                │
             ▼                                ▼
 ┌───────────────────────┐        ┌───────────────────────┐
 │   MongoDB Atlas (M0)  │        │     Vercel (PWA)      │
 │  • zones, alerts,     │        │  • React (Vite) App   │
 │    history, jobs      │        │  • Mobile Bottom Nav  │
 └───────────────────────┘        │  • Admin Login Screen │
                                  └───────────────────────┘
```

### 2. Local Architecture (Stand-alone PC)
```
                       ┌────────────────────────────────────────────────────────┐
                       │               Pluggable Video Source Layer             │
                       │   1. Laptop Webcam (cv2.VideoCapture(0))               │
                       │   2. Looped Video File (sample_shelf.mp4)              │
                       │   3. ESP32-CAM HTTP/MJPEG Stream (http://<ip>:81/stream)│
                       │   4. Remote Camera Agent (POST /ingest-frame)          │
                       └──────────────────────────┬─────────────────────────────┘
                                                  │
                                                  ▼
                                      Flask Backend (Python 3.10+)
                 ┌──────────────────────────────────────────────────────────────────┐
                 │ • YOLOv8 Object Detection (Normalized [x1, y1, x2, y2] boxes)    │
                 │ • Shelf Zone Stock Counter & Occupancy Fallback Logic            │
                 │ • Misplaced Product Detector (Expected Class vs Detected Class)  │
                 │ • Shortage Predictor (Linear Regression: Time-to-Empty / Low)    │
                 │ • Alert Engine with Cooldown Deduplication                       │
                 │ • Background Video Job Worker (FFmpeg H.264 Transcoder)          │
                 │ • JWT Dashboard Authentication & Rate Limiting                   │
                 └────────────────┬────────────────────────────────┬────────────────┘
                                  │                                │
                                  ▼                                ▼
                     MongoDB (Local Service)              React Vite Dashboard
               ┌──────────────────────────────────┐   ┌────────────────────────────────┐
               │ • zones (Configured boundaries)  │   │ • Live Annotated Video Feed    │
               │ • alerts (Anomaly history)       │   │ • Real-time Zone Capacity Cards│
               │ • history (Time-series logs)     │   │ • Recharts Trend Analytics     │
               │ • In-Memory / JSON Fallback Mode │   │ • Video Upload & Timeline Player│
               └──────────────────────────────────┘   │ • Zones & Video Source Settings│
                                                      │ • Mobile Bottom Nav & PWA Shell│
                                                      └────────────────────────────────┘
```

> **Key Architectural Decisions:**
> 1. **No Raspberry Pi**: All computer vision processing (YOLOv8 inference, stock logic, API, database) runs on the host PC or cloud container.
> 2. **Pluggable Video & Camera Agent**: Supports laptop webcams, looped disk videos, HTTP streams, and push ingest from remote camera agents with zero code changes.
> 3. **MongoDB Resilience**: If local MongoDB is unavailable or stopped, the backend automatically fails over to an in-memory/JSON store (`data/fallback_store.json`), allowing offline execution without crashing.

---

## 🚀 Quick Start Guide (Windows)

### Prerequisites
- **Python 3.10+** (tested on Python 3.14)
- **Node.js LTS (v18+)** & npm
- **MongoDB** (Local Windows service or MongoDB Community Server)
- **FFmpeg** (Local binary auto-detected in `d:\project\ffmpeg\`)

### 1. Installation
Clone the repository and run the automated setup script:
```cmd
scripts\setup.bat
```
*This will create the Python virtual environment (`venv`), install all backend dependencies, and run `npm install` for the React dashboard.*

### 2. Running Both Servers Concurrently
Double click or run:
```cmd
scripts\run_all.bat
```
This automatically launches:
- **Backend API Server**: `http://localhost:5000`
- **React Frontend Dashboard**: `http://localhost:5173`

*(Individual batch scripts `run_backend.bat` and `run_frontend.bat` are also available in `scripts/`).*

---

## 📱 Mobile Access Over Local WiFi

The system is configured out of the box for responsive mobile access on the same local network:

1. **Find your PC's Local IP Address**:
   Open PowerShell and run:
   ```powershell
   ipconfig
   ```
   Look for the **IPv4 Address** under your active Wi-Fi adapter (e.g. `192.168.1.15`).

2. **Allow Ports Through Windows Defender Firewall**:
   Run PowerShell as Administrator:
   ```powershell
   New-NetFirewallRule -DisplayName "SmartShelf Backend 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
   New-NetFirewallRule -DisplayName "SmartShelf Frontend 5173" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
   ```

3. **Open from Your Mobile Phone**:
   Open Chrome or Safari on your phone and browse to:
   ```
   http://192.168.1.15:5173
   ```
   - The frontend automatically routes API requests to `http://192.168.1.15:5000`.
   - The dashboard automatically adapts to a mobile-first viewport with a bottom navigation bar.
   - You can tap **"Add to Home Screen"** to install it as a standalone PWA.

---

## 📷 Pluggable Video Source & ESP32-CAM Setup

The video source layer ([`backend/sources.py`](file:///d:/project/smart%20shelf/backend/sources.py)) supports three interchangeable inputs:

| Source Type | Value Example | Description |
|---|---|---|
| `webcam` | `0` or `1` | Built-in laptop webcam or external USB camera |
| `video` | `sample_data/sample_shelf.mp4` | Looped demo video on disk for testing without a camera |
| `stream` | `http://192.168.1.100:81/stream` | ESP32-CAM HTTP/MJPEG stream endpoint |

### How to Switch to ESP32-CAM Later
When your ESP32-CAM module is powered on and connected to WiFi:
1. Note its IP address from the Serial Monitor (e.g., `192.168.1.100`).
2. Open the **Zones & Sources** tab on the web dashboard.
3. Select **ESP32-CAM Stream**, paste `http://192.168.1.100:81/stream`, and click **Apply Video Source**.
4. *Alternatively*, update [`backend/.env`](file:///d:/project/smart%20shelf/backend/.env) (or `agent/.env` if using the Camera Agent):
   ```ini
   SOURCE_TYPE=stream
   SOURCE_VALUE=http://192.168.1.100:81/stream
   ```
*No code modifications or recompilations are needed.*

---

## 📹 Running the Standalone Camera Agent (for Cloud Deployment)

When deploying the backend to the cloud (Render), the backend cannot access your local USB camera or home Wi-Fi ESP32-CAM. The **Camera Agent** runs on your PC next to the camera, captures frames, compresses them, and pushes them to your cloud backend via `POST /ingest-frame`:

1. Configure [`agent/.env`](file:///d:/project/smart%20shelf/agent/.env):
   ```ini
   BACKEND_URL=https://your-backend.onrender.com
   AGENT_API_KEY=shelf_agent_secret_key_2026
   SOURCE_TYPE=video
   SOURCE_VALUE=../backend/sample_data/sample_shelf.mp4
   INTERVAL_SECONDS=1.5
   ```
2. Launch the agent:
   ```cmd
   scripts\run_agent.bat
   ```
3. The live feed, inventory counts, and anomaly alerts will instantly appear on your public Vercel web app!

---

## ⚡ Alternative: Exposing PC-Hosted Backend via Cloudflare Tunnel

If you prefer to run the YOLOv8 model directly on your PC's CPU/GPU (for higher FPS than Render's free tier) while still having a public HTTPS URL:

1. Install Cloudflare Tunnel on Windows:
   ```powershell
   winget install --id Cloudflare.cloudflared
   ```
2. Start the local backend (`scripts\run_backend.bat`).
3. In a new PowerShell window, expose port 5000:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
4. Copy the temporary HTTPS URL provided by Cloudflare (e.g. `https://xxxx.trycloudflare.com`).
5. In your Vercel project settings, set `VITE_API_URL` to that Cloudflare URL.
> **Tradeoff:** Fast native PC performance, but only works while your PC is awake and connected to the internet.

---

## 🧠 Custom Trained YOLOv8 Model Deployment

1. **Annotate Shelf Images**:
   Follow [`dataset/LABELING_GUIDE.md`](file:///d:/project/smart%20shelf/dataset/LABELING_GUIDE.md) using Roboflow or LabelImg.
2. **Train the Model**:
   ```powershell
   & "d:\project\venv\Scripts\python.exe" train.py --epochs 50 --batch 16 --device cpu
   ```
3. **Deploy**:
   The script automatically copies the best weights to `backend/models/best.pt`.
4. Update [`backend/.env`](file:///d:/project/smart%20shelf/backend/.env):
   ```ini
   MODEL_PATH=models/best.pt
   ```
5. Restart the backend. The monitoring pipeline will immediately load your custom weights.

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | System uptime, database status, active video source, and config |
| `/shelf-status` | `GET` | Real-time zone evaluations, item counts, stock %, and depletion predictions |
| `/live-frame` | `GET` | Single JPEG frame snapshot from active video feed |
| `/live-stream` | `GET` | Continuous multipart/x-mixed-replace MJPEG feed for HTML `<img>` tags |
| `/alerts` | `GET` | List alerts (supports `?unacknowledged=true` and `?limit=50`) |
| `/alerts/<id>/ack` | `POST` | Acknowledge a specific alert by ID |
| `/zones` | `GET` | Retrieve all configured shelf zones |
| `/zones` | `POST` | Create a new shelf zone definition |
| `/zones/<id>` | `PUT` | Update zone name, class, capacity, thresholds, or coordinates |
| `/zones/<id>` | `DELETE` | Delete a shelf zone |
| `/source` | `GET` | Retrieve active video source configuration and health metrics |
| `/source` | `POST` | Dynamically switch video source (`webcam`, `video`, `stream`) |
| `/upload-video` | `POST` | Upload MP4/AVI/MOV file to trigger asynchronous background analysis |
| `/job-status/<id>` | `GET` | Check processing status (`queued`, `processing`, `done`, `failed`) and progress % |
| `/job-result/<id>` | `GET` | Retrieve analyzed sample count, anomaly timeline events, and output video URL |
| `/outputs/<file>` | `GET` | Download/stream browser-playable H.264 annotated video |
| `/history` | `GET` | Query historical time series points for Recharts (`?zone=&hours=`) |
| `/metrics` | `GET` | Average inference latency, FPS, uptime, alert counts, and processed frames |

---

## 🧪 Automated Testing

Run the complete 26-test unit and regression test suite:
```powershell
& "d:\project\venv\Scripts\python.exe" -m pytest -v "backend/tests"
```

Run the live end-to-end integration test (requires backend running):
```powershell
& "d:\project\venv\Scripts\python.exe" "backend/tests/test_e2e_live.py"
```

---

## 📁 Repository Structure

```
smart-shelf-monitor/
├── backend/
│   ├── app.py                  # Flask REST API and streaming routes
│   ├── config.py               # Environment configuration loader
│   ├── db.py                   # MongoDB driver with in-memory JSON fallback
│   ├── sources.py              # Pluggable video sources (webcam, file, MJPEG stream)
│   ├── pipeline.py             # Live background thread (detect -> zones -> alerts)
│   ├── video_jobs.py           # Video upload processor & FFmpeg H.264 transcoder
│   ├── inference/
│   │   ├── detect.py           # YOLOv8 inference wrapper with normalized coordinates
│   │   ├── stock.py            # Zone occupancy, stock % and misplaced item logic
│   │   └── predict.py          # Linear regression depletion & shortage forecasting
│   ├── models/                 # Model weights (yolov8n.pt, best.pt)
│   ├── sample_data/            # Synthetic retail shelf demo video
│   ├── uploads/                # User uploaded video files
│   ├── outputs/                # Annotated output videos
│   ├── tests/                  # Pytest unit & live integration test suites
│   ├── requirements.txt
│   └── .env.example
├── dashboard/                  # React.js (Vite) Frontend Application
│   ├── src/
│   │   ├── components/         # Sidebar, BottomNav, Header
│   │   ├── pages/              # LiveDashboard, AlertsView, Analytics, VideoUpload, Zones
│   │   ├── services/           # Axios API client with dynamic host detection
│   │   ├── App.jsx             # Main routing and toast notifications
│   │   └── index.css           # Glassmorphic responsive design system
│   ├── public/                 # PWA manifest.json and sw.js
│   └── vite.config.js          # Host 0.0.0.0 network configuration
├── dataset/
│   ├── dataset.yaml            # YOLOv8 class definitions
│   └── LABELING_GUIDE.md       # Roboflow / LabelImg annotation instructions
├── scripts/
│   ├── run_all.bat             # Starts backend + frontend concurrently
│   ├── run_backend.bat         # Starts Flask API server
│   ├── run_frontend.bat        # Starts Vite dev server with --host
│   └── setup.bat               # Installs all Python and Node dependencies
├── train.py                    # Transfer learning helper for custom YOLO training
├── PROGRESS.md                 # Live project status and resume instructions
├── AGENT_RULES.md              # Session continuity guidelines
└── README.md
```

---

## 📜 License
Free and open-source for educational and academic use.
