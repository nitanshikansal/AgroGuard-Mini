"""
AgroGuard AFHI — Adaptive Farm Health Index
============================================
A transparent, explainable, rule-based multi-criteria decision-support methodology
for evaluating overall farm and crop health from real-time environmental telemetry.

Formula:
    AFHI = (SM * 0.30) + (T * 0.20) + (H * 0.15) + (R * 0.20) + (W * 0.15)

Where:
    SM = Normalized Soil Moisture score (0 - 100)
    T  = Normalized Temperature score (0 - 100)
    H  = Normalized Relative Humidity score (0 - 100)
    R  = Normalized Rain-related score (0 - 100)
    W  = Normalized Water Level score (0 - 100)

Note: AFHI is a deterministic, rule-based agronomic decision-support methodology,
not an AI/ML model.
"""

from typing import Dict, Any, Union


class AFHIEngine:
    """Calculates the Adaptive Farm Health Index (AFHI) from telemetry."""

    # Weights defined by AgroGuard AFHI methodology
    WEIGHTS = {
        "soil_moisture": 0.30,
        "temperature": 0.20,
        "humidity": 0.15,
        "rain": 0.20,
        "water_level": 0.15
    }

    # Status classification thresholds
    STATUS_THRESHOLDS = [
        (80.0, "Excellent", "#16a34a"),
        (60.0, "Good", "#22c55e"),
        (40.0, "Needs Attention", "#eab308"),
        (0.0, "Critical", "#ef4444")
    ]

    @classmethod
    def normalize_soil_moisture(cls, moisture: Union[int, float]) -> float:
        """
        Normalizes volumetric soil moisture (%) into a 0 - 100 agronomic wellness score.
        Optimal range: 45% - 65% (score = 100).
        Moderately dry (30% - 45%) or wet (65% - 80%): proportional reduction.
        Critically dry (<30%) or waterlogged (>80%): severe reduction.
        """
        try:
            m = float(moisture)
        except (ValueError, TypeError):
            m = 45.0

        if 45.0 <= m <= 65.0:
            return 100.0
        elif 30.0 <= m < 45.0:
            # Linear scaling from 60 to 100
            return round(60.0 + (m - 30.0) * (40.0 / 15.0), 1)
        elif 0.0 <= m < 30.0:
            # Linear scaling from 0 to 60
            return round(max(0.0, m * 2.0), 1)
        elif 65.0 < m <= 80.0:
            # Linear scaling down from 100 to 70
            return round(100.0 - (m - 65.0) * (30.0 / 15.0), 1)
        else:  # m > 80.0 (saturation / waterlogging)
            return round(max(20.0, 70.0 - (m - 80.0) * 2.5), 1)

    @classmethod
    def normalize_temperature(cls, temp: Union[int, float]) -> float:
        """
        Normalizes ambient temperature (°C) into a 0 - 100 agronomic wellness score.
        Optimal thermal range: 20°C - 30°C (score = 100).
        Mild stress: 15°C - 20°C or 30°C - 36°C (score = 70 - 100).
        Extreme stress: <15°C (frost/chill) or >36°C (heat shock).
        """
        try:
            t = float(temp)
        except (ValueError, TypeError):
            t = 25.0

        if 20.0 <= t <= 30.0:
            return 100.0
        elif 15.0 <= t < 20.0:
            return round(70.0 + (t - 15.0) * 6.0, 1)
        elif t < 15.0:
            return round(max(0.0, 70.0 - (15.0 - t) * 7.0), 1)
        elif 30.0 < t <= 36.0:
            return round(100.0 - (t - 30.0) * 5.0, 1)
        else:  # t > 36.0
            return round(max(0.0, 70.0 - (t - 36.0) * 7.0), 1)

    @classmethod
    def normalize_humidity(cls, humidity: Union[int, float]) -> float:
        """
        Normalizes relative humidity (%) into a 0 - 100 agronomic wellness score.
        Optimal range: 50% - 75% (score = 100).
        Dry stress: <50% (increases evapotranspiration).
        Fungal disease risk: >80% (favorable for pathogens).
        """
        try:
            h = float(humidity)
        except (ValueError, TypeError):
            h = 60.0

        if 50.0 <= h <= 75.0:
            return 100.0
        elif 35.0 <= h < 50.0:
            return round(70.0 + (h - 35.0) * 2.0, 1)
        elif h < 35.0:
            return round(max(10.0, 70.0 - (35.0 - h) * 2.5), 1)
        elif 75.0 < h <= 85.0:
            return round(100.0 - (h - 75.0) * 3.0, 1)
        else:  # h > 85.0
            return round(max(10.0, 70.0 - (h - 85.0) * 4.0), 1)

    @classmethod
    def normalize_rain(cls, rain_status: Any, soil_moisture: float = 45.0) -> float:
        """
        Evaluates rain factor into a 0 - 100 agronomic score.
        Contextualized against current soil moisture:
        - Rain when soil is parched (<35%): highly beneficial (score = 100).
        - Rain when soil is already saturated (>80%): waterlogging hazard (score = 45).
        - Stable clear weather with adequate hydration: favorable (score = 95).
        - Drought (low moisture + no rain): stress factor (score = 40).
        """
        is_raining = False
        if isinstance(rain_status, bool):
            is_raining = rain_status
        elif isinstance(rain_status, (int, float)):
            is_raining = rain_status > 0
        elif isinstance(rain_status, str):
            is_raining = rain_status.strip().lower() not in ("no rain", "none", "false", "0", "")

        if is_raining:
            if soil_moisture > 80.0:
                return 45.0  # Excessive rain hazard
            elif soil_moisture < 35.0:
                return 100.0  # Much needed relief
            return 90.0  # Normal precipitation
        else:
            if soil_moisture < 25.0:
                return 40.0  # Unrelieved drought stress
            elif soil_moisture < 35.0:
                return 65.0  # Developing dry condition
            return 95.0  # Clear sunny conditions

    @classmethod
    def normalize_water_level(cls, water_level: Union[int, float]) -> float:
        """
        Normalizes farm water storage tank level (%) into a 0 - 100 score.
        Adequate reserves (>=70%): score = 100.
        Moderate reserves (40% - 70%): score = 70 - 100.
        Low reserves (20% - 40%): score = 40 - 70.
        Critical depletion (<20%): score = 0 - 40.
        """
        try:
            w = float(water_level)
        except (ValueError, TypeError):
            w = 75.0

        if w >= 70.0:
            return 100.0
        elif 40.0 <= w < 70.0:
            return round(70.0 + (w - 40.0) * 1.0, 1)
        elif 20.0 <= w < 40.0:
            return round(40.0 + (w - 20.0) * 1.5, 1)
        else:  # w < 20.0
            return round(max(0.0, w * 2.0), 1)

    @classmethod
    def calculate(cls, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the AFHI index and returns detailed component breakdown.

        Returns:
            {
                "score": float,
                "status": "Excellent" | "Good" | "Needs Attention" | "Critical",
                "color": str,
                "components": {
                    "soil_moisture": float,
                    "temperature": float,
                    "humidity": float,
                    "rain": float,
                    "water_level": float
                },
                "weights": dict,
                "methodology": str
            }
        """
        raw_sm = telemetry.get("soil_moisture", 45.0)
        raw_t = telemetry.get("temperature", 25.0)
        raw_h = telemetry.get("humidity", 60.0)
        raw_r = telemetry.get("rain_status", "No Rain")
        raw_w = telemetry.get("water_level", 75.0)

        # 1. Normalize components to 0 - 100
        sm_score = cls.normalize_soil_moisture(raw_sm)
        t_score = cls.normalize_temperature(raw_t)
        h_score = cls.normalize_humidity(raw_h)
        r_score = cls.normalize_rain(raw_r, soil_moisture=float(raw_sm) if isinstance(raw_sm, (int, float)) else 45.0)
        w_score = cls.normalize_water_level(raw_w)

        # 2. Compute weighted AFHI
        afhi_raw = (
            (sm_score * cls.WEIGHTS["soil_moisture"]) +
            (t_score * cls.WEIGHTS["temperature"]) +
            (h_score * cls.WEIGHTS["humidity"]) +
            (r_score * cls.WEIGHTS["rain"]) +
            (w_score * cls.WEIGHTS["water_level"])
        )

        # 3. Clamp strictly between 0 and 100
        final_score = round(max(0.0, min(100.0, afhi_raw)), 1)

        # 4. Map to qualitative status
        status = "Critical"
        color = "#ef4444"
        for threshold, label, hex_col in cls.STATUS_THRESHOLDS:
            if final_score >= threshold:
                status = label
                color = hex_col
                break

        return {
            "score": final_score,
            "status": status,
            "color": color,
            "components": {
                "soil_moisture": sm_score,
                "temperature": t_score,
                "humidity": h_score,
                "rain": r_score,
                "water_level": w_score
            },
            "weights": cls.WEIGHTS,
            "methodology": "Rule-based weighted multi-criteria decision-support methodology"
        }


afhi_engine = AFHIEngine()
