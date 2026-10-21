"""
AgroGuard CAII — Crop Adaptive Irrigation Intelligence
======================================================
Deterministic decision-support engine that analyzes soil moisture,
precipitation status, water reservoir capacity, and active pump state
to formulate priority-governed irrigation guidance.

States:
- Irrigation Running
- Irrigation Suspended
- Water Unavailable
- Irrigation Required
- Irrigation Recommended
- High Saturation
- Moisture Adequate
"""

from typing import Dict, Any, Union


class CAIIEngine:
    """Evaluates crop watering needs with strict hierarchical safety priority."""

    # Centralized configurable thresholds (ready for crop-specific customization)
    THRESHOLDS = {
        "critical_moisture_low": 25.0,    # Below this: plant wilt danger
        "recommended_moisture_low": 40.0, # Below this: irrigation recommended
        "optimal_moisture_high": 75.0,    # Above this: saturation hazard
        "critical_water_level_low": 20.0  # Below this: pump dry-run risk
    }

    @staticmethod
    def _is_rain_detected(rain_status: Any) -> bool:
        """Helper to determine whether precipitation is active."""
        if isinstance(rain_status, bool):
            return rain_status
        if isinstance(rain_status, (int, float)):
            return rain_status > 0
        if isinstance(rain_status, str):
            return rain_status.strip().lower() not in ("no rain", "none", "false", "0", "")
        return False

    @classmethod
    def evaluate(cls, telemetry: Dict[str, Any], is_pump_active: bool = False) -> Dict[str, Any]:
        """
        Executes priority-based irrigation logic.

        Priority:
        1. Irrigation Running (pump active)
        2. Rain detected -> Irrigation Suspended (conserve water, avoid waterlogging)
        3. Low water level (<20%) -> Water Unavailable (prevent pump burnout)
        4. Soil moisture < 25% -> Irrigation Required (prevent crop wilt)
        5. Soil moisture < 40% -> Irrigation Recommended
        6. Soil moisture > 75% -> High Saturation (avoid waterlogging)
        7. Otherwise -> Moisture Adequate
        """
        moisture = float(telemetry.get("soil_moisture", 45.0))
        rain = telemetry.get("rain_status", "No Rain")
        water_level = float(telemetry.get("water_level", 75.0))
        is_raining = cls._is_rain_detected(rain)

        # 1. Pump already running
        if is_pump_active:
            return {
                "state": "Irrigation Running",
                "action": "monitor",
                "message": "Irrigation system is actively running. Monitoring soil moisture saturation.",
                "pump_active": True
            }

        # 2. Rain detected
        if is_raining:
            return {
                "state": "Irrigation Suspended",
                "action": "hold",
                "message": "Precipitation detected. Automated irrigation suspended to conserve water.",
                "pump_active": False
            }

        # 3. Water reservoir critically low
        if water_level < cls.THRESHOLDS["critical_water_level_low"]:
            return {
                "state": "Water Unavailable",
                "action": "refill_tank",
                "message": f"Storage tank water level is critically low ({water_level:.1f}%). Refill tank before operating pump.",
                "pump_active": False
            }

        # 4. Soil moisture critically low
        if moisture < cls.THRESHOLDS["critical_moisture_low"]:
            return {
                "state": "Irrigation Required",
                "action": "start_pump",
                "message": f"Soil moisture is critically low ({moisture:.1f}%). Immediate irrigation required to prevent crop wilt.",
                "pump_active": False
            }

        # 5. Soil moisture moderately low
        if moisture < cls.THRESHOLDS["recommended_moisture_low"]:
            return {
                "state": "Irrigation Recommended",
                "action": "prepare_irrigation",
                "message": f"Soil moisture is below optimal threshold ({moisture:.1f}%). Irrigation cycle recommended.",
                "pump_active": False
            }

        # 6. High soil saturation
        if moisture > cls.THRESHOLDS["optimal_moisture_high"]:
            return {
                "state": "High Saturation",
                "action": "drain_or_hold",
                "message": f"Soil moisture saturation is high ({moisture:.1f}%). Avoid watering to protect root aeration.",
                "pump_active": False
            }

        # 7. Optimal / Adequate moisture
        return {
            "state": "Moisture Adequate",
            "action": "none",
            "message": f"Soil moisture is optimal ({moisture:.1f}%). No watering required at this time.",
            "pump_active": False
        }


caii_engine = CAIIEngine()
