import secrets
from typing import Optional
from fastapi import APIRouter, Request, Query, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.auth import (
    get_current_user,
    AuthenticatedUser,
    AuthenticatedDevice,
    get_device_or_farmer_auth,
    verify_farm_ownership,
    verify_device_ownership
)
from app.services.database import db_service
from app.services.database.models import ModelValidationError
from app.services.decision_engine import decision_engine

router = APIRouter(tags=["Database & Relational Foundation"])

# -----------------------------------------------------------------------------
# DATABASE HEALTH & STATUS (Public)
# -----------------------------------------------------------------------------
@router.get('/database/status', summary="Database health & status (Public)")
async def get_database_status():
    """Returns database connection status, active mode, and statistics (Public)."""
    info = db_service.get_status()
    return {
        "status": info.get("status", "healthy"),
        "service": "AgroGuard Database Service",
        "initialized": info.get("initialized", True),
        "mode": info.get("mode", "in_memory_repository"),
        "collections": info.get("record_counts", {}),
        **info
    }

# -----------------------------------------------------------------------------
# 1. FARMERS ENDPOINTS (Protected)
# -----------------------------------------------------------------------------
@router.get('/farmers/me', summary="Get authenticated farmer profile")
async def get_my_farmer_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns profile of the authenticated farmer."""
    farmer = db_service.get_farmer(current_user.farmer_id)
    if not farmer:
        farmer = db_service.get_or_create_farmer_for_auth(current_user.auth_user_id)
    return {"success": True, "data": farmer, **farmer}

@router.post('/farmers', status_code=status.HTTP_201_CREATED, summary="Create or update farmer profile")
async def create_farmer(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Creates or updates the authenticated farmer's profile."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    # Ensure farmer_id belongs to authenticated user
    data["auth_user_id"] = current_user.auth_user_id
    if not data.get("farmer_id") and not data.get("farmerId"):
        data["farmer_id"] = current_user.farmer_id
    elif (data.get("farmer_id") or data.get("farmerId")) != current_user.farmer_id:
        # Cross-farmer modification attempt
        raise HTTPException(status_code=403, detail="Forbidden: You cannot modify another farmer's profile.")

    try:
        farmer = db_service.save_farmer(data, farmer_id=current_user.farmer_id)
        return {"success": True, "data": farmer, "farmer": farmer, **farmer}
    except ModelValidationError as e:
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": str(e)})

@router.get('/farmers/{farmer_id}', summary="Get farmer profile by ID (Protected)")
async def get_farmer(farmer_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves farmer document by farmer_id. Only allowed for self."""
    farmer = db_service.get_farmer(farmer_id)
    if not farmer:
        return JSONResponse(status_code=404, content={"error": "Not Found", "message": f"Farmer '{farmer_id}' not found."})
    if farmer_id != current_user.farmer_id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot access another farmer's profile.")
    return {"success": True, "data": farmer, **farmer}

# -----------------------------------------------------------------------------
# 2. FARMS ENDPOINTS (Protected & Ownership Enforced)
# -----------------------------------------------------------------------------
@router.post('/farms', status_code=status.HTTP_201_CREATED, summary="Create farm plot (Protected)")
async def create_farm(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Creates a farm plot record linked to the authenticated farmer."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    # Enforce validation and ownership
    req_farmer_id = data.get("farmer_id") or data.get("farmerId")
    if not req_farmer_id:
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": "Field 'farmer_id' is required."})
    if req_farmer_id != current_user.farmer_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot create farm for another farmer.")
    data["farmer_id"] = current_user.farmer_id

    try:
        farm = db_service.save_farm(data)
        return {"success": True, "data": farm, "farm": farm, **farm}
    except ModelValidationError as e:
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": str(e)})

@router.get('/farms/{farm_id}', summary="Get farm plot by ID (Protected)")
async def get_farm(farm_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves farm metadata by farm_id. Enforces ownership."""
    farm = verify_farm_ownership(farm_id, current_user)
    return {"success": True, "data": farm, **farm}

@router.get('/farms', summary="List farm plots (Protected)")
async def get_farms(
    farmer_id: Optional[str] = Query(None),
    farmerId: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Lists farm plots belonging to authenticated farmer. Enforces ownership."""
    fid = farmer_id or farmerId
    if fid and fid != current_user.farmer_id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot view another farmer's farms.")
    farms = db_service.get_farms(farmer_id=current_user.farmer_id)
    return {"success": True, "count": len(farms), "farms": farms, "data": farms}

# -----------------------------------------------------------------------------
# 3. DEVICES ENDPOINTS (Protected & Ownership Enforced)
# -----------------------------------------------------------------------------
@router.post('/devices', status_code=status.HTTP_201_CREATED, summary="Register IoT controller device (Protected)")
async def register_device(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Registers an edge IoT controller node. Enforces farm and device ownership."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    farm_id = data.get("farm_id") or data.get("farmId")
    req_device_id = data.get("device_id") or data.get("deviceId")

    if req_device_id:
        existing_dev = db_service.get_device(req_device_id)
        if existing_dev:
            verify_device_ownership(req_device_id, current_user)
            if not (data.get("device_api_key") or data.get("deviceApiKey")):
                data["device_api_key"] = existing_dev.get("device_api_key") or existing_dev.get("deviceApiKey")

    if farm_id:
        verify_farm_ownership(farm_id, current_user)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        if not user_farms:
            raise HTTPException(status_code=400, detail="Must have at least one farm to register devices.")
        data["farm_id"] = user_farms[0]["farm_id"]

    # Provision device API key if not provided
    if not (data.get("device_api_key") or data.get("deviceApiKey")):
        data["device_api_key"] = f"agro_dev_{secrets.token_hex(16)}"
    if not data.get("status"):
        data["status"] = "active"

    try:
        device = db_service.register_device(data)
        return {"success": True, "data": device, "device": device, **device}
    except ModelValidationError as e:
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": str(e)})

@router.get('/devices', summary="List registered IoT devices (Protected)")
async def get_devices(
    farm_id: Optional[str] = Query(None),
    farmId: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Lists devices for authenticated farmer's farms."""
    fid = farm_id or farmId
    if fid:
        verify_farm_ownership(fid, current_user)
        devices = db_service.get_devices(farm_id=fid)
    else:
        # Return all devices across all farms owned by authenticated farmer
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        user_farm_ids = {f["farm_id"] for f in user_farms}
        all_devs = db_service.get_devices()
        devices = [d for d in all_devs if (d.get("farm_id") or d.get("farmId")) in user_farm_ids]
    return {"success": True, "count": len(devices), "devices": devices, "data": devices}

@router.get('/devices/{device_id}', summary="Get registered IoT device by ID (Protected)")
async def get_device(device_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieves IoT device by device_id. Enforces farm ownership."""
    device = verify_device_ownership(device_id, current_user)
    return {"success": True, "data": device, "device": device, **device}

# -----------------------------------------------------------------------------
# 4. SENSOR READINGS & DECISION PIPELINE (Protected & Ownership Enforced)
# -----------------------------------------------------------------------------
@router.post('/sensor/readings', status_code=status.HTTP_201_CREATED, summary="Ingest telemetry & evaluate decision engine (Protected)")
async def record_sensor_reading(
    request: Request,
    auth_identity = Depends(get_device_or_farmer_auth)
):
    """
    Ingests sensor reading, pipes it through AFHI/CAII/SPAE Decision Engine.
    Supports:
      1. Hardware Device Authentication via 'X-Device-API-Key'
      2. Farmer User Authentication via 'Authorization: Bearer <JWT>'
    Enforces device-to-farm isolation and farm ownership.
    """
    device_auth, farmer_auth = auth_identity

    try:
        data = await request.json()
    except Exception:
        data = {}

    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": "Sensor reading payload must be a JSON object."})

    if device_auth:
        registered_farm_id = device_auth.farm_id
        registered_device_id = device_auth.device_id

        # Unknown device check: if device_id is provided in payload and does not match authenticated device
        req_dev_id = data.get("device_id") or data.get("deviceId")
        if req_dev_id and str(req_dev_id).strip() != str(registered_device_id).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown device: Payload device_id '{req_dev_id}' does not match registered device '{registered_device_id}' for this API key."
            )
        data["device_id"] = registered_device_id

        # Cross-farm isolation: Device from Farm A cannot submit telemetry for Farm B
        req_farm_id = data.get("farm_id") or data.get("farmId")
        if req_farm_id and str(req_farm_id).strip() != str(registered_farm_id).strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Device registered to farm '{registered_farm_id}' cannot submit telemetry for farm '{req_farm_id}'."
            )
        data["farm_id"] = registered_farm_id

    elif farmer_auth:
        farm_id = data.get("farm_id") or data.get("farmId")
        if farm_id:
            verify_farm_ownership(farm_id, farmer_auth)
        else:
            user_farms = db_service.get_farms(farmer_id=farmer_auth.farmer_id)
            if not user_farms:
                raise HTTPException(status_code=400, detail="Cannot ingest sensor reading without an associated farm.")
            data["farm_id"] = user_farms[0]["farm_id"]

    try:
        reading = db_service.save_sensor_reading(data)

        # Pipe through AgroGuard Decision Engine
        telemetry_dict = {
            "soil_moisture": reading["soil_moisture"],
            "temperature": reading["temperature"],
            "humidity": reading["humidity"],
            "rain_status": reading["rain_status"],
            "water_level": reading["water_level"]
        }
        health_eval = decision_engine.evaluate_farm_health(telemetry_dict)
        rec_eval = decision_engine.evaluate_recommendations(telemetry_dict)

        health_record = db_service.save_farm_health({
            "farm_id": reading["farm_id"],
            "afhi_score": health_eval["score"],
            "health_status": health_eval["status"],
            "breakdown": health_eval.get("components", {}),
            "timestamp": reading["timestamp"]
        })

        advisory_record = db_service.save_advisory({
            "farm_id": reading["farm_id"],
            "type": "consolidated",
            "message": rec_eval.get("irrigation", ""),
            "recommendation": rec_eval.get("spae", {}).get("message", "") if isinstance(rec_eval.get("spae"), dict) else str(rec_eval.get("spae", "")),
            "irrigation": rec_eval.get("caii", {}),
            "pesticide": rec_eval.get("spae", {}),
            "timestamp": reading["timestamp"]
        })

        return {
            "success": True,
            "reading_id": reading.get("reading_id") or reading.get("id"),
            "farm_id": reading["farm_id"],
            "device_id": reading.get("device_id", ""),
            "AFHI": health_eval["score"],
            "health_status": health_eval["status"],
            "irrigation_recommendation": rec_eval.get("irrigation", ""),
            "pesticide_recommendation": rec_eval.get("spae", {}).get("message", "") if isinstance(rec_eval.get("spae"), dict) else str(rec_eval.get("spae", "")),
            "caii_recommendation": rec_eval.get("caii", {}),
            "spae_recommendation": rec_eval.get("spae", {}),
            # Backwards compatibility fields:
            "data": reading,
            "reading": reading,
            "processed_afhi": health_eval,
            "processed_advisory": rec_eval,
            "farm_health": health_record,
            "advisory": advisory_record
        }
    except ModelValidationError as e:
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": str(e)})

@router.get('/sensor/readings', summary="Query historical sensor readings (Protected)")
async def get_sensor_readings(
    farm_id: Optional[str] = Query(None),
    farmId: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves recent sensor readings history. Enforces farm ownership."""
    fid = farm_id or farmId
    if fid:
        verify_farm_ownership(fid, current_user)
        readings = db_service.get_recent_sensor_readings(farm_id=fid, limit=limit)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        readings = []
        for f in user_farms:
            readings.extend(db_service.get_recent_sensor_readings(farm_id=f["farm_id"], limit=limit))
        readings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        readings = readings[:limit]
    return {"success": True, "count": len(readings), "readings": readings, "data": readings}

# -----------------------------------------------------------------------------
# 5. FARM HEALTH (AFHI) HISTORY (Protected)
# -----------------------------------------------------------------------------
@router.get('/farm-health/history', summary="Query AFHI farm health audit history (Protected)")
async def get_farm_health_history(
    farm_id: Optional[str] = Query(None),
    farmId: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves AFHI historical evaluations. Enforces farm ownership."""
    fid = farm_id or farmId
    if fid:
        verify_farm_ownership(fid, current_user)
        history = db_service.get_farm_health_history(farm_id=fid, limit=limit)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        history = []
        for f in user_farms:
            history.extend(db_service.get_farm_health_history(farm_id=f["farm_id"], limit=limit))
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        history = history[:limit]
    return {"success": True, "count": len(history), "history": history, "data": history}

# -----------------------------------------------------------------------------
# 6. ADVISORIES HISTORY (Protected)
# -----------------------------------------------------------------------------
@router.get('/advisories', summary="Query historical agronomic advisories (Protected)")
async def get_advisories(
    farm_id: Optional[str] = Query(None),
    farmId: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves agronomic recommendations history. Enforces farm ownership."""
    fid = farm_id or farmId
    if fid:
        verify_farm_ownership(fid, current_user)
        advisories = db_service.get_recent_advisories(farm_id=fid, limit=limit)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        advisories = []
        for f in user_farms:
            advisories.extend(db_service.get_recent_advisories(farm_id=f["farm_id"], limit=limit))
        advisories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        advisories = advisories[:limit]
    return {"success": True, "count": len(advisories), "advisories": advisories, "data": advisories}

# -----------------------------------------------------------------------------
# 7. ALERTS ENDPOINTS (Protected)
# -----------------------------------------------------------------------------
@router.get('/alerts', summary="Query active/recent farm alerts (Protected)")
async def get_alerts(
    farm_id: Optional[str] = Query(None),
    farmId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves alerts belonging only to the authenticated farmer's farms."""
    fid = farm_id or farmId
    if fid:
        verify_farm_ownership(fid, current_user)
        alerts = db_service.get_recent_alerts(farm_id=fid, status=status, limit=limit)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        alerts = []
        for f in user_farms:
            alerts.extend(db_service.get_recent_alerts(farm_id=f["farm_id"], status=status, limit=limit))
        alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        alerts = alerts[:limit]
    return {"success": True, "count": len(alerts), "alerts": alerts, "data": alerts}

@router.post('/alerts', status_code=status.HTTP_201_CREATED, summary="Create farm alert (Protected)")
async def create_alert(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Creates a new farm alert record. Enforces farm ownership."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    farm_id = data.get("farm_id") or data.get("farmId")
    if farm_id:
        verify_farm_ownership(farm_id, current_user)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        if not user_farms:
            raise HTTPException(status_code=400, detail="Must have at least one farm to create alerts.")
        data["farm_id"] = user_farms[0]["farm_id"]

    try:
        alert = db_service.create_alert(data)
        return {"success": True, "data": alert, "alert": alert}
    except ModelValidationError as e:
        return JSONResponse(status_code=400, content={"error": "Validation Error", "message": str(e)})

# -----------------------------------------------------------------------------
# 8. PUMP EVENTS HISTORY (Protected)
# -----------------------------------------------------------------------------
@router.get('/pump/events', summary="Query actuator pump state change history (Protected)")
async def get_pump_events(
    farm_id: Optional[str] = Query(None),
    farmId: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves pump state change history. Enforces farm ownership."""
    fid = farm_id or farmId
    if fid:
        verify_farm_ownership(fid, current_user)
        events = db_service.get_pump_events(farm_id=fid, limit=limit)
    else:
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        events = []
        for f in user_farms:
            events.extend(db_service.get_pump_events(farm_id=f["farm_id"], limit=limit))
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        events = events[:limit]
    return {"success": True, "count": len(events), "events": events, "data": events}
