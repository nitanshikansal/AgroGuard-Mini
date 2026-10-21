from flask import Blueprint, jsonify
from services.sensor_service import sensor_service
from services.pump_service import pump_service

sensor_bp = Blueprint('sensor_bp', __name__)

@sensor_bp.route('/sensor', methods=['GET'])
def get_sensor_data():
    """
    Returns latest sensor readings:
    - soil moisture
    - temperature
    - humidity
    - rain status
    - water level
    - timestamp
    """
    # Trigger mild ambient micro-drift on fetch
    sensor_service.update_simulation_tick(is_pump_active=pump_service.is_active)
    data = sensor_service.get_telemetry()
    return jsonify(data), 200

@sensor_bp.route('/weather', methods=['GET'])
def get_weather_data():
    """Returns local agronomic weather forecast."""
    data = sensor_service.get_weather()
    return jsonify(data), 200
