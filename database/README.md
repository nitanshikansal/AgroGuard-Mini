# AgroGuard Database Setup Guide (Supabase PostgreSQL)

## Overview
AgroGuard uses PostgreSQL hosted on Supabase (with high-fidelity in-memory local fallback for development).
The relational database tracks:
1. `farmers` — Farmer user accounts linked to Supabase Auth UID (`auth_user_id`).
2. `farms` — Farm plots linked to farmers.
3. `devices` — Microcontroller nodes (Arduino UNO R4 WiFi, ESP32) with dedicated API key authentication (`device_api_key`) and active status (`status`).
4. `sensor_readings` — Real-time telemetry (soil moisture, temperature, humidity, rain, water level, crop_type).
5. `farm_health` — Historical AFHI (Adaptive Farm Health Index) scores and sub-metric components.
6. `advisories` — Automated CAII (irrigation) & SPAE (pesticide safety) advisory logs.
7. `alerts` — Threshold breach alert notifications (warning, critical, info).
8. `pump_events` — Actuator audit logs recording ON/OFF events, duration, and triggering source.

## Setting Up Supabase

1. Create a free project at [supabase.com](https://supabase.com).
2. Go to the **SQL Editor** in your Supabase dashboard.
3. Copy and run the entire contents of `supabase_schema.sql`.
4. Navigate to **Project Settings -> API**:
   - Copy `Project URL` -> Set as `SUPABASE_URL` in `backend/.env`.
   - Copy `anon public` key -> Set as `SUPABASE_ANON_KEY` in `backend/.env`.
   - Copy `service_role secret` key -> Set as `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`.
5. Navigate to **Project Settings -> API -> JWT Settings**:
   - Copy `JWT Secret` -> Set as `SUPABASE_JWT_SECRET` in `backend/.env`.
6. Start the backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 5000
   ```
   The backend will log:
   `[DATABASE SERVICE] Active Database: Supabase PostgreSQL (...)`
