from datetime import datetime, timezone
from .sensor_service import sensor_service

class PumpService:
    """
    Manages irrigation pump state, manual actuator triggers,
    and automatic cutoff logic.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PumpService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.is_active = False
        self.mode = "manual"  # "manual" | "auto"
        self.last_changed = datetime.now(timezone.utc).isoformat()

    def get_status(self) -> dict:
        return {
            "active": self.is_active,
            "status": "running" if self.is_active else "stopped",
            "mode": self.mode,
            "last_changed": self.last_changed
        }

    def set_pump_state(self, active: bool, mode: str = None) -> dict:
        """
        Activates or deactivates the irrigation pump actuator.
        """
        self.is_active = bool(active)
        if mode:
            self.mode = mode
        self.last_changed = datetime.now(timezone.utc).isoformat()

        # Trigger an immediate simulation tick with the new pump state
        sensor_service.update_simulation_tick(is_pump_active=self.is_active)

        return {
            "success": True,
            "active": self.is_active,
            "status": "running" if self.is_active else "stopped",
            "message": f"Irrigation pump {'started' if self.is_active else 'stopped'} successfully."
        }

# Global singleton
pump_service = PumpService()
