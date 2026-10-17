# Intelligent Empty Shelf and Low Stock Monitoring System

A computer-vision-based system that detects empty shelf spaces, counts stock,
flags misplaced products, and alerts store managers in real time via a web
dashboard. Built for Project Phase I, Department of CSE, St. Thomas College
of Engineering & Technology.

## Team
| Name | Reg No | Role |
|---|---|---|
| Shobin Bobby | STC23CS075 | Team Lead — Architecture, Implementation |
| Sachu Sreejith | STC23CS071 | Camera/Hardware Setup, Model Integration |
| Vrinda T Vinod | STC23CS083 | Dataset Preprocessing, Model Training |
| Aiswarya M S | MZW23CS002 | Dashboard/UI, GitHub, Project Diary |

**Supervisor:** Prof. Teena M Thomas, Assistant Professor, Dept. of CSE

## Architecture
```
ESP32-CAM (image capture + WiFi stream)
        │
        ▼
   PC/Laptop — Flask backend
   ├── YOLO inference (product + empty-slot detection)
   ├── Stock counting & alert logic
   └── MongoDB (stock state, alert history)
        │
        ▼
   React.js Dashboard (live status, alerts, video upload/analysis)
```

All CV processing and inference run on the PC — the ESP32-CAM only
captures and streams frames.

## Project Structure
```
smart-shelf-monitor/
├── backend/
│   ├── app.py              # Flask API entry point
│   ├── inference/          # YOLO detection & stock-counting logic
│   ├── models/              # Trained YOLO weights (.pt)
│   ├── requirements.txt
│   └── .env                 # Local config (Mongo URI, ESP32 IP) — not committed
├── dashboard/                # React (Vite) frontend
├── esp32-firmware/           # Arduino sketch for ESP32-CAM
├── dataset/
│   ├── images/
│   └── labels/               # YOLO-format annotations
└── README.md
```

## Prerequisites
- Python 3.10+
- Node.js LTS + npm
- MongoDB (local service or Atlas cluster)
- Arduino IDE 1.8.19 with ESP32 board package
- ESP32-CAM module + USB-to-serial programmer

## Setup

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file in `backend/`:
```
MONGO_URI=mongodb://localhost:27017/shelf_monitor
ESP32_STREAM_URL=http://<esp32-ip>:81/stream
```
Run the API:
```bash
python app.py
```

### 2. Dashboard
```bash
cd dashboard
npm install
npm run dev
```

### 3. ESP32-CAM Firmware
1. Open `esp32-firmware/CameraWebServer.ino` in Arduino IDE
2. Select **Tools → Board → AI Thinker ESP32-CAM**
3. Select the correct COM port
4. Update WiFi SSID/password in the sketch
5. Flash the board, note the IP printed in Serial Monitor
6. Update `ESP32_STREAM_URL` in `backend/.env` accordingly

## Usage
- **Live monitoring:** dashboard connects to the Flask API, which pulls the
  ESP32-CAM stream and runs continuous YOLO inference.
- **Video upload:** upload a shelf video via the dashboard's "Upload Video"
  tab for offline detection/testing without the live feed.

## Features
- Real-time empty shelf & low-stock detection (YOLO-based)
- Misplaced-product flagging
- Web dashboard with live stock levels and alerts
- Video upload mode for offline analysis/demos
- Historical stock/alert logging via MongoDB

## Dataset
- Custom shelf images captured via ESP32-CAM
- SKU-110K / Grozi-120 benchmark datasets (supplementary)
- Annotated in YOLO format using Roboflow / LabelImg

## Evaluation Metrics
- Detection precision / recall / mAP@50
- Stock-count accuracy vs. manual ground truth
- Alert latency (event → dashboard notification)

## Status
Phase I — Interim Evaluation complete. See `docs/project-diary.pdf` for
weekly progress logs.

## License
Academic project — St. Thomas College of Engineering & Technology.
