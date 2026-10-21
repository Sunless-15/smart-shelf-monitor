/*
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
    Serial.printf("IP Address: http://%s
", WiFi.localIP().toString().c_str());
    Serial.printf("Snapshot URL: http://%s/capture
", WiFi.localIP().toString().c_str());
    Serial.printf("Status URL:   http://%s/status
", WiFi.localIP().toString().c_str());
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
    Serial.printf("esp_camera_init failed with error code: 0x%x
", err);
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
  String header = "HTTP/1.1 200 OK\r\n";
  header += "Content-Type: image/jpeg\r\n";
  header += "Content-Length: " + String(fb->len) + "\r\n";
  header += "Access-Control-Allow-Origin: *\r\n";
  header += "Connection: close\r\n\r\n";
  client.print(header);
  client.write(fb->buf, fb->len);

  esp_camera_fb_return(fb);
}

void handleStatus() {
  String json = "{";
  json += "\"status\":\"online\",";
  json += "\"uptime_seconds\":" + String(millis() / 1000) + ",";
  json += "\"wifi_rssi_dbm\":" + String(WiFi.RSSI()) + ",";
  json += "\"free_heap_bytes\":" + String(ESP.getFreeHeap()) + ",";
  json += "\"ip_address\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"mac_address\":\"" + WiFi.macAddress() + "\"";
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
      Serial.printf("\n[WIFI] Reconnected! IP: %s\n", WiFi.localIP().toString().c_str());
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
    Serial.printf("[PUSH ERROR] Server responded with code %d\n", httpCode);
  }

  http.end();
  esp_camera_fb_return(fb);
}
