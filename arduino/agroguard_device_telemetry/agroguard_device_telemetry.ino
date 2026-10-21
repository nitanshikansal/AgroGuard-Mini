/*
==============================================================================
AgroGuard - TASK 4C: Arduino UNO R4 WiFi Live Telemetry + Device Auth
==============================================================================
Microcontroller: Arduino UNO R4 WiFi
Target Backend: FastAPI Server
Authentication: Dedicated Device API Key
==============================================================================
*/

#include <WiFiS3.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DFRobot_DHT11.h>
#include "arduino_secrets.h"

// -------------------- SERVER CONFIG --------------------
#define SERVER_HOST "SERVER_HOST"  // Replace with your FastAPI server hostname or IP
#define SERVER_PORT 5000

// Keep this equal to the registered device API key.
// If your project uses a different key, replace this value locally.
#define DEVICE_API_KEY "DEVICE_API_KEY"
#define DEVICE_ID "DEVICE_ID"

// -------------------- PIN DEFINITIONS --------------------
#define DHT11_PIN        2
#define NEXT_BUTTON_PIN  3
#define PREV_BUTTON_PIN  4

#define SOIL_PIN         A0
#define RAIN_PIN         A1
#define WATER_PIN        A2

#define LED_GREEN_PIN    8
#define LED_YELLOW_PIN   9
#define LED_RED_PIN      10

#define SCREEN_WIDTH     128
#define SCREEN_HEIGHT    64
#define OLED_RESET       -1
#define SCREEN_ADDRESS   0x3C

// -------------------- CALIBRATION --------------------
const int SOIL_DRY    = 1018;
const int SOIL_WET    = 166;

const int RAIN_DRY    = 1017;
const int RAIN_WET    = 320;

const int WATER_EMPTY = 0;
const int WATER_FULL  = 750;

// -------------------- CROPS --------------------
const char* CROPS[] = {"WHEAT", "RICE", "SUGARCANE", "POTATO"};
const int NUM_CROPS = 4;
int currentCropIndex = 0;

// -------------------- TIMING --------------------
const unsigned long TELEMETRY_INTERVAL_MS = 7000;
const unsigned long DISPLAY_INTERVAL_MS   = 1000;
const unsigned long SENSOR_INTERVAL_MS    = 1500;
const unsigned long HTTP_TIMEOUT_MS       = 3000;

// -------------------- HARDWARE --------------------
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DFRobot_DHT11 DHT;
WiFiClient client;

// -------------------- SENSOR STATE --------------------
int rawSoil = 0;
int soilPercent = 0;
int rawRain = 0;
int rainPercent = 0;
bool isRaining = false;
int rawWater = 0;
int waterPercent = 0;
int temperature = 25;
int humidity = 60;

// -------------------- BACKEND DECISION STATE --------------------
int lastAfhiScore = -1;
String lastStatus = "INIT";
String lastIrrigation = "";

// -------------------- TIMERS --------------------
unsigned long lastTelemetryTime = 0;
unsigned long lastDisplayTime = 0;
unsigned long lastSensorTime = 0;

// -------------------- BUTTON STATE --------------------
int lastNextBtnState = HIGH;
int lastPrevBtnState = HIGH;
unsigned long lastDebounceTime = 0;

// -------------------- FUNCTION PROTOTYPES --------------------
void connectToWiFi();
void readSensors();
void handleButtons();
void updateOLED();
void setStatusLeds(int green, int yellow, int red);
void sendTelemetryToFastAPI();

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);

  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_YELLOW_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);

  setStatusLeds(LOW, HIGH, LOW);

  pinMode(NEXT_BUTTON_PIN, INPUT_PULLUP);
  pinMode(PREV_BUTTON_PIN, INPUT_PULLUP);

  delay(1000);

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F("  AGROGUARD: ARDUINO UNO R4 WIFI TELEMETRY CONTROLLER"));
  Serial.println(F("======================================================"));

  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("[ERROR] SSD1306 OLED allocation failed. Check I2C wiring (0x3C)."));
    setStatusLeds(LOW, LOW, HIGH);
  } else {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(18, 10);
    display.println(F("AgroGuard Node"));
    display.setCursor(10, 26);
    display.println(F("UNO R4 WiFi Online"));
    display.setCursor(10, 44);
    display.println(F("Connecting Wi-Fi..."));
    display.display();
  }

  connectToWiFi();

  readSensors();
  updateOLED();
}

// ============================================================================
// MAIN LOOP
// ============================================================================
void loop() {
  unsigned long now = millis();

  handleButtons();

  if (now - lastSensorTime >= SENSOR_INTERVAL_MS) {
    lastSensorTime = now;
    readSensors();
  }

  if (now - lastDisplayTime >= DISPLAY_INTERVAL_MS) {
    lastDisplayTime = now;
    updateOLED();
  }

  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = now;

    // Do not attempt HTTP when there is no usable IP.
    if (WiFi.status() == WL_CONNECTED &&
        WiFi.localIP() != IPAddress(0, 0, 0, 0)) {
      sendTelemetryToFastAPI();
    } else {
      Serial.println(F("[WARN] Wi-Fi/IP unavailable. Reconnecting..."));
      setStatusLeds(LOW, LOW, HIGH);
      connectToWiFi();
    }
  }
}

// ============================================================================
// SENSOR FUNCTIONS
// ============================================================================
void readSensors() {
  DHT.read(DHT11_PIN);

  if (DHT.temperature >= 0 && DHT.temperature <= 60) {
    temperature = DHT.temperature;
  }

  if (DHT.humidity >= 5 && DHT.humidity <= 99) {
    humidity = DHT.humidity;
  }

  rawSoil = analogRead(SOIL_PIN);
  soilPercent = map(rawSoil, SOIL_DRY, SOIL_WET, 0, 100);
  soilPercent = constrain(soilPercent, 0, 100);

  rawRain = analogRead(RAIN_PIN);
  rainPercent = map(rawRain, RAIN_DRY, RAIN_WET, 0, 100);
  rainPercent = constrain(rainPercent, 0, 100);
  isRaining = (rawRain < 950);

  rawWater = analogRead(WATER_PIN);
  waterPercent = map(rawWater, WATER_EMPTY, WATER_FULL, 0, 100);
  waterPercent = constrain(waterPercent, 0, 100);
}

// ============================================================================
// BUTTONS
// ============================================================================
void handleButtons() {
  int nextBtn = digitalRead(NEXT_BUTTON_PIN);
  int prevBtn = digitalRead(PREV_BUTTON_PIN);

  if (nextBtn == LOW &&
      lastNextBtnState == HIGH &&
      (millis() - lastDebounceTime > 200)) {

    lastDebounceTime = millis();
    currentCropIndex = (currentCropIndex + 1) % NUM_CROPS;

    Serial.print(F("[USER] Crop Selected (NEXT): "));
    Serial.println(CROPS[currentCropIndex]);

    updateOLED();
  }

  if (prevBtn == LOW &&
      lastPrevBtnState == HIGH &&
      (millis() - lastDebounceTime > 200)) {

    lastDebounceTime = millis();
    currentCropIndex = (currentCropIndex - 1 + NUM_CROPS) % NUM_CROPS;

    Serial.print(F("[USER] Crop Selected (PREV): "));
    Serial.println(CROPS[currentCropIndex]);

    updateOLED();
  }

  lastNextBtnState = nextBtn;
  lastPrevBtnState = prevBtn;
}

// ============================================================================
// OLED
// ============================================================================
void updateOLED() {
  display.clearDisplay();
  display.setTextSize(1);

  display.setCursor(0, 0);
  display.print(F("CROP: "));
  display.print(CROPS[currentCropIndex]);

  display.setCursor(96, 0);
  display.print(WiFi.status() == WL_CONNECTED ? F("[WIFI]") : F("[OFF]"));

  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  display.setCursor(0, 14);
  display.print(F("Soil: "));
  display.print(soilPercent);
  display.print(F("% ("));
  display.print(rawSoil);
  display.print(F(")"));

  display.setCursor(0, 25);
  display.print(F("Tank: "));
  display.print(waterPercent);
  display.print(F("% ("));
  display.print(rawWater);
  display.print(F(")"));

  display.setCursor(0, 36);
  display.print(F("T: "));
  display.print(temperature);
  display.print(F("C H: "));
  display.print(humidity);
  display.print(F("%"));

  display.setCursor(80, 36);
  display.print(isRaining ? F("RAIN:YES") : F("RAIN:NO"));

  display.drawLine(0, 47, 127, 47, SSD1306_WHITE);

  display.setCursor(0, 52);
  if (lastAfhiScore >= 0) {
    display.print(F("AFHI: "));
    display.print(lastAfhiScore);
    display.print(F(" ["));
    display.print(lastStatus.substring(0, 5));
    display.print(F("]"));
  } else {
    display.print(F("FastAPI Telemetry Node"));
  }

  display.display();
}

// ============================================================================
// LED STATUS
// ============================================================================
void setStatusLeds(int green, int yellow, int red) {
  digitalWrite(LED_GREEN_PIN, green);
  digitalWrite(LED_YELLOW_PIN, yellow);
  digitalWrite(LED_RED_PIN, red);
}

// ============================================================================
// WI-FI CONNECTION
// ============================================================================
void connectToWiFi() {
  Serial.print(F("[INFO] Connecting to Wi-Fi SSID: "));
  Serial.println(SECRET_SSID);

  WiFi.disconnect();
  delay(500);

  if (strlen(SECRET_PASS) > 0) {
    WiFi.begin(SECRET_SSID, SECRET_PASS);
  } else {
    WiFi.begin(SECRET_SSID);
  }

  unsigned long startAttempt = millis();

  while (millis() - startAttempt < 30000) {
    if (WiFi.status() == WL_CONNECTED) {
      IPAddress ip = WiFi.localIP();

      if (ip != IPAddress(0, 0, 0, 0)) {
        Serial.println(F("[SUCCESS] Connected to Wi-Fi!"));

        Serial.print(F("[INFO] Arduino IP: "));
        Serial.println(ip);

        Serial.print(F("[INFO] Gateway: "));
        Serial.println(WiFi.gatewayIP());

        Serial.print(F("[INFO] Subnet: "));
        Serial.println(WiFi.subnetMask());

        Serial.print(F("[INFO] RSSI: "));
        Serial.print(WiFi.RSSI());
        Serial.println(F(" dBm"));

        setStatusLeds(HIGH, LOW, LOW);
        return;
      }

      Serial.println(F("[INFO] Wi-Fi connected, waiting for DHCP IP..."));
    } else {
      Serial.print(F("."));
    }

    delay(1000);
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }

  Serial.println();
  Serial.println(F("[WARN] Wi-Fi connected but no valid IP was assigned."));
  Serial.println(F("[WARN] Arduino will retry Wi-Fi connection."));
  setStatusLeds(LOW, LOW, HIGH);
}

// ============================================================================
// FASTAPI HTTP TELEMETRY
// ============================================================================
void sendTelemetryToFastAPI() {
  setStatusLeds(LOW, HIGH, LOW);

  Serial.println(F("\n--- Transmitting Telemetry to FastAPI ---"));

  String jsonPayload = "{";
  jsonPayload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  jsonPayload += "\"soil_moisture\":" + String(soilPercent) + ",";
  jsonPayload += "\"temperature\":" + String(temperature) + ",";
  jsonPayload += "\"humidity\":" + String(humidity) + ",";
  jsonPayload += "\"rain_status\":" + String(isRaining ? "true" : "false") + ",";
  jsonPayload += "\"water_level\":" + String(waterPercent) + ",";
  jsonPayload += "\"crop_type\":\"" + String(CROPS[currentCropIndex]) + "\"";
  jsonPayload += "}";

  Serial.print(F("[HTTP POST] Payload: "));
  Serial.println(jsonPayload);

  client.setTimeout(HTTP_TIMEOUT_MS);

  if (!client.connect(SERVER_HOST, SERVER_PORT)) {
    Serial.print(F("[ERROR] Failed to connect to backend server at "));
    Serial.print(SERVER_HOST);
    Serial.print(F(":"));
    Serial.println(SERVER_PORT);
    setStatusLeds(LOW, LOW, HIGH);
    return;
  }

  client.println(F("POST /sensor/readings HTTP/1.1"));

  client.print(F("Host: "));
  client.print(SERVER_HOST);
  client.print(F(":"));
  client.println(SERVER_PORT);

  client.println(F("User-Agent: AgroGuard-UNO-R4-WiFi/1.0"));
  client.println(F("Content-Type: application/json"));

  client.print(F("X-Device-API-Key: "));
  client.println(DEVICE_API_KEY);

  client.print(F("Content-Length: "));
  client.println(jsonPayload.length());

  client.println(F("Connection: close"));
  client.println();

  client.print(jsonPayload);

  unsigned long timeoutStart = millis();
  int httpCode = -1;
  String responseBody = "";

  while (client.connected() && millis() - timeoutStart < 5000) {
    if (client.available()) {
      String line = client.readStringUntil('\n');

      if (line.startsWith("HTTP/1.1 ") ||
          line.startsWith("HTTP/1.0 ")) {
        httpCode = line.substring(9, 12).toInt();
      }

      if (line == "\r" || line.length() == 0) {
        while (client.available()) {
          responseBody += (char)client.read();
        }
        break;
      }
    }
  }

  client.stop();

  Serial.print(F("[HTTP RESPONSE] Status Code: "));
  Serial.println(httpCode);

  if (responseBody.length() > 0) {
    Serial.print(F("[HTTP RESPONSE] Body: "));
    Serial.println(responseBody);
  }

  if (httpCode == 200 || httpCode == 201) {
    Serial.println(F("[SUCCESS] Telemetry accepted by FastAPI decision engine!"));
    setStatusLeds(HIGH, LOW, LOW);

    int afhiIdx = responseBody.indexOf("\"AFHI\":");

    if (afhiIdx >= 0) {
      int endIdx = responseBody.indexOf(",", afhiIdx);

      if (endIdx > afhiIdx) {
        String scoreStr =
          responseBody.substring(afhiIdx + 7, endIdx);

        scoreStr.trim();
        lastAfhiScore = scoreStr.toInt();
      }
    }

    int statusIdx =
      responseBody.indexOf("\"health_status\":\"");

    if (statusIdx >= 0) {
      int valueStart = statusIdx + 17;
      int endIdx = responseBody.indexOf("\"", valueStart);

      if (endIdx > valueStart) {
        lastStatus =
          responseBody.substring(valueStart, endIdx);
      }
    }

  } else {
    Serial.print(F("[ERROR] Backend rejected telemetry. Code: "));
    Serial.println(httpCode);
    setStatusLeds(LOW, LOW, HIGH);
  }
}
