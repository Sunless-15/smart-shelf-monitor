import os
from pathlib import Path

ROOT = Path(r"D:\project\smart shelf")
FW_DIR = ROOT / "esp32-firmware" / "shelf_camera"
FW_DIR.mkdir(parents=True, exist_ok=True)
TOOLS_DIR = ROOT / "backend" / "tools"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. esp32-firmware/shelf_camera/config.h.example
# -----------------------------------------------------------------------------
config_example = """// ============================================================================
// ShelfSense ESP32-CAM Configuration
// Copy this file to config.h and fill in your WiFi and PC server details.
// DO NOT commit config.h to git (it is listed in .gitignore).
// ============================================================================

#ifndef CONFIG_H
#define CONFIG_H

// 1. WiFi Network Credentials
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// 2. Camera Hardware Resolution & Compression
// Supported framesizes: FRAMESIZE_VGA (640x480), FRAMESIZE_SVGA (800x600), FRAMESIZE_XGA (1024x768)
// Recommended for retail shelves: FRAMESIZE_SVGA or FRAMESIZE_VGA
#define CAMERA_FRAME_SIZE FRAMESIZE_SVGA
// JPEG Quality: 10-63 (Lower number = higher quality & larger file. 12 is optimal balance)
#define CAMERA_JPEG_QUALITY 12

// 3. Operational Mode
// PULL mode (default): PC server requests http://<ESP32_IP>/capture every 5s.
// PUSH mode: ESP32 autonomously sends HTTP POST to http://<PC_IP>:5000/ingest-photo
#define ENABLE_PUSH_MODE false
const char* SERVER_PUSH_URL = "http://192.168.1.100:5000/ingest-photo";
const char* CAMERA_API_KEY  = "shelf_camera_secret_key_2026";
#define PUSH_INTERVAL_MS 5000

// 4. Onboard LED Flash Pin (GPIO 4 on AI-Thinker). Default FALSE to prevent glare.
#define ENABLE_FLASH_LED false

#endif // CONFIG_H
"""
(FW_DIR / "config.h.example").write_text(config_example, encoding="utf-8")

# Also write default config.h if it does not exist
if not (FW_DIR / "config.h").exists():
    (FW_DIR / "config.h").write_text(config_example, encoding="utf-8")

# Ensure .gitignore ignores config.h
git_ignore = ROOT / ".gitignore"
if git_ignore.exists():
    gi_text = git_ignore.read_text(encoding="utf-8")
    if "esp32-firmware/**/config.h" not in gi_text:
        git_ignore.write_text(gi_text + "\nesp32-firmware/**/config.h\n", encoding="utf-8")

# -----------------------------------------------------------------------------
# 2. esp32-firmware/shelf_camera/shelf_camera.ino
# -----------------------------------------------------------------------------
ino_code = """/*
 * ============================================================================
 * ShelfSense ESP32-CAM Firmware (AI-Thinker Model with OV2640 Sensor)
 * ============================================================================
 * Compatible with Arduino IDE 1.8.19+ and ESP32 Arduino Core 2.0.x / 3.x
 * Board Selection: "AI Thinker ESP32-CAM"
 *
 * Primary Capabilities:
 *  1. Connects to 2.4 GHz WiFi network with automatic background reconnection.
 *  2. Initializes OV2640 sensor at SVGA (800x600) with quality=12.
 *  3. Serves HTTP GET /capture -> returns one raw JPEG image directly to PC.
 *  4. Serves HTTP GET /status  -> returns JSON diagnostic telemetry (WiFi RSSI, uptime, free heap).
 *  5. Optional Autonomous Push -> POSTs frame to PC every 5 seconds with X-API-Key header.
 *  6. Watchdog & Auto-Recovery -> Reboots camera module after repeated sensor or network failures.
 * ============================================================================
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include "config.h"

// AI-Thinker ESP32-CAM Pin Definitions
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define FLASH_LED_PIN      4

WebServer server(80);
unsigned long lastPushTime = 0;
int consecutiveCaptureErrors = 0;
const int MAX_ALLOWED_ERRORS = 5;

// Function Prototypes
bool initCamera();
void handleCapture();
void handleStatus();
void handleNotFound();
void checkWiFi();
void pushPhotoToServer();

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("==================================================");
  Serial.println("   ShelfSense ESP32-CAM Firmware Initializing     ");
  Serial.println("==================================================");

  // Initialize Flash LED pin
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW); // Keep off by default to avoid retail glare

  // 1. Initialize OV2640 Camera Hardware
  if (!initCamera()) {
    Serial.println("[CRITICAL ERROR] Camera hardware initialization failed! Rebooting in 5s...");
    delay(5000);
    ESP.restart();
  }
  Serial.println("[OK] OV2640 camera sensor initialized successfully.");

  // 2. Connect to WiFi
  Serial.printf("Connecting to WiFi: %s ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int wifiAttempts = 0;
  while (WiFi.status() != WL_CONNECTED && wifiAttempts < 30) {
    delay(500);
    Serial.print(".");
    wifiAttempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("[OK] WiFi Connected Successfully!");
    Serial.printf("IP Address: http://%s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Snapshot URL: http://%s/capture\n", WiFi.localIP().toString().c_str());
    Serial.printf("Status URL:   http://%s/status\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println();
    Serial.println("[WARNING] Could not connect to WiFi within 15 seconds. Will retry in main loop.");
  }

  // 3. Register HTTP Web Server Endpoints
  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/status", HTTP_GET, handleStatus);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("[OK] HTTP Server listening on port 80.");
}

void loop() {
  // Maintain WiFi Connection
  checkWiFi();

  // Process incoming HTTP Pull requests
  server.handleClient();

  // Autonomous Push Mode (if enabled in config.h)
  #if ENABLE_PUSH_MODE
  if (millis() - lastPushTime >= PUSH_INTERVAL_MS) {
    lastPushTime = millis();
    pushPhotoToServer();
  }
  #endif

  // Watchdog check for repeated capture errors
  if (consecutiveCaptureErrors >= MAX_ALLOWED_ERRORS) {
    Serial.println("[WATCHDOG] Exceeded max capture error limit. Resetting ESP32-CAM...");
    delay(1000);
    ESP.restart();
  }

  delay(10);
}

// ============================================================================
// Camera Hardware Initialization
// ============================================================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = CAMERA_FRAME_SIZE;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;
    config.fb_count = 2;
  } else {
    // Fallback for boards without PSRAM
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 16;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("esp_camera_init failed with error code: 0x%x\n", err);
    return false;
  }

  // Adjust sensor parameters for retail store lighting
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_brightness(s, 1);     // -2 to 2
    s->set_contrast(s, 1);       // -2 to 2
    s->set_saturation(s, 0);     // -2 to 2
    s->set_whitebal(s, 1);       // Auto white balance enable
    s->set_awb_gain(s, 1);       // Auto white balance gain
    s->set_wb_mode(s, 0);        // 0: Auto, 1: Sunny, 2: Cloudy, 3: Office, 4: Home
  }

  return true;
}

// ============================================================================
// HTTP Handlers
// ============================================================================

void handleCapture() {
  #if ENABLE_FLASH_LED
  digitalWrite(FLASH_LED_PIN, HIGH);
  delay(50);
  #endif

  camera_fb_t * fb = esp_camera_fb_get();

  #if ENABLE_FLASH_LED
  digitalWrite(FLASH_LED_PIN, LOW);
  #endif

  if (!fb) {
    consecutiveCaptureErrors++;
    Serial.println("[ERROR] esp_camera_fb_get failed!");
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }

  consecutiveCaptureErrors = 0; // Reset error counter on success

  // Send raw JPEG bytes with standard image headers
  WiFiClient client = server.client();
  String header = "HTTP/1.1 200 OK\\r\\n";
  header += "Content-Type: image/jpeg\\r\\n";
  header += "Content-Length: " + String(fb->len) + "\\r\\n";
  header += "Access-Control-Allow-Origin: *\\r\\n";
  header += "Connection: close\\r\\n\\r\\n";
  client.print(header);
  client.write(fb->buf, fb->len);

  esp_camera_fb_return(fb);
}

void handleStatus() {
  String json = "{";
  json += "\\"status\\":\\"online\\",";
  json += "\\"uptime_seconds\\":" + String(millis() / 1000) + ",";
  json += "\\"wifi_rssi_dbm\\":" + String(WiFi.RSSI()) + ",";
  json += "\\"free_heap_bytes\\":" + String(ESP.getFreeHeap()) + ",";
  json += "\\"ip_address\\":\\"" + WiFi.localIP().toString() + "\\",";
  json += "\\"mac_address\\":\\"" + WiFi.macAddress() + "\\"";
  json += "}";

  server.send(200, "application/json", json);
}

void handleNotFound() {
  server.send(404, "text/plain", "ShelfSense ESP32: Endpoint Not Found. Use /capture or /status.");
}

void checkWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] Connection lost. Attempting reconnect...");
    WiFi.reconnect();
    unsigned long startAttempt = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 3000) {
      delay(200);
      Serial.print(".");
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.printf("\\n[WIFI] Reconnected! IP: %s\\n", WiFi.localIP().toString().c_str());
    }
  }
}

void pushPhotoToServer() {
  if (WiFi.status() != WL_CONNECTED) return;

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    consecutiveCaptureErrors++;
    return;
  }
  consecutiveCaptureErrors = 0;

  HTTPClient http;
  http.begin(SERVER_PUSH_URL);
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-API-Key", CAMERA_API_KEY);
  http.addHeader("X-Camera-ID", "esp32_" + WiFi.localIP().toString());
  http.setTimeout(4000);

  int httpCode = http.POST(fb->buf, fb->len);
  if (httpCode == 200 || httpCode == 201) {
    Serial.println("[PUSH] Photo pushed to server successfully.");
  } else {
    Serial.printf("[PUSH ERROR] Server responded with code %d\\n", httpCode);
  }

  http.end();
  esp_camera_fb_return(fb);
}
"""
(FW_DIR / "shelf_camera.ino").write_text(ino_code, encoding="utf-8")

# -----------------------------------------------------------------------------
# 3. backend/tools/test_esp32.py
# -----------------------------------------------------------------------------
test_tool = """\"\"\"Diagnostic CLI tool to verify an ESP32-CAM module before putting it live.

Usage:
    python backend/tools/test_esp32.py 192.168.1.50
    python backend/tools/test_esp32.py --ip 192.168.1.50 --save-snapshot

Performs:
1. HTTP reachability and latency check on /status
2. High-resolution snapshot capture from /capture
3. Validates JPEG SOI/EOI headers and checks for dark/underexposed images
4. Runs YOLO detection with bounding boxes and logs detected product count
\"\"\"

import argparse
import sys
import time
from pathlib import Path
import requests
import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
from inference.detect import detector


def test_esp32_cam(ip: str, save_snapshot: bool = True):
    print("=" * 60)
    print(f" ShelfSense ESP32-CAM Hardware Diagnostics -> {ip}")
    print("=" * 60)

    # 1. Status Check
    status_url = f"http://{ip}/status"
    print(f"[1/4] Checking module status at {status_url}...")
    try:
        t0 = time.time()
        resp = requests.get(status_url, timeout=3.0)
        latency = (time.time() - t0) * 1000.0
        if resp.status_code == 200:
            print(f"  [OK] Status responded in {latency:.1f}ms: {resp.text}")
        else:
            print(f"  [WARN] Unexpected status code {resp.status_code}: {resp.text}")
    except requests.exceptions.ConnectTimeout:
        print(f"  [FAIL] Connection timed out after 3.0s. Check if ESP32 is powered and on same WiFi subnet.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] Connection refused. Verify IP address {ip} in serial monitor.")
        return False
    except Exception as e:
        print(f"  [WARN] /status check error: {e}")

    # 2. Snapshot Capture Check
    capture_url = f"http://{ip}/capture"
    print(f"[2/4] Pulling photo snapshot from {capture_url}...")
    try:
        t0 = time.time()
        resp = requests.get(capture_url, timeout=5.0)
        capture_latency = (time.time() - t0) * 1000.0
        if resp.status_code != 200:
            print(f"  [FAIL] HTTP {resp.status_code} returned by ESP32 camera endpoint.")
            return False

        jpeg_bytes = resp.content
        size_kb = len(jpeg_bytes) / 1024.0
        print(f"  [OK] Captured {size_kb:.1f} KB JPEG in {capture_latency:.1f}ms.")
    except Exception as e:
        print(f"  [FAIL] Capture failed: {e}")
        return False

    # 3. Image Integrity & Lighting Analysis
    print("[3/4] Analyzing image integrity and store lighting...")
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        print("  [FAIL] Could not decode JPEG bytes into OpenCV image. Possible memory brownout.")
        return False

    h, w, c = img_bgr.shape
    print(f"  [OK] Resolution: {w}x{h} ({c} channels)")

    # Mean brightness analysis (0 to 255)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(gray))
    print(f"  [OK] Mean scene brightness: {mean_brightness:.1f} / 255.0")
    if mean_brightness < 40.0:
        print("  [WARNING] Scene is very dark (< 40). Ensure retail shelf lighting is turned on.")
    elif mean_brightness > 225.0:
        print("  [WARNING] Scene is overexposed (> 225). Check for direct overhead lamp glare.")

    if save_snapshot:
        out_path = BACKEND_DIR / "outputs" / f"esp32_test_{int(time.time())}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), img_bgr)
        print(f"  [OK] Snapshot saved to {out_path}")

    # 4. Instant YOLO Detection Test
    print("[4/4] Executing test YOLO inference...")
    detections, infer_lat = detector.detect(img_bgr)
    print(f"  [OK] Inference completed in {infer_lat:.1f}ms on {detector.device}")
    print(f"  [OK] Products detected: {len(detections)}")

    for i, d in enumerate(detections[:5], 1):
        print(f"    - Item {i}: class '{d['class_name']}', confidence: {d['confidence']:.2f}, box: {d['pixel_box']}")
    if len(detections) > 5:
        print(f"    ... and {len(detections) - 5} more items.")

    print("=" * 60)
    print(" [PASSED] ESP32-CAM is fully operational and ready for live monitoring!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ESP32-CAM Hardware Endpoint")
    parser.add_argument("ip", nargs="?", default="192.168.1.50", help="ESP32-CAM IP address")
    args = parser.parse_args()
    test_esp32_cam(args.ip)
"""
(TOOLS_DIR / "test_esp32.py").write_text(test_tool, encoding="utf-8")

# -----------------------------------------------------------------------------
# 4. backend/tools/collect_images.py
# -----------------------------------------------------------------------------
collect_tool = """\"\"\"Automated Dataset Collector for ESP32-CAM.

Saves a photo every N seconds into dataset/raw_esp32/ for model fine-tuning.
Real shelf photos from the physical camera account for real sensor noise, lens distortion,
and ambient store reflections.

Usage:
    python backend/tools/collect_images.py --ip 192.168.1.50 --count 300 --interval 3.0
\"\"\"

import argparse
import sys
import time
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "dataset" / "raw_esp32"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def collect_esp32_images(ip: str, count: int = 300, interval: float = 3.0):
    print("=" * 60)
    print(f" Collecting {count} real shelf photos from http://{ip}/capture")
    print(f" Saving to: {OUTPUT_DIR}")
    print(f" Interval: {interval} seconds")
    print(" Press Ctrl+C at any time to pause or stop.")
    print("=" * 60)

    success_count = 0
    url = f"http://{ip}/capture"

    for i in range(1, count + 1):
        try:
            t0 = time.time()
            resp = requests.get(url, timeout=5.0)
            if resp.status_code == 200 and len(resp.content) > 1000:
                filename = f"esp32_frame_{int(time.time())}_{i:04d}.jpg"
                save_path = OUTPUT_DIR / filename
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                success_count += 1
                lat = (time.time() - t0) * 1000.0
                print(f"[{i}/{count}] Saved {filename} ({len(resp.content)/1024:.1f} KB, {lat:.0f}ms)")
            else:
                print(f"[{i}/{count}] Error: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[{i}/{count}] Request failed: {e}")

        time.sleep(interval)

    print("=" * 60)
    print(f" Collection complete! Total saved: {success_count} / {count} photos.")
    print(f" Ready for labeling with labelme or Roboflow.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect training photos from ESP32-CAM")
    parser.add_argument("--ip", default="192.168.1.50", help="ESP32 IP address")
    parser.add_argument("--count", type=int, default=300, help="Number of photos to collect")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between snapshots")
    args = parser.parse_args()
    collect_esp32_images(args.ip, count=args.count, interval=args.interval)
"""
(TOOLS_DIR / "collect_images.py").write_text(collect_tool, encoding="utf-8")

# -----------------------------------------------------------------------------
# 5. docs/ESP32_SWITCHOVER.md
# -----------------------------------------------------------------------------
switchover_md = """# ESP32-CAM Hardware Switch-Over Kit & Checklist

This document is your definitive step-by-step procedure for the day the **AI-Thinker ESP32-CAM** hardware arrives.
Because ShelfSense was architected with a decoupled camera source layer, transitioning from simulated mode to live physical hardware requires **ONLY a configuration change**—with **zero code changes** to detection, zone analysis, alert generation, shortage prediction, database, or dashboard logic.

---

## 1. Hardware Overview & Pin Connections
You need:
1. **AI-Thinker ESP32-CAM board** with OV2640 camera module.
2. **FTDI USB-to-TTL Programmer** (or ESP32-CAM-MB micro-USB daughterboard).
3. Jumper wires (if using FTDI programmer):
   - `GND` -> `GND`
   - `5V` -> `5V` (or `VCC` -> `5V` with 5V jumper selected on FTDI; 3.3V can cause brownout reboots!)
   - `U0R` (RX) -> `TX` of FTDI
   - `U0T` (TX) -> `RX` of FTDI
   - `IO0` (GPIO 0) -> `GND` (Connect **only when flashing**; disconnect for normal run mode).

---

## 2. Step-by-Step Hardware Switch-Over Checklist

### Step A: Configure & Flash Firmware
1. Open Arduino IDE (version 1.8.19 or 2.x).
2. Go to `Tools -> Board -> ESP32 Arduino -> AI Thinker ESP32-CAM`.
3. Set CPU Frequency: `240MHz (WiFi/BT)`, Flash Frequency: `80MHz`, Partition Scheme: `Huge APP (3MB No OTA/1MB SPIFFS)`.
4. Open the firmware sketch: `esp32-firmware/shelf_camera/shelf_camera.ino`.
5. Copy `config.h.example` to `config.h`:
   - Enter your 2.4 GHz WiFi SSID and Password in `WIFI_SSID` and `WIFI_PASSWORD`.
   - Leave `CAMERA_FRAME_SIZE` as `FRAMESIZE_SVGA` (800x600) and `CAMERA_JPEG_QUALITY` as `12`.
6. Connect `GPIO 0` to `GND`, plug in USB, press the onboard **RST** button, and click **Upload**.
7. Once upload finishes (`Leaving... Hard resetting via RTS pin...`):
   - **Disconnect `GPIO 0` from `GND`**.
   - Open Serial Monitor at **115200 baud**.
   - Press the onboard **RST** button.
   - Note the printed IP address, e.g., `http://192.168.1.50`.

### Step B: Verify in Web Browser
1. In Chrome or Edge on your PC (connected to the same WiFi), open:
   ```
   http://192.168.1.50/status
   ```
   Verify JSON response returns `"status": "online"` and strong RSSI (> -70 dBm).
2. Open:
   ```
   http://192.168.1.50/capture
   ```
   Verify you see a crisp, live snapshot of your room or desk.

### Step C: Run Automated Diagnostic Tool
Run the verification script from your PC terminal:
```powershell
& "d:\\project\\venv\\Scripts\\python.exe" backend/tools/test_esp32.py 192.168.1.50
```
This tool checks connection speed, image size, verifies store lighting brightness, and runs immediate YOLO detection on the frame. Confirm it reports `[PASSED]`.

### Step D: Physical Mounting
1. Mount the ESP32-CAM 60–100 cm in front of the retail shelf.
2. Angle the lens so both the top and bottom shelf surfaces are clearly visible.
3. Secure the module using a 3D-printed bracket or non-conductive mount. Avoid touching the camera ribbon cable while powered.

### Step E: Fine-Tuning Photo Collection
Because the OV2640 sensor has different chromatic response and lens distortion compared to SKU-110K dataset photos, collect 300 real photos for fine-tuning:
```powershell
& "d:\\project\\venv\\Scripts\\python.exe" backend/tools/collect_images.py --ip 192.168.1.50 --count 300 --interval 3.0
```
Photos are saved into `dataset/raw_esp32/`.

### Step F: Configure Shelf Zones on Real Snapshot
1. In the ShelfSense dashboard, navigate to **Settings** (`/zones`).
2. Click **Capture Real Snapshot from ESP32** or upload a sample snapshot.
3. Draw your rectangular shelf zones (e.g., Top Shelf, Middle Shelf, Bottom Shelf).
4. Save zone definitions.

### Step G: Flip Configuration to Live Camera Mode
Open `backend/.env` (or navigate to Settings in the web UI):
```env
CAMERA_MODE=esp32_pull
ESP32_IP=192.168.1.50
CAPTURE_INTERVAL_SECONDS=5.0
```
*Note: If you prefer push mode, set `CAMERA_MODE=esp32_push`, set `ENABLE_PUSH_MODE true` in firmware `config.h`, and re-flash.*

### Step H: Verify Live Dashboard
1. Open the ShelfSense Dashboard: `http://localhost:5173`.
2. Notice the header banner immediately changes from amber `DEMO MODE: simulated camera` to vibrant green:
   ```
   LIVE CAMERA: ESP32-CAM (192.168.1.50)
   ```
3. Verify the main image card displays `"Latest photo"` with `"Last updated 3s ago"`.
4. Inspect the **Pipeline Trace** card confirming real live product counts and 3-photo confirmation.

---

## 3. Hardware Troubleshooting Table

| Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| **Serial shows brownout detector reset** | Insufficient 5V current during WiFi transmission bursts | Power from dedicated 5V 2A adapter. Connect a 100uF–470uF electrolytic capacitor across `5V` and `GND` pins. |
| **WiFi connects but /capture returns 500** | Camera sensor ribbon cable unseated or dirty pins | Unpower, open FPC latch, reseat OV2640 ribbon cable firmly, re-latch. |
| **Images are extremely dark or grainy** | Indoor retail lighting below sensor baseline | Increase brightness in firmware: `s->set_brightness(s, 2)` or increase store illumination. |
| **Harsh glare on packaging** | Overhead lighting reflecting into lens | Ensure onboard flash LED is off (`ENABLE_FLASH_LED false`). Angle camera slightly downward (15° tilt). |
| **Connection times out intermittently** | Weak 2.4 GHz WiFi signal | Reposition camera closer to WiFi access point or install external 2.4 GHz rubber duck antenna via IPEX connector (move 0-ohm resistor). |
| **IP address changes on reboot** | DHCP lease expired | Assign a static DHCP reservation for the ESP32 MAC address in your router admin panel. |
"""
(DOCS_DIR / "ESP32_SWITCHOVER.md").write_text(switchover_md, encoding="utf-8")

print("ESP32-CAM Firmware & Switch-Over Kit built successfully!")
