import os
from typing import Dict, Any, List, Optional
try:
    from app.config import Config
except ImportError:
    from config import Config

from .base import BaseRepository
from .models import (
    generate_id,
    current_timestamp,
    validate_farmer,
    validate_farm,
    validate_device,
    validate_sensor_reading,
    validate_farm_health,
    validate_advisory,
    validate_alert,
    validate_pump_event
)

class SupabaseRepository(BaseRepository):
    """Production database repository using Supabase PostgreSQL client."""

    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.mode = "supabase_postgresql"
        self.client = None
        self.connected = False
        self.error_message = None
        self._init_client()

    def _init_client(self):
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(self.url, self.key)
            self.connected = True
            print(f"[SUPABASE] Successfully initialized Supabase client at: {self.url[:24]}...")
        except Exception as e:
            self.connected = False
            self.error_message = str(e)
            print(f"[SUPABASE WARNING] Failed to connect to Supabase: {e}")

    def get_status(self) -> Dict[str, Any]:
        collections_tracked = [
            "farmers", "farms", "devices", "sensor_readings",
            "farm_health", "advisories", "alerts", "pump_events"
        ]
        counts = {}
        if self.connected and self.client:
            for tbl in collections_tracked:
                try:
                    res = self.client.table(tbl).select("id", count="exact").limit(1).execute()
                    counts[tbl] = res.count if hasattr(res, 'count') and res.count is not None else 0
                except Exception:
                    counts[tbl] = 0
        return {
            "status": "healthy" if self.connected else "degraded",
            "initialized": self.connected,
            "mode": self.mode,
            "credentials_configured": True,
            "supabase_configured": True,
            "supabase_connected": self.connected,
            "fallback_active": not self.connected,
            "collections_tracked": collections_tracked,
            "collections": counts,
            "record_counts": counts,
            "error": self.error_message
        }

    def save_farmer(self, data: Dict[str, Any], farmer_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farmer(data)
        doc_id = farmer_id or clean.get("farmer_id") or generate_id("farmer_")
        clean["id"] = doc_id
        clean["farmer_id"] = doc_id
        clean["farmerId"] = doc_id

        pg_row = {
            "id": doc_id,
            "farmer_id": doc_id,
            "name": clean["name"],
            "phone": clean["phone"],
            "email": clean.get("email", ""),
            "preferred_language": clean.get("preferred_language", "en"),
            "region": clean.get("region", ""),
            "created_at": clean.get("created_at"),
            "updated_at": clean.get("updated_at")
        }
        if clean.get("auth_user_id"):
            pg_row["auth_user_id"] = clean.get("auth_user_id")

        if self.client:
            self.client.table("farmers").upsert(pg_row).execute()
        return clean

    def get_farmer(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        res = self.client.table("farmers").select("*").eq("farmer_id", farmer_id).execute()
        if res.data:
            row = res.data[0]
            row["farmerId"] = row.get("farmer_id")
            row["authUserId"] = row.get("auth_user_id")
            return row
        return None

    def get_farmer_by_auth_id(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        res = self.client.table("farmers").select("*").eq("auth_user_id", auth_user_id).execute()
        if res.data:
            row = res.data[0]
            row["farmerId"] = row.get("farmer_id")
            row["authUserId"] = row.get("auth_user_id")
            return row
        return None

    def get_or_create_farmer_for_auth(self, auth_user_id: str, phone: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        existing = self.get_farmer_by_auth_id(auth_user_id)
        if existing:
            return existing
        # Stable unique ID mapping
        doc_id = auth_user_id if "farmer" in auth_user_id.lower() else f"farmer_{auth_user_id}"
        new_farmer = {
            "id": doc_id,
            "farmer_id": doc_id,
            "auth_user_id": auth_user_id,
            "name": f"Farmer {auth_user_id}",
            "phone": phone or "+919876543210",
            "email": email or "",
            "preferred_language": "en",
            "region": "Default Region",
            "created_at": current_timestamp(),
            "updated_at": current_timestamp()
        }
        return self.save_farmer(new_farmer, farmer_id=doc_id)

    def save_farm(self, data: Dict[str, Any], farm_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farm(data)
        doc_id = farm_id or clean.get("farm_id") or generate_id("farm_")
        clean["id"] = doc_id
        clean["farm_id"] = doc_id
        clean["farmId"] = doc_id

        pg_row = {
            "id": doc_id,
            "farm_id": doc_id,
            "farmer_id": clean["farmer_id"],
            "name": clean["name"],
            "location": clean.get("location", "Default Location"),
            "crop_type": clean.get("crop_type", "Wheat"),
            "soil_type": clean.get("soil_type", "Loamy"),
            "area_acres": clean.get("area_acres", 1.0),
            "created_at": clean.get("created_at"),
            "updated_at": clean.get("updated_at")
        }
        if self.client:
            self.client.table("farms").upsert(pg_row).execute()
        return clean

    def get_farm(self, farm_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        res = self.client.table("farms").select("*").eq("farm_id", farm_id).execute()
        if res.data:
            row = res.data[0]
            row["farmId"] = row.get("farm_id")
            row["farmerId"] = row.get("farmer_id")
            return row
        return None

    def get_farms(self, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("farms").select("*")
        if farmer_id:
            query = query.eq("farmer_id", farmer_id)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["farmId"] = d.get("farm_id")
            d["farmerId"] = d.get("farmer_id")
        return data

    def register_device(self, data: Dict[str, Any], device_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_device(data)
        doc_id = device_id or clean.get("device_id") or generate_id("device_")
        clean["id"] = doc_id
        clean["device_id"] = doc_id
        clean["deviceId"] = doc_id

        pg_row = {
            "id": doc_id,
            "device_id": doc_id,
            "farm_id": clean["farm_id"],
            "device_type": clean.get("device_type", "Arduino UNO R4 WiFi"),
            "device_name": clean.get("device_name", "AgroGuard Controller"),
            "status": clean.get("status", "active"),
            "device_api_key": clean.get("device_api_key", ""),
            "ip_address": clean.get("ip_address", ""),
            "mac_address": clean.get("mac_address", ""),
            "firmware_version": clean.get("firmware_version", "1.0.0"),
            "last_seen": clean.get("last_seen"),
            "created_at": clean.get("created_at")
        }
        if self.client:
            self.client.table("devices").upsert(pg_row).execute()
        return clean

    def get_devices(self, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("devices").select("*")
        if farm_id:
            query = query.eq("farm_id", farm_id)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["deviceId"] = d.get("device_id")
            d["farmId"] = d.get("farm_id")
            d["deviceApiKey"] = d.get("device_api_key")
        return data

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        if not self.client or not device_id:
            return None
        try:
            res = self.client.table("devices").select("*").eq("device_id", device_id).execute()
            data = res.data or []
            if data:
                d = data[0]
                d["deviceId"] = d.get("device_id")
                d["farmId"] = d.get("farm_id")
                d["deviceApiKey"] = d.get("device_api_key")
                return d
        except Exception:
            pass
        return None

    def get_device_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not self.client or not api_key:
            return None
        try:
            res = self.client.table("devices").select("*").eq("device_api_key", api_key).execute()
            data = res.data or []
            if data:
                d = data[0]
                d["deviceId"] = d.get("device_id")
                d["farmId"] = d.get("farm_id")
                d["deviceApiKey"] = d.get("device_api_key")
                return d
        except Exception:
            pass
        return None

    def save_sensor_reading(self, data: Dict[str, Any], reading_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_sensor_reading(data)
        doc_id = reading_id or clean.get("reading_id") or generate_id("read_")
        clean["id"] = doc_id
        clean["reading_id"] = doc_id
        clean["readingId"] = doc_id

        pg_row = {
            "id": doc_id,
            "reading_id": doc_id,
            "farm_id": clean["farm_id"],
            "device_id": clean.get("device_id", ""),
            "soil_moisture": clean["soil_moisture"],
            "temperature": clean["temperature"],
            "humidity": clean["humidity"],
            "rain_status": clean["rain_status"],
            "water_level": clean["water_level"],
            "light_lux": clean.get("light_lux", 0.0),
            "crop_type": clean.get("crop_type", "Wheat"),
            "timestamp": clean.get("timestamp")
        }
        if self.client:
            self.client.table("sensor_readings").insert(pg_row).execute()
        return clean

    def get_recent_sensor_readings(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("sensor_readings").select("*")
        if farm_id:
            query = query.eq("farm_id", farm_id)
        query = query.order("timestamp", desc=True).limit(limit)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["readingId"] = d.get("reading_id")
            d["farmId"] = d.get("farm_id")
            d["deviceId"] = d.get("device_id")
            d["soilMoisture"] = d.get("soil_moisture")
            d["waterLevel"] = d.get("water_level")
            d["rainStatus"] = d.get("rain_status")
            d["lightLux"] = d.get("light_lux")
        return data

    def save_farm_health(self, data: Dict[str, Any], health_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farm_health(data)
        doc_id = health_id or clean.get("health_id") or generate_id("afhi_")
        clean["id"] = doc_id
        clean["health_id"] = doc_id
        clean["healthId"] = doc_id

        pg_row = {
            "id": doc_id,
            "health_id": doc_id,
            "farm_id": clean["farm_id"],
            "afhi_score": clean["afhi_score"],
            "health_status": clean["health_status"],
            "breakdown": clean.get("breakdown", {}),
            "timestamp": clean.get("timestamp")
        }
        if self.client:
            self.client.table("farm_health").insert(pg_row).execute()
        return clean

    def get_farm_health_history(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("farm_health").select("*")
        if farm_id:
            query = query.eq("farm_id", farm_id)
        query = query.order("timestamp", desc=True).limit(limit)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["healthId"] = d.get("health_id")
            d["farmId"] = d.get("farm_id")
            d["afhiScore"] = d.get("afhi_score")
            d["score"] = d.get("afhi_score")
            d["status"] = d.get("health_status")
            d["components"] = d.get("breakdown", {})
        return data

    def save_advisory(self, data: Dict[str, Any], advisory_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_advisory(data)
        doc_id = advisory_id or clean.get("advisory_id") or generate_id("adv_")
        clean["id"] = doc_id
        clean["advisory_id"] = doc_id
        clean["advisoryId"] = doc_id

        pg_row = {
            "id": doc_id,
            "advisory_id": doc_id,
            "farm_id": clean["farm_id"],
            "type": clean.get("type", "consolidated"),
            "message": clean.get("message", ""),
            "recommendation": clean.get("recommendation", ""),
            "irrigation": clean.get("irrigation", {}),
            "pesticide": clean.get("pesticide", {}),
            "timestamp": clean.get("timestamp")
        }
        if self.client:
            self.client.table("advisories").insert(pg_row).execute()
        return clean

    def get_recent_advisories(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("advisories").select("*")
        if farm_id:
            query = query.eq("farm_id", farm_id)
        query = query.order("timestamp", desc=True).limit(limit)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["advisoryId"] = d.get("advisory_id")
            d["farmId"] = d.get("farm_id")
            d["caii"] = d.get("irrigation", {})
            d["spae"] = d.get("pesticide", {})
        return data

    def create_alert(self, data: Dict[str, Any], alert_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_alert(data)
        doc_id = alert_id or clean.get("alert_id") or generate_id("alert_")
        clean["id"] = doc_id
        clean["alert_id"] = doc_id
        clean["alertId"] = doc_id

        pg_row = {
            "id": doc_id,
            "alert_id": doc_id,
            "farm_id": clean["farm_id"],
            "device_id": clean.get("device_id", ""),
            "alert_type": clean.get("alert_type", "info"),
            "severity": clean.get("severity", "info"),
            "title": clean["title"],
            "message": clean["message"],
            "category": clean.get("category", "general"),
            "status": clean.get("status", "unread"),
            "acknowledged": clean.get("acknowledged", False),
            "timestamp": clean.get("timestamp")
        }
        if self.client:
            self.client.table("alerts").insert(pg_row).execute()
        return clean

    def get_recent_alerts(self, farm_id: Optional[str] = None, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("alerts").select("*")
        if farm_id:
            query = query.eq("farm_id", farm_id)
        if status:
            query = query.eq("status", status)
        query = query.order("timestamp", desc=True).limit(limit)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["alertId"] = d.get("alert_id")
            d["farmId"] = d.get("farm_id")
            d["deviceId"] = d.get("device_id")
            d["alertType"] = d.get("alert_type")
        return data

    def record_pump_event(self, data: Dict[str, Any], event_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_pump_event(data)
        doc_id = event_id or clean.get("event_id") or generate_id("event_")
        clean["id"] = doc_id
        clean["event_id"] = doc_id
        clean["eventId"] = doc_id

        pg_row = {
            "id": doc_id,
            "event_id": doc_id,
            "farm_id": clean["farm_id"],
            "device_id": clean.get("device_id", ""),
            "action": clean["action"],
            "state": clean["state"],
            "triggered_by": clean.get("triggered_by", "dashboard"),
            "reason": clean.get("reason", ""),
            "timestamp": clean.get("timestamp")
        }
        if self.client:
            self.client.table("pump_events").insert(pg_row).execute()
        return clean

    def get_pump_events(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        query = self.client.table("pump_events").select("*")
        if farm_id:
            query = query.eq("farm_id", farm_id)
        query = query.order("timestamp", desc=True).limit(limit)
        res = query.execute()
        data = res.data or []
        for d in data:
            d["eventId"] = d.get("event_id")
            d["farmId"] = d.get("farm_id")
            d["deviceId"] = d.get("device_id")
        return data
