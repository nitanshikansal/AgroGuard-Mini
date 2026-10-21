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

class MemoryRepository(BaseRepository):
    """High-fidelity in-memory repository store providing local development fallback."""

    def __init__(self):
        self.mode = "in_memory_repository"
        self.error_message = None
        self._memory_store = {
            "farmers": {},
            "farms": {},
            "devices": {},
            "sensor_readings": {},
            "farm_health": {},
            "advisories": {},
            "alerts": {},
            "pump_events": {}
        }

    def get_status(self) -> Dict[str, Any]:
        counts = {col: len(docs) for col, docs in self._memory_store.items()}
        return {
            "status": "healthy",
            "initialized": True,
            "mode": self.mode,
            "credentials_configured": False,
            "supabase_configured": False,
            "supabase_connected": False,
            "fallback_active": True,
            "collections_tracked": list(self._memory_store.keys()),
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
        self._memory_store["farmers"][doc_id] = clean
        return clean

    def get_farmer(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        return self._memory_store["farmers"].get(farmer_id)

    def get_farmer_by_auth_id(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        for farmer in self._memory_store["farmers"].values():
            if farmer.get("auth_user_id") == auth_user_id or farmer.get("authUserId") == auth_user_id:
                return farmer
            if farmer.get("farmer_id") == auth_user_id:
                return farmer
        return None

    def get_or_create_farmer_for_auth(self, auth_user_id: str, phone: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        existing = self.get_farmer_by_auth_id(auth_user_id)
        if existing:
            return existing

        # Stable unique ID mapping: if auth_user_id already represents a farmer, preserve it
        doc_id = auth_user_id if "farmer" in auth_user_id.lower() else f"farmer_{auth_user_id}"

        # Check if already exists by farmer_id
        if doc_id in self._memory_store["farmers"]:
            farmer = self._memory_store["farmers"][doc_id]
            farmer["auth_user_id"] = auth_user_id
            farmer["authUserId"] = auth_user_id
            return farmer

        new_farmer = {
            "id": doc_id,
            "farmer_id": doc_id,
            "farmerId": doc_id,
            "auth_user_id": auth_user_id,
            "authUserId": auth_user_id,
            "name": f"Farmer {auth_user_id}",
            "phone": phone or "+919876543210",
            "email": email or "",
            "preferred_language": "en",
            "region": "Default Region",
            "created_at": current_timestamp(),
            "updated_at": current_timestamp()
        }
        self._memory_store["farmers"][doc_id] = new_farmer
        return new_farmer

    def save_farm(self, data: Dict[str, Any], farm_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farm(data)
        doc_id = farm_id or clean.get("farm_id") or generate_id("farm_")
        clean["id"] = doc_id
        clean["farm_id"] = doc_id
        clean["farmId"] = doc_id
        self._memory_store["farms"][doc_id] = clean
        return clean

    def get_farm(self, farm_id: str) -> Optional[Dict[str, Any]]:
        return self._memory_store["farms"].get(farm_id)

    def get_farms(self, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["farms"].values())
        if farmer_id:
            docs = [d for d in docs if d.get("farmer_id") == farmer_id or d.get("farmerId") == farmer_id]
        return docs

    def register_device(self, data: Dict[str, Any], device_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_device(data)
        doc_id = device_id or clean.get("device_id") or generate_id("device_")
        clean["id"] = doc_id
        clean["device_id"] = doc_id
        clean["deviceId"] = doc_id
        # Enforce unique device_api_key constraint in memory store
        dev_key = clean.get("device_api_key")
        if dev_key:
            stale_keys = [k for k, v in self._memory_store["devices"].items() if (v.get("device_api_key") == dev_key or v.get("deviceApiKey") == dev_key) and k != doc_id]
            for sk in stale_keys:
                del self._memory_store["devices"][sk]
        self._memory_store["devices"][doc_id] = clean
        return clean

    def get_devices(self, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["devices"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        return docs

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        for d in self._memory_store["devices"].values():
            if d.get("device_id") == device_id or d.get("deviceId") == device_id or d.get("id") == device_id:
                return d
        return None

    def get_device_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not api_key:
            return None
        for d in self._memory_store["devices"].values():
            dev_key = d.get("device_api_key") or d.get("deviceApiKey")
            if dev_key and dev_key == api_key:
                return d
        return None

    def save_sensor_reading(self, data: Dict[str, Any], reading_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_sensor_reading(data)
        doc_id = reading_id or clean.get("reading_id") or generate_id("read_")
        clean["id"] = doc_id
        clean["reading_id"] = doc_id
        clean["readingId"] = doc_id
        self._memory_store["sensor_readings"][doc_id] = clean
        return clean

    def get_recent_sensor_readings(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["sensor_readings"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    def save_farm_health(self, data: Dict[str, Any], health_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_farm_health(data)
        doc_id = health_id or clean.get("health_id") or generate_id("afhi_")
        clean["id"] = doc_id
        clean["health_id"] = doc_id
        clean["healthId"] = doc_id
        self._memory_store["farm_health"][doc_id] = clean
        return clean

    def get_farm_health_history(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["farm_health"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    def save_advisory(self, data: Dict[str, Any], advisory_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_advisory(data)
        doc_id = advisory_id or clean.get("advisory_id") or generate_id("adv_")
        clean["id"] = doc_id
        clean["advisory_id"] = doc_id
        clean["advisoryId"] = doc_id
        self._memory_store["advisories"][doc_id] = clean
        return clean

    def get_recent_advisories(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["advisories"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    def create_alert(self, data: Dict[str, Any], alert_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_alert(data)
        doc_id = alert_id or clean.get("alert_id") or generate_id("alert_")
        clean["id"] = doc_id
        clean["alert_id"] = doc_id
        clean["alertId"] = doc_id
        self._memory_store["alerts"][doc_id] = clean
        return clean

    def get_recent_alerts(self, farm_id: Optional[str] = None, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["alerts"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        if status:
            docs = [d for d in docs if d.get("status") == status]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]

    def record_pump_event(self, data: Dict[str, Any], event_id: Optional[str] = None) -> Dict[str, Any]:
        clean = validate_pump_event(data)
        doc_id = event_id or clean.get("event_id") or generate_id("event_")
        clean["id"] = doc_id
        clean["event_id"] = doc_id
        clean["eventId"] = doc_id
        self._memory_store["pump_events"][doc_id] = clean
        return clean

    def get_pump_events(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        docs = list(self._memory_store["pump_events"].values())
        if farm_id:
            docs = [d for d in docs if d.get("farm_id") == farm_id or d.get("farmId") == farm_id]
        docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return docs[:limit]
