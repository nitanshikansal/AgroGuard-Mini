from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.auth import get_current_user, AuthenticatedUser, verify_farm_ownership
from app.services.pump_service import pump_service
from app.services.database import db_service

router = APIRouter(tags=["Actuator & Pump Control"])

@router.get('/control/pump', summary="Get irrigation pump operating status (Protected)")
async def get_pump_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the current state and operating mode of the irrigation pump for authenticated farmer."""
    return pump_service.get_status()

@router.post('/control/pump', summary="Set irrigation pump state (Protected & Ownership Enforced)")
async def set_pump_state(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Sets the operating state of the irrigation pump.
    Enforces that target farm_id belongs to the authenticated farmer.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Bad Request", "message": "JSON body required."})

    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Bad Request", "message": "JSON body required."})

    new_state = None
    if "active" in data:
        val = data.get("active")
        if isinstance(val, bool):
            new_state = val
        elif isinstance(val, (int, float)):
            new_state = bool(val)
        elif str(val).lower() in ("true", "1", "on"):
            new_state = True
        elif str(val).lower() in ("false", "0", "off"):
            new_state = False

    if new_state is None and "state" in data:
        state_str = str(data["state"]).strip().upper()
        if state_str in ("ON", "RUNNING", "TRUE", "1"):
            new_state = True
        elif state_str in ("OFF", "STOPPED", "FALSE", "0"):
            new_state = False

    if new_state is None:
        return JSONResponse(status_code=400, content={"error": "Bad Request", "message": "Field 'active' or 'state' is required."})

    # Verify farm ownership if farm_id is supplied
    farm_id = data.get("farm_id") or data.get("farmId")
    if farm_id:
        # Check ownership: raises 403 if user doesn't own this farm
        verify_farm_ownership(farm_id, current_user)
    else:
        # Resolve to user's first farm or default
        user_farms = db_service.get_farms(farmer_id=current_user.farmer_id)
        farm_id = user_farms[0]["farm_id"] if user_farms else f"farm_{current_user.farmer_id[:8]}"

    # Actuate state
    result = pump_service.set_pump_state(new_state)

    # Record event in Database
    try:
        device_id = data.get("device_id") or data.get("deviceId") or "arduino_r4_pump"
        source = data.get("triggered_by") or data.get("source") or "dashboard_manual"
        reason = data.get("reason", "")
        db_service.record_pump_event({
            "farm_id": farm_id,
            "device_id": device_id,
            "action": "ON" if new_state else "OFF",
            "triggered_by": source,
            "reason": reason
        })
    except Exception as e:
        print(f"[CONTROL WARNING] Failed to record pump event in database: {e}")

    result["action"] = "ON" if new_state else "OFF"
    result["pump_state"] = "ON" if new_state else "OFF"
    result["state"] = "running" if new_state else "stopped"
    result["status_text"] = f"Pump turned {'ON' if new_state else 'OFF'}"
    return result
