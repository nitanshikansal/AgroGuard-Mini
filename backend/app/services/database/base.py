from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseRepository(ABC):
    """Abstract base interface defining all database repository operations."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def save_farmer(self, data: Dict[str, Any], farmer_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_farmer(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_farmer_by_auth_id(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_or_create_farmer_for_auth(self, auth_user_id: str, phone: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def save_farm(self, data: Dict[str, Any], farm_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_farm(self, farm_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_farms(self, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def register_device(self, data: Dict[str, Any], device_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_devices(self, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_device_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_sensor_reading(self, data: Dict[str, Any], reading_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_recent_sensor_readings(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_farm_health(self, data: Dict[str, Any], health_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_farm_health_history(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_advisory(self, data: Dict[str, Any], advisory_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_recent_advisories(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_alert(self, data: Dict[str, Any], alert_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_recent_alerts(self, farm_id: Optional[str] = None, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def record_pump_event(self, data: Dict[str, Any], event_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_pump_events(self, farm_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        pass
