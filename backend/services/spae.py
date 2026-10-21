"""
AgroGuard SPAE — Smart Pesticide Advisory Engine
================================================
Deterministic environmental suitability engine that evaluates whether ambient
meteorological conditions are safe and effective for foliar spray applications.

Safety Notice:
SPAE strictly provides environmental condition suitability guidance. It DOES NOT
prescribe chemical formulations, active ingredients, dosages, or unsafe application
instructions.

States:
- Suitable: Conditions are agronomically favorable for spray application.
- Caution: High humidity or extreme temperature may compromise efficacy or increase phytotoxicity risk.
- Unsafe: Precipitation or imminent rainfall will cause chemical wash-off and environmental contamination.
"""

from typing import Dict, Any


class SPAEEngine:
    """Evaluates environmental suitability for pesticide/foliar application."""

    # Centralized thresholds for environmental spray suitability
    THRESHOLDS = {
        "max_humidity": 85.0,    # % - prolonged drying time and fungal spread
        "max_temp": 35.0,        # °C - rapid volatilization & chemical scorch risk
        "min_temp": 10.0         # °C - slowed uptake & reduced biological efficacy
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
    def evaluate(cls, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates ambient weather conditions (rain, humidity, temperature).

        Returns:
            {
                "state": "Suitable" | "Caution" | "Unsafe",
                "action": "proceed_with_care" | "delay_or_recheck" | "delay_spraying",
                "message": str,
                "factors": {
                    "rain_detected": bool,
                    "humidity_high": bool,
                    "temperature_extreme": bool
                }
            }
        """
        rain = telemetry.get("rain_status", "No Rain")
        humidity = float(telemetry.get("humidity", 60.0))
        temp = float(telemetry.get("temperature", 25.0))

        is_raining = cls._is_rain_detected(rain)
        is_humidity_high = humidity > cls.THRESHOLDS["max_humidity"]
        is_temp_extreme = (temp > cls.THRESHOLDS["max_temp"] or temp < cls.THRESHOLDS["min_temp"])

        # 1. Unsafe: Rain detected
        if is_raining:
            return {
                "state": "Unsafe",
                "action": "delay_spraying",
                "message": "Precipitation detected. Do not spray; rainfall causes immediate chemical wash-off and groundwater runoff.",
                "factors": {
                    "rain_detected": True,
                    "humidity_high": is_humidity_high,
                    "temperature_extreme": is_temp_extreme
                }
            }

        # 2. Caution: High humidity or thermal extremes
        if is_humidity_high or is_temp_extreme:
            caution_reasons = []
            if is_humidity_high:
                caution_reasons.append(f"high humidity ({humidity:.1f}%)")
            if temp > cls.THRESHOLDS["max_temp"]:
                caution_reasons.append(f"high ambient temperature ({temp:.1f}°C)")
            elif temp < cls.THRESHOLDS["min_temp"]:
                caution_reasons.append(f"low temperature ({temp:.1f}°C)")

            reasons_str = " and ".join(caution_reasons)
            return {
                "state": "Caution",
                "action": "delay_or_recheck",
                "message": f"Suboptimal spraying conditions due to {reasons_str}. Recheck conditions before application.",
                "factors": {
                    "rain_detected": False,
                    "humidity_high": is_humidity_high,
                    "temperature_extreme": is_temp_extreme
                }
            }

        # 3. Suitable: Favorable conditions
        return {
            "state": "Suitable",
            "action": "proceed_with_care",
            "message": f"Environmental conditions (temp {temp:.1f}°C, humidity {humidity:.1f}%) are favorable for spraying. Follow standard PPE safety protocols.",
            "factors": {
                "rain_detected": False,
                "humidity_high": False,
                "temperature_extreme": False
            }
        }


spae_engine = SPAEEngine()
