from .sensor_routes import router as sensor_router
from .dashboard_routes import router as dashboard_router
from .control_routes import router as control_router
from .database_routes import router as database_router

__all__ = ['sensor_router', 'dashboard_router', 'control_router', 'database_router']
