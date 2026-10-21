from fastapi import APIRouter, Depends
from app.auth import get_current_user, AuthenticatedUser
from app.services.sensor_service import sensor_service

router = APIRouter(tags=["Sensor Telemetry & Weather"])

@router.get('/sensor', summary="Get real-time sensor telemetry (Protected)")
async def get_sensor_data(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the latest sensor readings from the hardware/simulator (Requires Authentication)."""
    return sensor_service.get_telemetry()

@router.get('/weather', summary="Get agronomic weather forecast (Public)")
async def get_weather_data():
    """Returns the local agronomic weather forecast and spray suitability window."""
    return sensor_service.get_weather()
