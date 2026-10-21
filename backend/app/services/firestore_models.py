"""
AgroGuard Firestore Data Models & Validation
=============================================
Defines validation schemas and timestamp formatting for the 8 core Firestore collections:
1. farmers
2. farms
3. devices
4. sensor_readings
5. farm_health
6. advisories
7. alerts
8. pump_events
"""

from datetime import datetime, timezone
import uuid

def generate_id(prefix=""):
    """Generates an alphanumeric unique identifier with an optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"

def current_timestamp():
    """Generates a standardized UTC ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).isoformat()

class ModelValidationError(Exception):
    """Raised when incoming document data fails validation."""
    pass

def validate_farmer(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Farmer payload must be a JSON object.")
    
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    if not name:
        raise ModelValidationError("Field 'name' is required.")
    if not phone:
        raise ModelValidationError("Field 'phone' is required.")

    now = current_timestamp()
    farmer_id = str(data.get("farmer_id") or data.get("farmerId") or generate_id("farmer_")).strip()
    email = str(data.get("email", "")).strip()
    lang = str(data.get("preferred_language") or data.get("preferredLanguage") or "en").strip()
    region = str(data.get("region", "")).strip()
    created_at = data.get("created_at") or data.get("createdAt") or now

    return {
        "farmer_id": farmer_id,
        "farmerId": farmer_id,
        "name": name,
        "phone": phone,
        "email": email,
        "preferred_language": lang,
        "preferredLanguage": lang,
        "region": region,
        "created_at": created_at,
        "createdAt": created_at,
        "updated_at": now,
        "updatedAt": now
    }

def validate_farm(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Farm payload must be a JSON object.")
    
    farmer_id = str(data.get("farmer_id") or data.get("farmerId") or "").strip()
    farm_name = str(data.get("name") or data.get("farm_name") or data.get("farmName") or "").strip()
    if not farmer_id:
        raise ModelValidationError("Field 'farmer_id' (or 'farmerId') is required.")
    if not farm_name:
        raise ModelValidationError("Field 'name' (or 'farm_name' / 'farmName') is required.")

    now = current_timestamp()
    farm_id = str(data.get("farm_id") or data.get("farmId") or generate_id("farm_")).strip()
    crop_type = str(data.get("crop_type") or data.get("crop") or "Wheat").strip()
    soil_type = str(data.get("soil_type") or data.get("soilType") or "Loamy").strip()
    location = data.get("location", "Default Location")
    try:
        area = float(data.get("area_acres") or data.get("area") or 1.0)
    except (ValueError, TypeError):
        area = 1.0

    created_at = data.get("created_at") or data.get("createdAt") or now

    return {
        "farm_id": farm_id,
        "farmId": farm_id,
        "farmer_id": farmer_id,
        "farmerId": farmer_id,
        "name": farm_name,
        "farm_name": farm_name,
        "farmName": farm_name,
        "location": location,
        "crop_type": crop_type,
        "crop": crop_type,
        "soil_type": soil_type,
        "soilType": soil_type,
        "area_acres": area,
        "area": area,
        "created_at": created_at,
        "createdAt": created_at,
        "updated_at": now,
        "updatedAt": now
    }

def validate_device(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Device payload must be a JSON object.")

    farm_id = str(data.get("farm_id") or data.get("farmId") or "default_farm").strip()
    device_id = str(data.get("device_id") or data.get("deviceId") or generate_id("device_")).strip()
    device_type = str(data.get("device_type") or data.get("deviceType") or "Arduino UNO R4 WiFi").strip()
    device_name = str(data.get("device_name") or data.get("deviceName") or data.get("name") or "AgroGuard Controller").strip()
    status = str(data.get("status") or "active").strip()
    device_api_key = str(data.get("device_api_key") or data.get("deviceApiKey") or data.get("api_key") or "").strip()
    ip_address = str(data.get("ip_address") or data.get("ipAddress") or "").strip()
    mac_address = str(data.get("mac_address") or data.get("macAddress") or "").strip()
    firmware_version = str(data.get("firmware_version") or data.get("firmwareVersion") or "1.0.0").strip()

    now = current_timestamp()
    created_at = data.get("created_at") or data.get("createdAt") or now
    last_seen = data.get("last_seen") or data.get("lastSeen") or now

    return {
        "device_id": device_id,
        "deviceId": device_id,
        "farm_id": farm_id,
        "farmId": farm_id,
        "device_type": device_type,
        "deviceType": device_type,
        "device_name": device_name,
        "deviceName": device_name,
        "status": status,
        "device_api_key": device_api_key,
        "deviceApiKey": device_api_key,
        "ip_address": ip_address,
        "ipAddress": ip_address,
        "mac_address": mac_address,
        "macAddress": mac_address,
        "firmware_version": firmware_version,
        "firmwareVersion": firmware_version,
        "last_seen": last_seen,
        "lastSeen": last_seen,
        "created_at": created_at,
        "createdAt": created_at
    }

def validate_sensor_reading(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Sensor reading payload must be a JSON object.")

    reading_id = str(data.get("reading_id") or data.get("readingId") or generate_id("read_")).strip()
    farm_id = str(data.get("farm_id") or data.get("farmId") or "default_farm").strip()
    device_id = str(data.get("device_id") or data.get("deviceId") or "arduino_r4_default").strip()

    try:
        sm = float(data.get("soil_moisture") if data.get("soil_moisture") is not None else data.get("soilMoisture", 45.0))
        temp = float(data.get("temperature", 25.0))
        hum = float(data.get("humidity", 60.0))
        wl = float(data.get("water_level") if data.get("water_level") is not None else data.get("waterLevel", 75.0))
    except (ValueError, TypeError) as e:
        raise ModelValidationError(f"Sensor metrics must be numeric: {e}")

    try:
        light_lux = float(data.get("light_lux") or data.get("lightLux") or 0.0)
    except (ValueError, TypeError):
        light_lux = 0.0

    crop_type = str(data.get("crop_type") or data.get("crop") or "Wheat").strip()

    rain_raw = data.get("rain_status") if data.get("rain_status") is not None else data.get("rainStatus", "No Rain")
    if isinstance(rain_raw, bool):
        rain_str = "Raining" if rain_raw else "No Rain"
    elif isinstance(rain_raw, (int, float)):
        rain_str = "Raining" if rain_raw > 0 else "No Rain"
    else:
        rain_str = str(rain_raw).strip()

    now = current_timestamp()
    ts = data.get("timestamp", now)

    return {
        "reading_id": reading_id,
        "readingId": reading_id,
        "farm_id": farm_id,
        "farmId": farm_id,
        "device_id": device_id,
        "deviceId": device_id,
        "soil_moisture": round(sm, 1),
        "soilMoisture": round(sm, 1),
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "rain_status": rain_str,
        "rainStatus": rain_str,
        "water_level": round(wl, 1),
        "waterLevel": round(wl, 1),
        "light_lux": light_lux,
        "lightLux": light_lux,
        "crop_type": crop_type,
        "crop": crop_type,
        "timestamp": ts
    }

def validate_farm_health(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Farm health payload must be a JSON object.")

    health_id = str(data.get("health_id") or data.get("healthId") or generate_id("afhi_")).strip()
    farm_id = str(data.get("farm_id") or data.get("farmId") or "default_farm").strip()
    score = float(data.get("afhi_score") if data.get("afhi_score") is not None else (data.get("afhiScore") if data.get("afhiScore") is not None else data.get("score", 85.0)))
    status = str(data.get("health_status") or data.get("status") or "Good").strip()
    breakdown = data.get("breakdown") or data.get("components") or {}

    now = current_timestamp()
    ts = data.get("timestamp", now)

    return {
        "health_id": health_id,
        "healthId": health_id,
        "farm_id": farm_id,
        "farmId": farm_id,
        "afhi_score": round(score, 1),
        "afhiScore": round(score, 1),
        "score": round(score, 1),
        "health_status": status,
        "status": status,
        "breakdown": breakdown,
        "components": breakdown,
        "timestamp": ts
    }

def validate_advisory(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Advisory payload must be a JSON object.")

    advisory_id = str(data.get("advisory_id") or data.get("advisoryId") or generate_id("adv_")).strip()
    farm_id = str(data.get("farm_id") or data.get("farmId") or "default_farm").strip()
    adv_type = str(data.get("type", "consolidated")).strip()
    message = str(data.get("message", "")).strip()
    recommendation = str(data.get("recommendation", "")).strip()
    irrigation = data.get("irrigation") or data.get("caii") or {}
    pesticide = data.get("pesticide") or data.get("spae") or {}

    now = current_timestamp()
    ts = data.get("timestamp", now)

    return {
        "advisory_id": advisory_id,
        "advisoryId": advisory_id,
        "farm_id": farm_id,
        "farmId": farm_id,
        "type": adv_type,
        "message": message,
        "recommendation": recommendation,
        "irrigation": irrigation,
        "caii": irrigation,
        "pesticide": pesticide,
        "spae": pesticide,
        "timestamp": ts
    }

def validate_alert(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Alert payload must be a JSON object.")

    alert_id = str(data.get("alert_id") or data.get("alertId") or generate_id("alert_")).strip()
    farm_id = str(data.get("farm_id") or data.get("farmId") or "default_farm").strip()
    device_id = str(data.get("device_id") or data.get("deviceId") or "default_device").strip()
    alert_type = str(data.get("alert_type") or data.get("alertType") or data.get("type") or "info").strip()
    severity = str(data.get("severity") or alert_type).strip()
    title = str(data.get("title", "Farm Alert")).strip()
    message = str(data.get("message", "")).strip()
    category = str(data.get("category", "general")).strip()
    status = str(data.get("status", "unread")).strip()
    acknowledged = bool(data.get("acknowledged", False) or status == "acknowledged")

    now = current_timestamp()
    ts = data.get("timestamp", now)

    return {
        "alert_id": alert_id,
        "alertId": alert_id,
        "farm_id": farm_id,
        "farmId": farm_id,
        "device_id": device_id,
        "deviceId": device_id,
        "alert_type": alert_type,
        "alertType": alert_type,
        "type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "category": category,
        "status": status,
        "acknowledged": acknowledged,
        "timestamp": ts
    }

def validate_pump_event(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ModelValidationError("Pump event payload must be a JSON object.")

    event_id = str(data.get("event_id") or data.get("eventId") or generate_id("event_")).strip()
    farm_id = str(data.get("farm_id") or data.get("farmId") or "default_farm").strip()
    device_id = str(data.get("device_id") or data.get("deviceId") or "arduino_r4_pump").strip()
    
    raw_state = data.get("action") if data.get("action") is not None else data.get("state")
    if isinstance(raw_state, bool):
        action = "ON" if raw_state else "OFF"
    else:
        s = str(raw_state).strip().upper()
        action = "ON" if s in ("ON", "RUNNING", "TRUE", "1") else "OFF"

    triggered_by = str(data.get("triggered_by") or data.get("source") or "dashboard").strip()
    reason = str(data.get("reason", "")).strip()

    now = current_timestamp()
    ts = data.get("timestamp", now)

    return {
        "event_id": event_id,
        "eventId": event_id,
        "farm_id": farm_id,
        "farmId": farm_id,
        "device_id": device_id,
        "deviceId": device_id,
        "action": action,
        "state": "running" if action == "ON" else "stopped",
        "triggered_by": triggered_by,
        "source": triggered_by,
        "reason": reason,
        "timestamp": ts
    }
