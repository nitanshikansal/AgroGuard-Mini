-- ==============================================================================
-- AgroGuard PostgreSQL Database Schema for Supabase with Authentication
-- ==============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. FARMERS TABLE (Mapped to Supabase Auth UID)
CREATE TABLE IF NOT EXISTS farmers (
    id VARCHAR(64) PRIMARY KEY,
    farmer_id VARCHAR(64) UNIQUE NOT NULL,
    auth_user_id VARCHAR(64) UNIQUE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(255) DEFAULT '',
    preferred_language VARCHAR(32) DEFAULT 'en',
    region VARCHAR(255) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. FARMS TABLE
CREATE TABLE IF NOT EXISTS farms (
    id VARCHAR(64) PRIMARY KEY,
    farm_id VARCHAR(64) UNIQUE NOT NULL,
    farmer_id VARCHAR(64) NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) DEFAULT 'Default Location',
    crop_type VARCHAR(64) DEFAULT 'Wheat',
    soil_type VARCHAR(64) DEFAULT 'Loamy',
    area_acres NUMERIC(8, 2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. DEVICES TABLE
CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,
    farm_id VARCHAR(64) NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    device_type VARCHAR(64) DEFAULT 'Arduino UNO R4 WiFi',
    device_name VARCHAR(255) DEFAULT 'AgroGuard Controller',
    status VARCHAR(32) DEFAULT 'active',
    device_api_key VARCHAR(128) UNIQUE,
    ip_address VARCHAR(45) DEFAULT '',
    mac_address VARCHAR(32) DEFAULT '',
    firmware_version VARCHAR(32) DEFAULT '1.0.0',
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. SENSOR READINGS TABLE
CREATE TABLE IF NOT EXISTS sensor_readings (
    id VARCHAR(64) PRIMARY KEY,
    reading_id VARCHAR(64) UNIQUE NOT NULL,
    farm_id VARCHAR(64) NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    device_id VARCHAR(64) DEFAULT '',
    soil_moisture NUMERIC(5, 2) NOT NULL,
    temperature NUMERIC(5, 2) NOT NULL,
    humidity NUMERIC(5, 2) NOT NULL,
    rain_status VARCHAR(32) NOT NULL,
    water_level NUMERIC(5, 2) NOT NULL,
    light_lux NUMERIC(8, 2) DEFAULT 0.0,
    crop_type VARCHAR(64) DEFAULT 'Wheat',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. FARM HEALTH (AFHI) TABLE
CREATE TABLE IF NOT EXISTS farm_health (
    id VARCHAR(64) PRIMARY KEY,
    health_id VARCHAR(64) UNIQUE NOT NULL,
    farm_id VARCHAR(64) NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    afhi_score NUMERIC(5, 2) NOT NULL,
    health_status VARCHAR(64) NOT NULL,
    breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 6. ADVISORIES (CAII + SPAE) TABLE
CREATE TABLE IF NOT EXISTS advisories (
    id VARCHAR(64) PRIMARY KEY,
    advisory_id VARCHAR(64) UNIQUE NOT NULL,
    farm_id VARCHAR(64) NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    type VARCHAR(64) DEFAULT 'consolidated',
    message TEXT DEFAULT '',
    recommendation TEXT DEFAULT '',
    irrigation JSONB NOT NULL DEFAULT '{}'::jsonb,
    pesticide JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 7. ALERTS TABLE
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(64) PRIMARY KEY,
    alert_id VARCHAR(64) UNIQUE NOT NULL,
    farm_id VARCHAR(64) NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    device_id VARCHAR(64) DEFAULT '',
    alert_type VARCHAR(64) DEFAULT 'info',
    severity VARCHAR(64) DEFAULT 'info',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(64) DEFAULT 'general',
    status VARCHAR(32) DEFAULT 'unread',
    acknowledged BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 8. PUMP ACTUATOR EVENTS TABLE
CREATE TABLE IF NOT EXISTS pump_events (
    id VARCHAR(64) PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    farm_id VARCHAR(64) NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    device_id VARCHAR(64) DEFAULT '',
    action VARCHAR(16) NOT NULL,
    state VARCHAR(32) NOT NULL,
    triggered_by VARCHAR(64) DEFAULT 'dashboard',
    reason TEXT DEFAULT '',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_farmers_phone ON farmers(phone);
CREATE INDEX IF NOT EXISTS idx_farmers_auth_user_id ON farmers(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_farms_farmer_id ON farms(farmer_id);
CREATE INDEX IF NOT EXISTS idx_devices_farm_id ON devices(farm_id);
CREATE INDEX IF NOT EXISTS idx_devices_api_key ON devices(device_api_key);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_farm_id ON sensor_readings(farm_id);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_device_id ON sensor_readings(device_id);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_farm_health_farm_id ON farm_health(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_health_timestamp ON farm_health(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_advisories_farm_id ON advisories(farm_id);
CREATE INDEX IF NOT EXISTS idx_advisories_timestamp ON advisories(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_farm_id ON alerts(farm_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_pump_events_farm_id ON pump_events(farm_id);
CREATE INDEX IF NOT EXISTS idx_pump_events_timestamp ON pump_events(timestamp DESC);

-- RLS
ALTER TABLE farmers ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE advisories ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pump_events ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN (
        'farmers', 'farms', 'devices', 'sensor_readings', 'farm_health', 'advisories', 'alerts', 'pump_events'
    ) LOOP
        EXECUTE format('DROP POLICY IF EXISTS service_role_all_%I ON %I', tbl, tbl);
        EXECUTE format('CREATE POLICY service_role_all_%I ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)', tbl, tbl);
    END LOOP;
END $$;
