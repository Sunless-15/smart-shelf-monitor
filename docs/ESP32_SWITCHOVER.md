# ESP32-CAM Hardware Switch-Over Kit & Checklist

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
& "d:\project\venv\Scripts\python.exe" backend/tools/test_esp32.py 192.168.1.50
```
This tool checks connection speed, image size, verifies store lighting brightness, and runs immediate YOLO detection on the frame. Confirm it reports `[PASSED]`.

### Step D: Physical Mounting
1. Mount the ESP32-CAM 60–100 cm in front of the retail shelf.
2. Angle the lens so both the top and bottom shelf surfaces are clearly visible.
3. Secure the module using a 3D-printed bracket or non-conductive mount. Avoid touching the camera ribbon cable while powered.

### Step E: Fine-Tuning Photo Collection
Because the OV2640 sensor has different chromatic response and lens distortion compared to SKU-110K dataset photos, collect 300 real photos for fine-tuning:
```powershell
& "d:\project\venv\Scripts\python.exe" backend/tools/collect_images.py --ip 192.168.1.50 --count 300 --interval 3.0
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
