import random
from datetime import datetime, timezone

class SensorService:
    """
    Centralized sensor service managing simulated environmental parameters.
    Designed so it can be swapped seamlessly with Arduino UNO R4 WiFi data
    in future hardware integration tasks without modifying route signatures.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SensorService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # Telemetry State (aligned with AgroGuard frontend requirements)
        self.soil_moisture = 45.0      # Volumetric percentage (%)
        self.temperature = 27.4        # Ambient degrees Celsius (°C)
        self.humidity = 62.0           # Relative humidity percentage (%)
        self.rain_status = "No Rain"   # "No Rain" | "Light Rain" | "Heavy Storm"
        self.water_level = 78.0        # Tank volume level (%)
        self.last_updated = datetime.now(timezone.utc)

        # Sparkline Telemetry History (last 10 data points)
        self.moisture_history = [40.0, 42.0, 41.0, 43.0, 44.0, 46.0, 45.0, 44.0, 45.0, 45.0]

    def update_simulation_tick(self, is_pump_active: bool = False):
        """
        Executes a realistic micro-fluctuation step.
        Watering rises moisture and depletes tank if pump is running.
        """
        if is_pump_active:
            # Active watering increases moisture and drains tank
            self.soil_moisture = min(85.0, round(self.soil_moisture + 3.5, 1))
            self.water_level = max(10.0, round(self.water_level - 1.2, 1))
        else:
            # Natural moisture dissipation
            self.soil_moisture = max(15.0, round(self.soil_moisture - 0.2 + random.uniform(-0.1, 0.1), 1))

        # Ambient temperature and humidity drift
        self.temperature = max(12.0, min(45.0, round(self.temperature + random.uniform(-0.3, 0.3), 1)))
        self.humidity = max(25.0, min(95.0, round(self.humidity + random.uniform(-0.8, 0.8), 1)))

        # Keep history buffer updated
        self.moisture_history.append(self.soil_moisture)
        if len(self.moisture_history) > 10:
            self.moisture_history.pop(0)

        self.last_updated = datetime.now(timezone.utc)

    def get_telemetry(self) -> dict:
        """Returns the current sensor telemetry payload."""
        return {
            "soil_moisture": round(self.soil_moisture, 1),
            "temperature": round(self.temperature, 1),
            "humidity": round(self.humidity, 1),
            "rain_status": self.rain_status,
            "water_level": round(self.water_level, 1),
            "timestamp": self.last_updated.isoformat()
        }

    def get_weather(self) -> dict:
        """Returns the localized agronomic weather forecast."""
        return {
            "temp": round(self.temperature),
            "condition": "Partly Cloudy" if self.rain_status == "No Rain" else "Rain Showers",
            "high": round(self.temperature + 4.0),
            "low": round(self.temperature - 5.0)
        }

    def get_moisture_history(self) -> list:
        return list(self.moisture_history)

# Global singleton
sensor_service = SensorService()
