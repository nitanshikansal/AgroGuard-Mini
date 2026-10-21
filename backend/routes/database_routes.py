"""
AgroGuard Firestore Database Routes
====================================
Exposes RESTful endpoints for managing farmers, farms, registered devices,
sensor readings time-series, AFHI farm health audit history, CAII/SPAE advisories,
alerts, and actuator pump events.
"""

from flask import Blueprint, jsonify, request
from services.firestore_service import firestore_service
from services.firestore_models import ModelValidationError
from services.decision_engine import decision_engine

database_bp = Blueprint('database_bp', __name__)

# -----------------------------------------------------------------------------
# DATABASE HEALTH & STATUS
# -----------------------------------------------------------------------------
@database_bp.route('/database/status', methods=['GET'])
def get_database_status():
    """Returns Firestore connection status and record statistics."""
    info = firestore_service.get_status()
    return jsonify({
        "status": "healthy",
        "service": "AgroGuard Firestore Database",
        "initialized": True,
        "collections": info.get("record_counts", {}),
        **info
    }), 200

# -----------------------------------------------------------------------------
# 1. FARMERS ENDPOINTS
# -----------------------------------------------------------------------------
@database_bp.route('/farmers', methods=['POST'])
def create_farmer():
    """Creates or registers a farmer profile in Firestore."""
    data = request.get_json() or {}
    try:
        farmer = firestore_service.save_farmer(data)
        return jsonify({"success": True, "data": farmer, "farmer": farmer}), 201
    except ModelValidationError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400

@database_bp.route('/farmers/<farmer_id>', methods=['GET'])
def get_farmer(farmer_id):
    """Retrieves farmer document by farmer_id."""
    farmer = firestore_service.get_farmer(farmer_id)
    if not farmer:
        return jsonify({"error": "Not Found", "message": f"Farmer '{farmer_id}' not found."}), 404
    return jsonify({"success": True, "data": farmer, **farmer}), 200

# -----------------------------------------------------------------------------
# 2. FARMS ENDPOINTS
# -----------------------------------------------------------------------------
@database_bp.route('/farms', methods=['POST'])
def create_farm():
    """Creates a farm plot record linked to a farmer."""
    data = request.get_json() or {}
    try:
        farm = firestore_service.save_farm(data)
        return jsonify({"success": True, "data": farm, "farm": farm}), 201
    except ModelValidationError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400

@database_bp.route('/farms/<farm_id>', methods=['GET'])
def get_farm(farm_id):
    """Retrieves farm metadata by farm_id."""
    farm = firestore_service.get_farm(farm_id)
    if not farm:
        return jsonify({"error": "Not Found", "message": f"Farm '{farm_id}' not found."}), 404
    return jsonify({"success": True, "data": farm, **farm}), 200

@database_bp.route('/farms', methods=['GET'])
def get_farms():
    """Lists farm plots, optionally filtered by ?farmer_id=... or ?farmerId=..."""
    farmer_id = request.args.get('farmer_id') or request.args.get('farmerId')
    farms = firestore_service.get_farms(farmer_id=farmer_id)
    return jsonify({"success": True, "count": len(farms), "farms": farms, "data": farms}), 200

# -----------------------------------------------------------------------------
# 3. DEVICES ENDPOINTS
# -----------------------------------------------------------------------------
@database_bp.route('/devices', methods=['POST'])
def register_device():
    """Registers an edge IoT controller node."""
    data = request.get_json() or {}
    try:
        device = firestore_service.register_device(data)
        return jsonify({"success": True, "data": device, "device": device}), 201
    except ModelValidationError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400

@database_bp.route('/devices', methods=['GET'])
def get_devices():
    """Lists registered devices, optionally filtered by ?farm_id=... or ?farmId=..."""
    farm_id = request.args.get('farm_id') or request.args.get('farmId')
    devices = firestore_service.get_devices(farm_id=farm_id)
    return jsonify({"success": True, "count": len(devices), "devices": devices, "data": devices}), 200

# -----------------------------------------------------------------------------
# 4. SENSOR READINGS & DECISION PIPELINE ENDPOINTS
# -----------------------------------------------------------------------------
@database_bp.route('/sensor/readings', methods=['POST'])
def record_sensor_reading():
    """
    Ingests sensor reading, pipes it through AFHI/CAII/SPAE Decision Engine,
    and commits telemetry + health grading + advisory to Firestore in one flow!
    """
    data = request.get_json() or {}
    try:
        reading = firestore_service.save_sensor_reading(data)

        # Pipe through AgroGuard Decision Engine
        telemetry_dict = {
            "soil_moisture": reading["soil_moisture"],
            "temperature": reading["temperature"],
            "humidity": reading["humidity"],
            "rain_status": reading["rain_status"],
            "water_level": reading["water_level"]
        }
        health_eval = decision_engine.evaluate_farm_health(telemetry_dict)
        rec_eval = decision_engine.evaluate_recommendations(telemetry_dict)

        # Persist AFHI health evaluation to Firestore
        health_record = firestore_service.save_farm_health({
            "farm_id": reading["farm_id"],
            "afhi_score": health_eval["score"],
            "health_status": health_eval["status"],
            "breakdown": health_eval.get("components", {}),
            "timestamp": reading["timestamp"]
        })

        # Persist CAII/SPAE advisory to Firestore
        advisory_record = firestore_service.save_advisory({
            "farm_id": reading["farm_id"],
            "type": "consolidated",
            "message": rec_eval.get("irrigation", ""),
            "recommendation": rec_eval.get("spae", {}).get("message", ""),
            "irrigation": rec_eval.get("caii", {}),
            "pesticide": rec_eval.get("spae", {}),
            "timestamp": reading["timestamp"]
        })

        return jsonify({
            "success": True,
            "data": reading,
            "reading": reading,
            "processed_afhi": health_eval,
            "processed_advisory": rec_eval,
            "farm_health": health_record,
            "advisory": advisory_record
        }), 201
    except ModelValidationError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400

@database_bp.route('/sensor/readings', methods=['GET'])
def get_sensor_readings():
    """Retrieves recent sensor readings history."""
    farm_id = request.args.get('farm_id') or request.args.get('farmId')
    limit = min(int(request.args.get('limit', 20)), 100)
    readings = firestore_service.get_recent_sensor_readings(farm_id=farm_id, limit=limit)
    return jsonify({"success": True, "count": len(readings), "readings": readings, "data": readings}), 200

# -----------------------------------------------------------------------------
# 5. FARM HEALTH (AFHI) HISTORY
# -----------------------------------------------------------------------------
@database_bp.route('/farm-health/history', methods=['GET'])
def get_farm_health_history():
    """Retrieves AFHI historical evaluations."""
    farm_id = request.args.get('farm_id') or request.args.get('farmId')
    limit = min(int(request.args.get('limit', 20)), 100)
    history = firestore_service.get_farm_health_history(farm_id=farm_id, limit=limit)
    return jsonify({"success": True, "count": len(history), "history": history, "data": history}), 200

# -----------------------------------------------------------------------------
# 6. ADVISORIES HISTORY
# -----------------------------------------------------------------------------
@database_bp.route('/advisories', methods=['GET'])
def get_advisories():
    """Retrieves agronomic recommendations history."""
    farm_id = request.args.get('farm_id') or request.args.get('farmId')
    limit = min(int(request.args.get('limit', 20)), 100)
    advisories = firestore_service.get_recent_advisories(farm_id=farm_id, limit=limit)
    return jsonify({"success": True, "count": len(advisories), "advisories": advisories, "data": advisories}), 200

# -----------------------------------------------------------------------------
# 7. ALERTS ENDPOINTS
# -----------------------------------------------------------------------------
@database_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Retrieves active/recent farm alerts."""
    farm_id = request.args.get('farm_id') or request.args.get('farmId')
    status_filter = request.args.get('status')
    limit = min(int(request.args.get('limit', 20)), 100)
    alerts = firestore_service.get_recent_alerts(farm_id=farm_id, status=status_filter, limit=limit)
    return jsonify({"success": True, "count": len(alerts), "alerts": alerts, "data": alerts}), 200

@database_bp.route('/alerts', methods=['POST'])
def create_alert():
    """Creates a new farm alert record."""
    data = request.get_json() or {}
    try:
        alert = firestore_service.create_alert(data)
        return jsonify({"success": True, "data": alert, "alert": alert}), 201
    except ModelValidationError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400

# -----------------------------------------------------------------------------
# 8. PUMP EVENTS HISTORY
# -----------------------------------------------------------------------------
@database_bp.route('/pump/events', methods=['GET'])
def get_pump_events():
    """Retrieves actuator pump state change history."""
    farm_id = request.args.get('farm_id') or request.args.get('farmId')
    limit = min(int(request.args.get('limit', 20)), 100)
    events = firestore_service.get_pump_events(farm_id=farm_id, limit=limit)
    return jsonify({"success": True, "count": len(events), "events": events, "data": events}), 200
