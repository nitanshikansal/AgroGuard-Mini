from flask import Blueprint, jsonify, request
from services.pump_service import pump_service
from services.firestore_service import firestore_service

control_bp = Blueprint('control_bp', __name__)

@control_bp.route('/control/pump', methods=['GET'])
def get_pump_status():
    """Returns the current state and operating mode of the irrigation pump."""
    return jsonify(pump_service.get_status()), 200

@control_bp.route('/control/pump', methods=['POST'])
def set_pump_state():
    """
    Sets the operating state of the irrigation pump.
    Accepts JSON body: {"active": bool} or {"state": "ON"|"OFF"}
    Records pump state transition in Firestore.
    """
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Bad Request", "message": "JSON body required."}), 400

    new_state = None
    if "active" in data:
        val = data.get("active")
        if isinstance(val, bool):
            new_state = val
        elif isinstance(val, (int, float)):
            new_state = bool(val)
        elif str(val).lower() in ("true", "1", "on"):
            new_state = True
        elif str(val).lower() in ("false", "0", "off"):
            new_state = False

    if new_state is None and "state" in data:
        state_str = str(data["state"]).strip().upper()
        if state_str in ("ON", "RUNNING", "TRUE", "1"):
            new_state = True
        elif state_str in ("OFF", "STOPPED", "FALSE", "0"):
            new_state = False

    if new_state is None:
        return jsonify({"error": "Bad Request", "message": "Field 'active' or 'state' is required."}), 400

    # Actuate state
    result = pump_service.set_pump_state(new_state)

    # Record event in Firestore
    try:
        farm_id = data.get("farm_id") or data.get("farmId") or "default_farm"
        device_id = data.get("device_id") or data.get("deviceId") or "arduino_r4_pump"
        source = data.get("triggered_by") or data.get("source") or "dashboard_manual"
        reason = data.get("reason", "")
        firestore_service.record_pump_event({
            "farm_id": farm_id,
            "device_id": device_id,
            "action": "ON" if new_state else "OFF",
            "triggered_by": source,
            "reason": reason
        })
    except Exception as e:
        print(f"[CONTROL WARNING] Failed to record pump event in database: {e}")

    # Add dual response keys for maximum client compatibility
    result["action"] = "ON" if new_state else "OFF"
    result["pump_state"] = "ON" if new_state else "OFF"
    result["state"] = "running" if new_state else "stopped"
    result["status_text"] = f"Pump turned {'ON' if new_state else 'OFF'}"
    return jsonify(result), 200
