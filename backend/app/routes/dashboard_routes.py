from fastapi import APIRouter, Depends
from app.auth import get_current_user, AuthenticatedUser
from app.services.sensor_service import sensor_service
from app.services.decision_engine import decision_engine
from app.services.pump_service import pump_service
from app.services.database import db_service

router = APIRouter(tags=["Dashboard & Decision Support"])

@router.get('/dashboard', summary="Get consolidated farm dashboard telemetry and decision analytics (Protected)")
async def get_dashboard(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns consolidated dashboard payload scoped to the authenticated farmer's farms.
    """
    telemetry = sensor_service.get_telemetry()
    farms = db_service.get_farms(farmer_id=current_user.farmer_id)
    if farms:
        primary_farm_id = farms[0].get("farm_id")
        recent = db_service.get_recent_sensor_readings(farm_id=primary_farm_id, limit=1)
        if recent:
            telemetry.update({
                "soil_moisture": recent[0].get("soil_moisture", telemetry["soil_moisture"]),
                "temperature": recent[0].get("temperature", telemetry["temperature"]),
                "humidity": recent[0].get("humidity", telemetry["humidity"]),
                "rain_status": recent[0].get("rain_status", telemetry["rain_status"]),
                "water_level": recent[0].get("water_level", telemetry["water_level"])
            })

    weather = sensor_service.get_weather()
    farm_health = decision_engine.evaluate_farm_health(telemetry)
    recommendation = decision_engine.evaluate_recommendations(telemetry)
    pump = pump_service.get_status()

    return {
        "telemetry": telemetry,
        "weather": weather,
        "farmHealth": farm_health,
        "recommendation": recommendation,
        "pump": pump,
        "farmer_id": current_user.farmer_id
    }

@router.get('/farm-health', summary="Get current farm health score and grading (Protected)")
async def get_farm_health(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Evaluates current telemetry through the AFHI decision model for authenticated farmer."""
    telemetry = sensor_service.get_telemetry()
    return decision_engine.evaluate_farm_health(telemetry)

@router.get('/recommendation', summary="Get automated crop and irrigation advisory (Protected)")
async def get_recommendation(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Evaluates current conditions through CAII and SPAE models for authenticated farmer."""
    telemetry = sensor_service.get_telemetry()
    return decision_engine.evaluate_recommendations(telemetry)
