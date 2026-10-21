# AgroGuard — Intelligent IoT Precision Agriculture & Decision Support Platform

AgroGuard is an end-to-end smart agriculture decision support system designed for smallholder and commercial farmers. It couples real-time Arduino UNO R4 WiFi telemetry, dedicated hardware device API key authentication, automated agronomic decision engines (AFHI, CAII, SPAE), cloud database persistence, and farmer-friendly interfaces across 10 Indian regional languages.

---

## Architecture Summary

```
                      +-----------------------------+
                      |   Arduino UNO R4 WiFi Node  |
                      |  (Sensors: Moisture, Temp,  |
                      |   Humidity, Rain, Water)    |
                      +--------------+--------------+
                                     |
                                     | HTTP POST (X-Device-API-Key Header)
                                     v
+-----------------------+   +-----------------------------+   +-------------------------+
|   Farmer Web Client   |   |   FastAPI Backend (5000)    |   |   Supabase PostgreSQL   |
| (Dashboard, Login,    |<->| - Dual Device / JWT Auth    |<->| - 8 Relational Tables   |
|  Alerts, Profile)     |   | - AFHI Health Model         |   | - RLS Ownership         |
| [10 Indian Languages] |   | - CAII Irrigation Intel     |   | - Secure JWT Auth       |
+-----------------------+   | - SPAE Spray Safety         |   +-------------------------+
                            | - Device & Farm Ownership   |
                            +-----------------------------+
```

---

## Directory Structure

```
AgroGuard_MiniProject/
├── frontend/                     # Modern responsive web console
│   ├── index.html                # Hero splash and introduction
│   ├── dashboard.html            # Main farmer telemetry & decision dashboard
│   ├── login.html                # Phone OTP verification portal
│   ├── profile.html              # Farm plot & farmer profile management
│   ├── alerts.html               # Real-time alert notifications console
│   ├── about.html, features.html # Informational portals
│   ├── css/style.css             # Unified AgriTech design system
│   ├── js/                       # Modular services: auth, dashboard, i18n, notifications
│   └── locales/                  # 10 Indian language JSON dictionaries
├── backend/                      # High-performance FastAPI REST API
│   ├── app/
│   │   ├── auth/                 # PyJWT token verification, Device API Key auth, & ownership dependencies
│   │   ├── routes/               # API endpoints (sensor, dashboard, control, database, auth)
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── services/             # AFHI, CAII, SPAE models, sensor simulator, pump service
│   │   │   └── database/         # Supabase PostgreSQL client & in-memory fallback
│   │   ├── config.py             # Settings & CORS configuration
│   │   └── main.py               # Application factory & global handlers
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Environment variables template
│   └── run.py                    # Entry point runner script
├── database/                     # PostgreSQL database foundation
│   ├── supabase_schema.sql       # Full schema DDL (tables, FKs, RLS, indexes)
│   └── README.md                 # Supabase setup instructions
├── arduino/                      # Arduino UNO R4 WiFi firmware
│   ├── agroguard_wifi_test/      # Task 4A connectivity sketch
│   └── agroguard_device_telemetry/ # Task 4C live telemetry & device auth sketch
└── README.md                     # This master document
```

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed
- Arduino IDE 2.0+ (with Arduino UNO R4 Board Package & WiFiS3, DFRobot_DHT11, Adafruit_SSD1306 libraries)
- Web browser (Chrome, Firefox, Edge, Safari)
- (Optional) Supabase free account for cloud database

---

### 2. Run the FastAPI Backend
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server listening on all interfaces (LAN & Hotspot accessible)
python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```
- **Backend Health Check:** [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health) or [http://YOUR_BACKEND_HOST:5000/health](http://YOUR_BACKEND_HOST:5000/health)
- **Interactive OpenAPI Docs:** [http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs)

---

### 3. Run the Frontend
In a separate terminal:
```bash
cd frontend

# Start lightweight HTTP server
python -m http.server 8000
```
- **Dashboard:** [http://127.0.0.1:8000/dashboard.html](http://127.0.0.1:8000/dashboard.html)
- **Login:** [http://127.0.0.1:8000/login.html](http://127.0.0.1:8000/login.html)
- **Home:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

### 4. Device Registration & Arduino Setup

#### Device Registration Procedure:
1. Authenticate as farmer or generate demo token via `POST http://YOUR_BACKEND_HOST:5000/auth/demo-token`.
2. Get your `farm_id` via `GET http://127.0.0.1:5000/farms`.
3. Register your Arduino device via `POST http://127.0.0.1:5000/devices`:
   ```json
   {
     "farm_id": "YOUR_FARM_ID",
     "device_name": "Arduino UNO R4 WiFi Node",
     "device_api_key": "device_api_key",
     "status": "active"
   }
   ```
4. Configure `arduino/agroguard_device_telemetry/arduino_secrets.h`:
   ```cpp
   #define SECRET_SSID     "YOUR_PHONE_HOTSPOT"
   #define SECRET_PASS     "YOUR_HOTSPOT_PASSWORD"
   #define DEVICE_ID       "DEVICE_ID"
   #define DEVICE_API_KEY  "DEVICE_API_KEY"
   #define SERVER_HOST     "SERVER_HOST"
   #define SERVER_PORT     5000
   ```
5. Open `arduino/agroguard_device_telemetry/agroguard_device_telemetry.ino` in Arduino IDE, select board **Arduino UNO R4 WiFi**, and upload!

---

## Agronomic Decision Models

1. **AFHI (Adaptive Farm Health Index)**:
   Authoritative multi-criteria decision model (0–100 score):
   `AFHI = (SM * 0.30) + (T * 0.20) + (H * 0.15) + (R * 0.20) + (W * 0.15)`
   - Status: `Excellent` (80–100), `Good` (60–79), `Needs Attention` (40–59), `Critical` (<40).

2. **CAII (Crop Adaptive Irrigation Intelligence)**:
   Prioritized 7-state irrigation automation model with rain suspension and tank depletion safeguards.

3. **SPAE (Smart Pesticide Advisory Engine)**:
   Environmental spray suitability assessment (Suitable / Caution / Unsafe) factoring drift, evaporation, and wash-off risks.


## Team Setup and Security Notes

- This repository intentionally does **not** include `arduino_secrets.h`. Copy `arduino_secrets.example.h` in the relevant Arduino sketch folder to `arduino_secrets.h`, then fill in your own Wi-Fi credentials.
- Configure the device ID, device API key, and backend host for your own local network before uploading the sketch.
- Keep `.env` and all real credentials private. Never commit passwords, access tokens, service-role keys, or JWT signing secrets.
- `YOUR_BACKEND_HOST` is a placeholder. Use `127.0.0.1` for local browser tests, and the computer's reachable LAN IP for an Arduino on the same network.
