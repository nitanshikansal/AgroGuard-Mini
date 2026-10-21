from typing import Optional, Union, Dict, Any, List
from pydantic import BaseModel, Field

class PumpControlRequest(BaseModel):
    active: Optional[Any] = None
    state: Optional[Any] = None
    source: Optional[str] = "dashboard_manual"
    triggered_by: Optional[str] = None
    farm_id: Optional[str] = "default_farm"
    farmId: Optional[str] = None
    device_id: Optional[str] = "arduino_r4_pump"
    deviceId: Optional[str] = None
    reason: Optional[str] = ""

    class Config:
        extra = "allow"

class FarmerCreateSchema(BaseModel):
    farmer_id: Optional[str] = None
    farmerId: Optional[str] = None
    name: str
    phone: str
    email: Optional[str] = ""
    preferred_language: Optional[str] = "en"
    preferredLanguage: Optional[str] = None
    region: Optional[str] = ""

    class Config:
        extra = "allow"

class FarmCreateSchema(BaseModel):
    farm_id: Optional[str] = None
    farmId: Optional[str] = None
    farmer_id: Optional[str] = None
    farmerId: Optional[str] = None
    name: Optional[str] = None
    farm_name: Optional[str] = None
    farmName: Optional[str] = None
    crop_type: Optional[str] = "Wheat"
    crop: Optional[str] = None
    soil_type: Optional[str] = "Loamy"
    soilType: Optional[str] = None
    area_acres: Optional[float] = 1.0
    area: Optional[float] = None
    location: Optional[Any] = "Default Location"

    class Config:
        extra = "allow"

class DeviceRegisterSchema(BaseModel):
    device_id: Optional[str] = None
    deviceId: Optional[str] = None
    farm_id: Optional[str] = "default_farm"
    farmId: Optional[str] = None
    device_type: Optional[str] = "Arduino UNO R4 WiFi"
    deviceType: Optional[str] = None
    device_name: Optional[str] = "AgroGuard Controller"
    deviceName: Optional[str] = None
    status: Optional[str] = "active"
    device_api_key: Optional[str] = None
    deviceApiKey: Optional[str] = None
    ip_address: Optional[str] = ""
    ipAddress: Optional[str] = None
    mac_address: Optional[str] = ""
    macAddress: Optional[str] = None
    firmware_version: Optional[str] = "1.0.0"

    class Config:
        extra = "allow"

class SensorReadingSchema(BaseModel):
    reading_id: Optional[str] = None
    readingId: Optional[str] = None
    farm_id: Optional[str] = "default_farm"
    farmId: Optional[str] = None
    device_id: Optional[str] = "arduino_r4_default"
    deviceId: Optional[str] = None
    soil_moisture: Optional[float] = None
    soilMoisture: Optional[float] = None
    temperature: Optional[float] = 25.0
    humidity: Optional[float] = 60.0
    rain_status: Optional[Any] = "No Rain"
    rainStatus: Optional[Any] = None
    water_level: Optional[float] = None
    waterLevel: Optional[float] = None
    light_lux: Optional[float] = 0.0
    crop_type: Optional[str] = "Wheat"

    class Config:
        extra = "allow"

class AlertCreateSchema(BaseModel):
    alert_id: Optional[str] = None
    alertId: Optional[str] = None
    farm_id: Optional[str] = "default_farm"
    farmId: Optional[str] = None
    device_id: Optional[str] = "default_device"
    deviceId: Optional[str] = None
    alert_type: Optional[str] = "info"
    alertType: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = "Farm Alert"
    message: Optional[str] = ""
    category: Optional[str] = "general"
    status: Optional[str] = "unread"

    class Config:
        extra = "allow"
