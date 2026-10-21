import os
from typing import List, Optional

class Config:
    """Base application configuration for FastAPI backend."""
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'REPLACE_WITH_A_UNIQUE_RANDOM_SECRET')
    DEBUG: bool = os.environ.get('FLASK_DEBUG', os.environ.get('DEBUG', 'False')).lower() in ('true', '1', 't')
    PORT: int = int(os.environ.get('PORT', 5000))
    HOST: str = os.environ.get('HOST', '0.0.0.0')

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "*"
    ]

    # Baseline Simulated Sensor Defaults
    DEFAULT_SOIL_MOISTURE: float = 45.0
    DEFAULT_TEMPERATURE: float = 27.4
    DEFAULT_HUMIDITY: float = 62.0
    DEFAULT_RAIN_STATUS: str = "No Rain"
    DEFAULT_WATER_LEVEL: float = 78.0

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY: Optional[str] = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_KEY')
    SUPABASE_ANON_KEY: Optional[str] = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_JWT_SECRET: Optional[str] = os.environ.get('SUPABASE_JWT_SECRET')
    SUPABASE_ENABLED: bool = os.environ.get('SUPABASE_ENABLED', 'true').lower() in ('true', '1', 't')
    AUTH_ENABLED: bool = os.environ.get('AUTH_ENABLED', 'true').lower() in ('true', '1', 't')

    # Firebase / Firestore Configuration (Optional Reference)
    FIREBASE_CREDENTIALS_PATH: Optional[str] = os.environ.get('FIREBASE_CREDENTIALS_PATH') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    FIREBASE_PROJECT_ID: str = os.environ.get('FIREBASE_PROJECT_ID', 'agroguard-smart-agriculture')
    FIRESTORE_EMULATOR_HOST: Optional[str] = os.environ.get('FIRESTORE_EMULATOR_HOST')

settings = Config()
Config = Config  # Compatibility alias
