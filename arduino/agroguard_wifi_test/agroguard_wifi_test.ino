/*
  ==============================================================================
  AgroGuard — TASK 4A: Arduino UNO R4 WiFi Connectivity Test
  ==============================================================================
  Board: Arduino UNO R4 WiFi (Renesas RA4M1 + ESP32-S3)
  Target Network: Same local Wi-Fi network as the laptop running the backend
  Library: WiFiS3 (Official built-in networking library for UNO R4 WiFi)

  Features:
  - Automatic DHCP IP allocation
  - Non-crashing timeout & graceful reconnect loop
  - Detailed Serial Monitor diagnostics (Local IP, Subnet, Gateway, RSSI, MAC)
  - Activity LED indication
  - Prepared architectural hooks for upcoming sensor & Flask HTTP telemetry tasks

  Serial Monitor Settings:
  - Baud Rate: 115200 baud
  - Line ending: Both NL & CR / Autoscroll
  ==============================================================================
*/

#include <WiFiS3.h>
#include "arduino_secrets.h"

// -----------------------------------------------------------------------------
// 1. NETWORK CONFIGURATION VARIABLES
// -----------------------------------------------------------------------------
// Values are imported from arduino_secrets.h.
// Alternatively, you may replace these placeholders directly.
const char WIFI_SSID[]     = SECRET_SSID;
const char WIFI_PASSWORD[] = SECRET_PASS;

// Connection timing parameters (milliseconds)
const unsigned long CONNECT_TIMEOUT_MS   = 20000; // 20 seconds timeout per attempt
const unsigned long RETRY_DELAY_MS       = 10000; // 10 seconds backoff between retries
const unsigned long HEARTBEAT_INTERVAL_MS = 10000; // 10 seconds between periodic pings

// Internal state
int wifiStatus = WL_IDLE_STATUS;
unsigned long lastHeartbeatTime = 0;
unsigned int connectionAttempts = 0;

// Function Prototypes
bool connectToWiFi();
void printNetworkDetails();
void printWiFiFirmwareVersion();

// -----------------------------------------------------------------------------
// 2. SETUP: HARDWARE INITIALIZATION & FIRST CONNECTION
// -----------------------------------------------------------------------------
void setup() {
  // Initialize on-board LED for visual status feedback
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // Initialize USB CDC Serial communication
  Serial.begin(115200);

  // Allow up to 3 seconds for Serial Monitor to open (does not block if standalone)
  while (!Serial && millis() < 3000) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(50);
    digitalWrite(LED_BUILTIN, LOW);
    delay(50);
  }

  Serial.println();
  Serial.println(F("======================================================"));
  Serial.println(F("  AGROGUARD -- ARDUINO UNO R4 WIFI CONNECTIVITY TEST  "));
  Serial.println(F("======================================================"));

  // Verify that the on-board ESP32-S3 radio module is responding
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println(F("[FATAL] Communication with WiFi module failed!"));
    Serial.println(F("[FATAL] Please check that the board is an Arduino UNO R4 WiFi."));
    while (true) {
      // Fast error blink sequence (200ms cycle)
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
      delay(100);
    }
  }

  // Print module firmware version
  printWiFiFirmwareVersion();

  // Validate placeholder credentials
  if (strcmp(WIFI_SSID, "YOUR_WIFI_SSID") == 0) {
    Serial.println(F("[NOTICE] Configuration needed:"));
    Serial.println(F("         Please open 'arduino_secrets.h' and enter"));
    Serial.println(F("         your Wi-Fi SSID and Password before connecting."));
    Serial.println(F("------------------------------------------------------"));
  }

  // Perform initial Wi-Fi connection attempt
  connectToWiFi();
}

// -----------------------------------------------------------------------------
// 3. MAIN LOOP: CONNECTION MAINTENANCE & HEARTBEAT
// -----------------------------------------------------------------------------
void loop() {
  wifiStatus = WiFi.status();

  // If connection is dropped, attempt graceful reconnect without resetting MCU
  if (wifiStatus != WL_CONNECTED) {
    Serial.println();
    Serial.println(F("[WARN] Wi-Fi connection dropped!"));
    digitalWrite(LED_BUILTIN, LOW);

    // Wait backoff period before attempting reconnect
    delay(RETRY_DELAY_MS);
    connectToWiFi();
  } else {
    // Connection is healthy -- print periodic heartbeat diagnostics
    unsigned long currentMillis = millis();
    if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
      lastHeartbeatTime = currentMillis;

      unsigned long uptimeSec = currentMillis / 1000;
      Serial.print(F("[STATUS] Wi-Fi Active | Arduino IP: "));
      Serial.print(WiFi.localIP());
      Serial.print(F(" | RSSI: "));
      Serial.print(WiFi.RSSI());
      Serial.print(F(" dBm | Uptime: "));
      Serial.print(uptimeSec);
      Serial.println(F("s"));

      // Gentle visual pulse on built-in LED
      digitalWrite(LED_BUILTIN, HIGH);
      delay(80);
      digitalWrite(LED_BUILTIN, LOW);
    }
  }

  // ===========================================================================
  // PLACEHOLDER: SENSOR TELEMETRY ACQUISITION (Reserved for Task 4B)
  // ===========================================================================
  // Future sensors to read periodically:
  // - Soil Moisture (Capacitive/Resistive) on Analog Pin A0
  // - Ambient Temperature & Humidity (DHT11 / DHT22) on Digital Pin D2
  // - Rain Sensor on Analog Pin A1 / Digital D3
  // - Water Tank Storage Level (Ultrasonic / Float) on Analog Pin A2
  //
  // ===========================================================================
  // PLACEHOLDER: FLASK REST API HTTP TELEMETRY POST (Reserved for Task 4C)
  // ===========================================================================
  // Future communication:
  // - Use WiFiClient to send JSON payload:
  //   POST http://<laptop-ip>:5000/sensor
  // - Synchronize actuator state:
  //   GET http://<laptop-ip>:5000/control/pump
  // ===========================================================================
}

// -----------------------------------------------------------------------------
// 4. HELPER FUNCTIONS
// -----------------------------------------------------------------------------

/**
 * Attempts connection to the configured Wi-Fi network.
 * Returns true if connection succeeded, false if timed out.
 */
bool connectToWiFi() {
  connectionAttempts++;

  Serial.println();
  Serial.print(F("[INFO] Starting Wi-Fi connection (Attempt #"));
  Serial.print(connectionAttempts);
  Serial.println(F(")..."));

  Serial.print(F("[INFO] Target Network SSID : "));
  Serial.println(WIFI_SSID);
  Serial.println(F("[INFO] Negotiating IP via DHCP..."));

  // Disconnect any lingering stale sessions
  WiFi.disconnect();
  delay(1000);

  // Begin connection to WPA2/WPA Personal or Open network
  if (strlen(WIFI_PASSWORD) > 0) {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  } else {
    WiFi.begin(WIFI_SSID);
  }

  // Wait for connection up to CONNECT_TIMEOUT_MS with visual progress dots
  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startAttemptTime < CONNECT_TIMEOUT_MS)) {
    delay(500);
    Serial.print(F("."));

    // Rapid toggle of LED while negotiating DHCP
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }
  Serial.println();

  // Evaluate connection status
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("[SUCCESS] Wi-Fi connected!"));
    digitalWrite(LED_BUILTIN, HIGH); // Solid ON when connected

    // Display assigned network parameters
    printNetworkDetails();
    lastHeartbeatTime = millis();
    return true;
  } else {
    Serial.println(F("[ERROR] Wi-Fi connection failed or timed out."));
    Serial.print(F("[INFO] Current status code: "));
    Serial.println(WiFi.status());
    Serial.println(F("[INFO] The microcontroller will retry automatically in 10s."));
    Serial.println(F("[TIP]  Check Wi-Fi SSID, password, and router 2.4 GHz availability."));
    digitalWrite(LED_BUILTIN, LOW);
    return false;
  }
}

/**
 * Prints the network diagnostic details assigned to this Arduino board.
 */
void printNetworkDetails() {
  Serial.println(F("------------------------------------------------------"));
  Serial.println(F("  NETWORK DIAGNOSTIC INFORMATION (DHCP)"));
  Serial.println(F("------------------------------------------------------"));

  // Assigned Local IP Address
  Serial.print(F("  Arduino Local IP   : "));
  Serial.println(WiFi.localIP());

  // Subnet Mask
  Serial.print(F("  Subnet Mask        : "));
  Serial.println(WiFi.subnetMask());

  // Gateway IP Address
  Serial.print(F("  Default Gateway    : "));
  Serial.println(WiFi.gatewayIP());

  // Signal Strength (RSSI)
  Serial.print(F("  Signal Strength    : "));
  Serial.print(WiFi.RSSI());
  Serial.println(F(" dBm"));

  // MAC Address of the UNO R4 WiFi board
  byte mac[6];
  WiFi.macAddress(mac);
  char macBuffer[18];
  snprintf(macBuffer, sizeof(macBuffer), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  Serial.print(F("  MAC Address        : "));
  Serial.println(macBuffer);

  Serial.println(F("------------------------------------------------------"));
  Serial.println(F("[READY] Wi-Fi link active and waiting for sensor tasks."));
  Serial.println(F("======================================================"));
}

/**
 * Checks and prints the WiFi firmware version on the ESP32-S3 module.
 */
void printWiFiFirmwareVersion() {
  String fv = WiFi.firmwareVersion();
  Serial.print(F("[INFO] UNO R4 WiFi Radio Firmware : v"));
  Serial.println(fv);

  // Latest standard is typically 0.4.1 or higher
  if (fv < WIFI_FIRMWARE_LATEST_VERSION) {
    Serial.println(F("[NOTE] A newer Wi-Fi module firmware version is available from Arduino."));
  }
}
