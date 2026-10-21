import os
from typing import Dict, Any, List, Optional
try:
    from app.config import Config
except ImportError:
    from config import Config

from .base import BaseRepository
from .memory_repository import MemoryRepository
from .supabase_service import SupabaseRepository

class UnifiedDatabaseService(BaseRepository):
    """Unified database dispatcher providing automatic Supabase integration with memory fallback."""

    def __init__(self):
        self.memory_repo = MemoryRepository()
        self.supabase_repo = None
        self.active_mode = "in_memory_repository"
        self._init_repository()

    def _init_repository(self):
        url = Config.SUPABASE_URL
        key = Config.SUPABASE_KEY
        enabled = Config.SUPABASE_ENABLED

        if enabled and url and key and "your-project" not in url:
            try:
                repo = SupabaseRepository(url, key)
                if repo.connected:
                    self.supabase_repo = repo
                    self.active_mode = "supabase_postgresql"
                    print(f"[DATABASE SERVICE] Active Database: Supabase PostgreSQL ({url[:25]}...)")
                    return
                else:
                    print(f"[DATABASE WARNING] Supabase connection failed. Falling back to in-memory repository.")
            except Exception as e:
                print(f"[DATABASE WARNING] Error initializing Supabase repository: {e}")

        self.active_mode = "in_memory_repository"
        print("[DATABASE SERVICE] Active Database: Local In-Memory Development Repository")

    @property
    def current(self) -> BaseRepository:
        if self.active_mode == "supabase_postgresql" and self.supabase_repo and self.supabase_repo.connected:
            return self.supabase_repo
        return self.memory_repo

    def get_status(self) -> Dict[str, Any]:
        status_dict = self.current.get_status()
        status_dict["mode"] = self.active_mode
        status_dict["credentials_configured"] = bool(self.active_mode == "supabase_postgresql" and self.supabase_repo and self.supabase_repo.connected)
        status_dict["active_engine"] = "Supabase PostgreSQL" if self.active_mode == "supabase_postgresql" else "In-Memory High-Fidelity Repository"
        return status_dict

    def save_farmer(self, data: Dict[str, Any], farmer_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.save_farmer(data, farmer_id=farmer_id)

    def get_farmer(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        return self.current.get_farmer(farmer_id)

    def get_farmer_by_auth_id(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        return self.current.get_farmer_by_auth_id(auth_user_id)

    def get_or_create_farmer_for_auth(self, auth_user_id: str, phone: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        return self.current.get_or_create_farmer_for_auth(auth_user_id, phone=phone, email=email)

    def save_farm(self, data: Dict[str, Any], farm_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.save_farm(data, farm_id=farm_id)

    def get_farm(self, farm_id: str) -> Optional[Dict[str, Any]]:
        return self.current.get_farm(farm_id)

    def get_farms(self, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.current.get_farms(farmer_id=farmer_id)

    def register_device(self, data: Dict[str, Any], device_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.register_device(data, device_id=device_id)

    def get_devices(self, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.current.get_devices(farm_id=farm_id)

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.current.get_device(device_id=device_id)

    def get_device_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        return self.current.get_device_by_api_key(api_key=api_key)

    def save_sensor_reading(self, data: Dict[str, Any], reading_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.save_sensor_reading(data, reading_id=reading_id)

    def get_recent_sensor_readings(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self.current.get_recent_sensor_readings(farm_id=farm_id, limit=limit)

    def save_farm_health(self, data: Dict[str, Any], health_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.save_farm_health(data, health_id=health_id)

    def get_farm_health_history(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self.current.get_farm_health_history(farm_id=farm_id, limit=limit)

    def save_advisory(self, data: Dict[str, Any], advisory_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.save_advisory(data, advisory_id=advisory_id)

    def get_recent_advisories(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self.current.get_recent_advisories(farm_id=farm_id, limit=limit)

    def create_alert(self, data: Dict[str, Any], alert_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.create_alert(data, alert_id=alert_id)

    def get_recent_alerts(self, farm_id: Optional[str] = None, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self.current.get_recent_alerts(farm_id=farm_id, status=status, limit=limit)

    def record_pump_event(self, data: Dict[str, Any], event_id: Optional[str] = None) -> Dict[str, Any]:
        return self.current.record_pump_event(data, event_id=event_id)

    def get_pump_events(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self.current.get_pump_events(farm_id=farm_id, limit=limit)

db_service = UnifiedDatabaseService()
firestore_service = db_service

__all__ = ['db_service', 'firestore_service', 'UnifiedDatabaseService']
