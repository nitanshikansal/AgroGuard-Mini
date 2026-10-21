from flask import Blueprint, jsonify
from services.sensor_service import sensor_service
from services.pump_service import pump_service
from services.decision_engine import decision_engine

dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
def get_dashboard_summary():
    """
    Returns comprehensive consolidated telemetry, weather,
    farm health, recommendations, and actuator status.
    """
    sensor_service.update_simulation_tick(is_pump_active=pump_service.is_active)
    telemetry = sensor_service.get_telemetry()
    weather = sensor_service.get_weather()
    farm_health = decision_engine.evaluate_farm_health(telemetry)
    recommendation = decision_engine.evaluate_recommendations(telemetry, is_pump_active=pump_service.is_active)
    pump = pump_service.get_status()

    return jsonify({
        "telemetry": telemetry,
        "weather": weather,
        "farmHealth": farm_health,
        "recommendation": recommendation,
        "pump": pump
    }), 200

@dashboard_bp.route('/farm-health', methods=['GET'])
def get_farm_health():
    """Returns farm health evaluation."""
    telemetry = sensor_service.get_telemetry()
    health = decision_engine.evaluate_farm_health(telemetry)
    return jsonify(health), 200

@dashboard_bp.route('/recommendation', methods=['GET'])
def get_recommendation():
    """Returns agronomic crop and watering recommendation."""
    telemetry = sensor_service.get_telemetry()
    rec = decision_engine.evaluate_recommendations(telemetry, is_pump_active=pump_service.is_active)
    return jsonify(rec), 200
