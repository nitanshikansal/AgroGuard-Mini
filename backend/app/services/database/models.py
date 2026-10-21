from ..firestore_models import (
    generate_id,
    current_timestamp,
    ModelValidationError,
    validate_farm,
    validate_device,
    validate_sensor_reading,
    validate_farm_health,
    validate_advisory,
    validate_alert,
    validate_pump_event
)

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
    auth_user_id = str(data.get("auth_user_id") or data.get("authUserId") or "").strip()
    email = str(data.get("email", "")).strip()
    lang = str(data.get("preferred_language") or data.get("preferredLanguage") or "en").strip()
    region = str(data.get("region", "")).strip()
    created_at = data.get("created_at") or data.get("createdAt") or now

    res = {
        "id": farmer_id,
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
    if auth_user_id:
        res["auth_user_id"] = auth_user_id
        res["authUserId"] = auth_user_id
    return res

__all__ = [
    'generate_id',
    'current_timestamp',
    'ModelValidationError',
    'validate_farmer',
    'validate_farm',
    'validate_device',
    'validate_sensor_reading',
    'validate_farm_health',
    'validate_advisory',
    'validate_alert',
    'validate_pump_event'
]
