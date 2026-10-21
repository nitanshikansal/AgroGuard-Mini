# AgroGuard FastAPI REST Backend API

High-performance, asynchronous Python **FastAPI** backend serving real-time simulated telemetry, agronomic weather forecasts, farm health grading (AFHI), crop adaptive irrigation intelligence (CAII), smart pesticide advisories (SPAE), manual pump actuator controls, and multi-tenant Firestore/in-memory database repository for the **AgroGuard Smart Agriculture Decision Support System**.

---

## Key Features

- **FastAPI Framework**: High performance, automatic OpenAPI schema generation, built-in validation via Pydantic v2.
- **Interactive API Documentation**:
  - Swagger UI: `http://127.0.0.1:5000/docs`
  - ReDoc: `http://127.0.0.1:5000/redoc`
  - OpenAPI Spec: `http://127.0.0.1:5000/openapi.json`
- **AgroGuard Decision Support Engine**:
  - **AFHI** (Adaptive Farm Health Index): Multi-metric weighted health scoring (0-100).
  - **CAII** (Crop Adaptive Irrigation Intelligence): Soil moisture deficit, rain delay, irrigation decision.
  - **SPAE** (Smart Pesticide Advisory Engine): Weather safety scoring, spray window advisory.
- **Database Layer**: Multi-tenant repository supporting Farmers, Farms, Devices, Telemetry Readings, Advisories, Alerts, and Pump Events with seamless in-memory fallback and optional Google Cloud Firestore.
- **CORS Configured**: Seamless integration with local frontend servers (e.g. `http://127.0.0.1:8000`).

---

## Directory Architecture

```
agroguard-backend/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic BaseSettings (Host, Port, CORS, Simulation)
│   ├── main.py                   # FastAPI app factory, CORS middleware, global error handlers
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── sensor_routes.py      # /sensor, /weather
│   │   ├── dashboard_routes.py   # /dashboard, /farm-health, /recommendation
│   │   ├── control_routes.py     # /control/pump (GET, POST)
│   │   └── database_routes.py    # /farmers, /farms, /devices, /alerts, /sensor/readings...
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── sensor_service.py     # Centralized simulated telemetry provider
│       ├── decision_engine.py    # Decision engine wrapper
│       ├── afhi.py               # AFHI calculation module
│       ├── caii.py               # CAII calculation module
│       ├── spae.py               # SPAE calculation module
│       ├── pump_service.py       # Actuator state management
│       ├── firestore_service.py  # Repository provider (Firestore + In-Memory Fallback)
│       └── firestore_models.py   # Domain data models & validation
├── run.py                        # Uvicorn entrypoint script
├── app.py                        # Backwards-compatible entrypoint
├── requirements.txt              # FastAPI, Uvicorn, Pydantic, Firebase-Admin
└── README.md                     # Documentation & API reference
```

---

## Quick Start

### 1. Create and Activate Virtual Environment

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the FastAPI Server

Using Uvicorn CLI:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 5000 --reload
```

Or using `run.py`:
```bash
python run.py
```

The server will start on **`http://127.0.0.1:5000`**.

---

## API Endpoints Reference

### Core Telemetry & Decision Engine
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status & timestamp |
| `GET` | `/sensor` | Current telemetry (`soil_moisture`, `temperature`, `humidity`, `rain_status`, `water_level`) |
| `GET` | `/weather` | Local agronomic weather forecast |
| `GET` | `/dashboard` | Consolidated telemetry, weather, health, recommendation & pump state |
| `GET` | `/farm-health` | AFHI plot wellness score, status, and sub-index metrics |
| `GET` | `/recommendation` | CAII irrigation advisory & SPAE pesticide safety window |
| `GET` | `/control/pump` | Irrigation pump actuator status |
| `POST` | `/control/pump` | Set pump state: `{"active": true}` or `{"active": false}` |

### Database & Multi-Farmer Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/database/status` | Firestore connection status and repository mode |
| `POST` | `/farmers` | Register a new farmer profile |
| `GET` | `/farmers` | List registered farmers |
| `POST` | `/farms` | Register a new farm plot |
| `GET` | `/farms` | List farms (supports `?farmer_id=<id>`) |
| `POST` | `/devices` | Register an IoT device |
| `GET` | `/devices` | List IoT devices (supports `?farm_id=<id>`) |
| `POST` | `/sensor/readings` | Ingest sensor telemetry record |
| `GET` | `/sensor/readings` | Query historical sensor readings (`?farm_id=<id>&limit=20`) |
| `GET` | `/farm-health/history` | Query historical AFHI logs (`?farm_id=<id>`) |
| `GET` | `/advisories` | Query historical CAII/SPAE advisories (`?farm_id=<id>`) |
| `POST` | `/alerts` | Create farm-specific system alert |
| `GET` | `/alerts` | Query alerts (`?farm_id=<id>&status=active`) |
| `GET` | `/pump/events` | Query historical pump activation logs (`?farm_id=<id>`) |

### Interactive Documentation
- **Swagger UI**: `http://127.0.0.1:5000/docs`
- **ReDoc**: `http://127.0.0.1:5000/redoc`
- **OpenAPI JSON**: `http://127.0.0.1:5000/openapi.json`
