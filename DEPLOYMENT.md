# Public Cloud Deployment Guide

A step-by-step guide to deploying the **Intelligent Empty Shelf and Low Stock Monitoring System** to the public internet using 100% free-tier services.

Once deployed:
- **Frontend Dashboard** is hosted on **Vercel** with a public `https://...vercel.app` URL.
- **Backend API & AI Engine** runs in a Docker container on **Render** (`https://...onrender.com`).
- **Database** is hosted on **MongoDB Atlas** (M0 Free Tier).
- **Camera Feed** is pushed by the lightweight **Camera Agent** from your laptop/PC (or ESP32-CAM) to the cloud backend.
- Anyone can view the dashboard from any phone or PC with no local network restrictions!

---

## 🏛️ Public Cloud Architecture

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

---

## 📋 Prerequisites Checklist
Before starting, create free accounts on:
1. [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. [GitHub](https://github.com/join)
3. [Render](https://render.com/)
4. [Vercel](https://vercel.com/signup)

---

## Step 1: Create a Free MongoDB Atlas Database

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com/).
2. Click **Create** $\rightarrow$ Choose **M0 Free** (Shared) cluster.
3. Select your closest AWS region (e.g. `ap-south-1` Mumbai or `us-east-1` N. Virginia) $\rightarrow$ Click **Create Deployment**.
4. **Create a Database User**:
   - Set **Username**: e.g. `shelf_admin`
   - Set **Password**: Click **Autogenerate Secure Password** or set a strong password (e.g. `ShelfPass2026!`).
   - ⚠️ **Save this password immediately** — you will need it in the connection string.
   - Click **Create Database User**.
5. **Configure Network Access**:
   - Under **Where would you like to connect from?**, select **Allow Access from Anywhere** (`0.0.0.0/0`).
   - Click **Add Entry**.
6. **Get Connection String**:
   - Click **Finish and Close** $\rightarrow$ Click **Go to Overview**.
   - Click **Connect** $\rightarrow$ Select **Drivers** (Python 3.12+).
   - Copy the connection string. It looks like:
     ```
     mongodb+srv://shelf_admin:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
     ```
   - Replace `<password>` with your actual password (and ensure special characters are URL-encoded if needed).
   - Append your database name before the `?`:
     ```
     mongodb+srv://shelf_admin:ShelfPass2026!@cluster0.abcde.mongodb.net/shelf_monitor?retryWrites=true&w=majority
     ```

---

## Step 2: Push Your Project to GitHub

1. Verify that sensitive local files (`.env`, `venv/`, `node_modules/`, `uploads/`, `outputs/`) are excluded by `.gitignore`.
2. Open PowerShell in `d:\project\smart shelf` and verify git status:
   ```powershell
   git status
   ```
3. Create a new repository on [GitHub](https://github.com/new):
   - Repository name: `smart-shelf-monitor`
   - Privacy: **Private** or **Public**
   - Do **NOT** initialize with README, .gitignore, or license (we already have them).
4. Link your local repo and push:
   ```powershell
   git remote add origin https://github.com/<your-username>/smart-shelf-monitor.git
   git branch -M main
   git push -u origin main
   ```

---

## Step 3: Deploy the Backend on Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** $\rightarrow$ Select **Web Service**.
3. Choose **Build and deploy from a Git repository** $\rightarrow$ Connect your GitHub account and select `smart-shelf-monitor`.
4. Configure the Web Service:
   - **Name**: `smart-shelf-backend` (or similar)
   - **Region**: Choose the region closest to your MongoDB Atlas cluster (e.g. Oregon or Singapore).
   - **Branch**: `main` (or `master`)
   - **Root Directory**: `backend`
   - **Runtime**: **Docker**
   - **Instance Type**: **Free** ($0/month, 512 MB RAM, 0.1 CPU)
5. **Add Environment Variables**:
   Click **Advanced** $\rightarrow$ **Add Environment Variable** and enter:

   | Key | Value | Description |
   |---|---|---|
   | `MONGO_URI` | `mongodb+srv://shelf_admin:...@cluster0...` | Your Atlas connection string |
   | `DB_NAME` | `shelf_monitor` | MongoDB database name |
   | `DASHBOARD_PASSWORD` | `admin123` | Password to unlock dashboard |
   | `SECRET_KEY` | `super_secure_random_key_with_at_least_32_characters_2026` | Key to sign JWT tokens |
   | `AGENT_API_KEY` | `shelf_agent_secret_key_2026` | Key used by local camera agent |
   | `CORS_ORIGINS` | `http://localhost:5173` | Temporary value (updated in Step 5 with Vercel URL) |
   | `DEFAULT_SOURCE_TYPE` | `agent` | Server waits for camera agent frames |
   | `DEFAULT_SOURCE_VALUE` | `remote_push` | Source descriptor |
   | `INFERENCE_MAX_WIDTH` | `640` | Resizes frames to fit 512MB RAM |
   | `MAX_UPLOAD_MB` | `50` | Maximum video upload size |
   | `FILE_CLEANUP_HOURS` | `6` | Automatically purges old files |

6. Click **Create Web Service**.
7. Render will build the Docker container (installing FFmpeg, CPU PyTorch, and Gunicorn). This initial build takes ~4-6 minutes.
8. Once deployed, Render will display your public URL:
   ```
   https://smart-shelf-backend.onrender.com
   ```
9. **Verify Health**:
   Open in your browser:
   `https://smart-shelf-backend.onrender.com/health`
   You should see: `{"status": "ok", "service": "smart-shelf-monitor-api", ...}`.

---

## Step 4: Deploy the Frontend on Vercel

1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New...** $\rightarrow$ Select **Project**.
3. Import your GitHub repository `smart-shelf-monitor`.
4. Configure Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** $\rightarrow$ select `dashboard` $\rightarrow$ click **Continue**.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. **Add Environment Variable**:
   Under **Environment Variables**:
   - **Key**: `VITE_API_URL`
   - **Value**: Your Render backend URL from Step 3 (e.g. `https://smart-shelf-backend.onrender.com`)
   - Click **Add**.
6. Click **Deploy**.
7. In ~45 seconds, Vercel will finish building and provide your public URL:
   ```
   https://smart-shelf-monitor.vercel.app
   ```
8. Click the link to open your live web app!
   - You will see the **Dashboard Access** modal.
   - Enter your `DASHBOARD_PASSWORD` (default: `admin123`).
   - The dashboard opens and presents the live vision cards, alerts, analytics, and upload studio!

---

## Step 5: Update CORS on the Backend

Now that you have your live Vercel URL:
1. Go back to your [Render Dashboard](https://dashboard.render.com/) $\rightarrow$ click `smart-shelf-backend`.
2. Click **Environment** on the left menu.
3. Edit `CORS_ORIGINS` to include your Vercel domain:
   ```
   https://smart-shelf-monitor.vercel.app,http://localhost:5173
   ```
4. Click **Save Changes**. Render will automatically redeploy with the updated CORS policy in ~30 seconds.

---

## Step 6: Start the Camera Agent on Your PC

Because cloud servers cannot directly access your local laptop webcam or your home Wi-Fi ESP32-CAM, the **Camera Agent** runs on your PC, grabs video, and pushes frames to your public cloud backend:

1. Open `agent/.env` on your PC:
   ```ini
   BACKEND_URL=https://smart-shelf-backend.onrender.com
   AGENT_API_KEY=shelf_agent_secret_key_2026
   CAMERA_ID=shelf_camera_1
   SOURCE_TYPE=video
   SOURCE_VALUE=../backend/sample_data/sample_shelf.mp4
   INTERVAL_SECONDS=1.5
   ```
2. Double-click or run:
   ```cmd
   scripts\run_agent.bat
   ```
3. You will see:
   ```
   [OK #1] Pushed frame (640x480, 24 KB) -> Detections: 4 | Items: 4
   [OK #2] Pushed frame (640x480, 24 KB) -> Detections: 4 | Items: 4
   ```
4. **Test on Your Phone over Mobile Data**:
   - Turn off Wi-Fi on your phone and enable 4G/5G mobile data.
   - Open `https://smart-shelf-monitor.vercel.app`.
   - Log in with `admin123`.
   - You will see the live shelf video stream, bounding box detections, and live stock percentages updating in real time across the internet!

---

## Step 7: How to Deploy a Custom Trained Model (`best.pt`)

When you train a custom model using `python train.py`:

### Option A: Via MODEL_URL (Recommended — keeps GitHub repo small)
1. Upload your trained `best.pt` file to GitHub Releases, Google Drive (direct link), or Hugging Face.
2. In your Render Dashboard, add an environment variable:
   - `MODEL_URL`: `https://your-host.com/path/to/best.pt`
   - `MODEL_PATH`: `models/best.pt`
3. Restart the service. The backend will automatically download your weights on startup!

### Option B: Commit directly to Git
If your `best.pt` is small (< 15 MB):
1. Place it in `backend/models/best.pt`.
2. Update `backend/.env` or Render environment: `MODEL_PATH=models/best.pt`.
3. Commit and push to GitHub. Render will redeploy with the new weights.

---

## Step 8: Switching to ESP32-CAM Later

When your ESP32-CAM hardware arrives and is powered on your local Wi-Fi:
1. Find its IP address from the Arduino Serial Monitor (e.g. `192.168.1.105`).
2. Open `agent/.env` on your PC:
   ```ini
   SOURCE_TYPE=stream
   SOURCE_VALUE=http://192.168.1.105:81/stream
   ```
3. Restart `run_agent.bat`.
   - The agent now pulls frames from the ESP32-CAM and streams them directly into your public cloud dashboard!
   - **Zero code changes or cloud redeployments required.**

---

## ⚡ Alternative: Free Cloudflare Tunnel (Run Backend on PC)

If Render's free CPU inference is too slow (e.g. 500ms latency) and you want your PC's CPU/GPU power while still having a public HTTPS URL:

1. Download `cloudflared` on Windows:
   ```powershell
   winget install --id Cloudflare.cloudflared
   ```
2. Start your local backend (`run_backend.bat` on port 5000).
3. In a separate terminal, expose port 5000:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
4. Cloudflare outputs a free public URL:
   `https://random-words.trycloudflare.com`
5. On Vercel, set `VITE_API_URL` to that Cloudflare URL!
   - **Tradeoff**: Super fast inference using your PC's hardware, but only accessible while your PC is on and running `cloudflared`.

---

## ⚠️ Known Limits of Free Tiers & Workarounds

| Limitation | Impact | Recommended Solution / Workaround |
|---|---|---|
| **Render Cold Sleep** | Free web services spin down after 15 minutes of inactivity. First request takes ~30-50s to wake up. | 1. The dashboard displays a friendly *"Server is waking up..."* banner.<br>2. Set up a free 5-minute pinger on [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com) pointing to `https://...onrender.com/health`.<br>3. Or upgrade Render to Starter ($7) for your demo day. |
| **512 MB RAM Limit** | Running large 4K image models can cause out-of-memory crashes. | The backend automatically uses `INFERENCE_MAX_WIDTH=640` and `yolov8n` (nano) which uses < 250 MB RAM. |
| **Ephemeral Disk** | Uploaded videos in `uploads/` and `outputs/` are erased when Render restarts. | MongoDB Atlas persists all zone definitions, alert history, and time-series metrics permanently. |
| **CPU-Only Inference** | Cloud inference runs at ~2-4 FPS on free CPU. | The camera agent samples every 1.5s, which matches cloud CPU capacity. For 30 FPS demos, use the Cloudflare Tunnel option. |

---

## 🛠️ Troubleshooting

- **CORS Error (`Access-Control-Allow-Origin`) in browser console:**
  Verify that your exact Vercel domain (including `https://`) is added to `CORS_ORIGINS` in your Render Environment settings.
- **502 Bad Gateway / Application Error on Render:**
  Check the **Logs** tab on Render. Ensure `MONGO_URI` is correct and network access in Atlas is set to `0.0.0.0/0`.
- **Camera Agent says `[AUTH ERROR] 401 Unauthorized`:**
  Check that `AGENT_API_KEY` in `agent/.env` matches the `AGENT_API_KEY` configured on Render.
- **Dashboard says "Invalid password":**
  Ensure you are using the password configured in `DASHBOARD_PASSWORD` (default: `admin123`).
- **Video player doesn't play uploaded videos:**
  Render's Dockerfile installs native `ffmpeg` with `libx264` and `+faststart` so all generated MP4 files are natively playable in Safari and Chrome.
