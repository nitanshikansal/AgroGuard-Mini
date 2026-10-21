"""
AgroGuard Decision Support Engine (Coordinator)
================================================
Coordinates the three core AgroGuard decision-support methodologies:
1. AFHI (Adaptive Farm Health Index)
2. CAII (Crop Adaptive Irrigation Intelligence)
3. SPAE (Smart Pesticide Advisory Engine)

Also exposes alert-ready state descriptors for consumption by downstream
notification modules.
"""

from typing import Dict, Any, List
from .afhi import afhi_engine
from .caii import caii_engine
from .spae import spae_engine


class DecisionEngine:
    """Coordinates AgroGuard decision support modules."""

    def evaluate_farm_health(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates the full AFHI health report."""
        return afhi_engine.calculate(telemetry)

    def evaluate_irrigation(self, telemetry: Dict[str, Any], is_pump_active: bool = False) -> Dict[str, Any]:
        """Evaluates CAII irrigation guidance."""
        return caii_engine.evaluate(telemetry, is_pump_active=is_pump_active)

    def evaluate_pesticide_advisory(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates SPAE environmental spraying suitability."""
        return spae_engine.evaluate(telemetry)

    def evaluate_recommendations(self, telemetry: Dict[str, Any], is_pump_active: bool = False) -> Dict[str, Any]:
        """
        Unified agronomic recommendations combining CAII, SPAE, and alert-ready flags.
        Preserves 'crop' and 'irrigation' fields to maintain 100% backward compatibility
        with frontend and existing test suites.
        """
        caii_res = self.evaluate_irrigation(telemetry, is_pump_active=is_pump_active)
        spae_res = self.evaluate_pesticide_advisory(telemetry)
        alerts_ready = self.evaluate_alerts_ready(telemetry, is_pump_active, caii_res, spae_res)

        return {
            "crop": "Maize (Corn)",
            "irrigation": caii_res["message"],
            "caii": caii_res,
            "spae": spae_res,
            "alerts_ready": alerts_ready
        }

    def evaluate_alerts_ready(
        self,
        telemetry: Dict[str, Any],
        is_pump_active: bool,
        caii_res: Dict[str, Any] = None,
        spae_res: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates structured alert candidates matching frontend alert categories
        without duplicate notification triggers.
        """
        alerts = []
        moisture = float(telemetry.get("soil_moisture", 45.0))
        water_level = float(telemetry.get("water_level", 75.0))
        rain = telemetry.get("rain_status", "No Rain")

        # Rain detected
        is_raining = False
        if isinstance(rain, bool):
            is_raining = rain
        elif isinstance(rain, str):
            is_raining = rain.strip().lower() not in ("no rain", "none", "false", "0", "")
        if is_raining:
            alerts.append({
                "type": "rain_detected",
                "severity": "info",
                "title": "Rain Detected",
                "message": "Rainfall detected in your farm area. Irrigation suspended."
            })

        # Low soil moisture
        if moisture < 25.0:
            alerts.append({
                "type": "low_soil_moisture",
                "severity": "critical",
                "title": "Critical Soil Moisture",
                "message": f"Soil moisture dropped to {moisture:.1f}%. Immediate watering required."
            })

        # Low water level
        if water_level < 20.0:
            alerts.append({
                "type": "low_water_level",
                "severity": "warning",
                "title": "Low Water Level",
                "message": f"Storage tank reserves at {water_level:.1f}%. Please refill tank."
            })

        # Irrigation state alerts
        if is_pump_active:
            alerts.append({
                "type": "irrigation_started",
                "severity": "info",
                "title": "Irrigation Active",
                "message": "Water pump is actively running."
            })
        elif caii_res and caii_res.get("state") == "Irrigation Required":
            alerts.append({
                "type": "irrigation_required",
                "severity": "warning",
                "title": "Irrigation Required",
                "message": caii_res.get("message")
            })

        # Unsuitable pesticide conditions
        if spae_res and spae_res.get("state") in ("Caution", "Unsafe"):
            alerts.append({
                "type": "unsuitable_pesticide_conditions",
                "severity": "warning" if spae_res.get("state") == "Caution" else "critical",
                "title": f"Pesticide Spray Advisory: {spae_res.get('state')}",
                "message": spae_res.get("message")
            })

        return alerts


decision_engine = DecisionEngine()
