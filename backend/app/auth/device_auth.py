from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field
from app.services.database import db_service
from app.auth.models import AuthenticatedUser
from app.auth.dependencies import get_current_user

class AuthenticatedDevice(BaseModel):
    """Represents a verified physical IoT device authenticated via device API key."""
    device_id: str = Field(..., description="Device unique ID")
    farm_id: str = Field(..., description="Registered farm plot ID")
    status: str = Field("active", description="Device operating status (active, inactive, revoked)")
    device_name: Optional[str] = Field("AgroGuard Controller", description="Device display name")
    device_api_key: Optional[str] = Field(None, description="Device authentication key")

    model_config = {"extra": "allow"}

async def get_device_auth(request: Request) -> Optional[AuthenticatedDevice]:
    """
    Extracts and verifies the device API key from the request headers.
    Header: 'X-Device-API-Key: <key>'
    Raises 401 if key is invalid/unknown.
    Raises 403 if device status is inactive or revoked.
    """
    api_key = (
        request.headers.get("X-Device-API-Key") or
        request.headers.get("x-device-api-key") or
        request.headers.get("X-API-Key") or
        request.headers.get("x-api-key")
    )
    if not api_key:
        return None

    api_key = api_key.strip()
    device_doc = db_service.get_device_by_api_key(api_key)
    if not device_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Device API Key."
        )

    dev_status = str(device_doc.get("status") or "active").strip().lower()
    if dev_status in ("inactive", "revoked", "disabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is inactive or revoked."
        )

    device_id = str(device_doc.get("device_id") or device_doc.get("deviceId") or device_doc.get("id") or "").strip()
    farm_id = str(device_doc.get("farm_id") or device_doc.get("farmId") or "").strip()

    return AuthenticatedDevice(
        device_id=device_id,
        farm_id=farm_id,
        status=dev_status,
        device_name=device_doc.get("device_name", "AgroGuard Controller"),
        device_api_key=api_key
    )

async def get_device_or_farmer_auth(request: Request) -> Tuple[Optional[AuthenticatedDevice], Optional[AuthenticatedUser]]:
    """
    Dual-authentication dependency for telemetry ingestion.
    Supports either:
    1. Hardware Device Authentication via 'X-Device-API-Key'
    2. Farmer User Authentication via 'Authorization: Bearer <JWT>'
    """
    # Check if Device API Key is provided
    device = await get_device_auth(request)
    if device is not None:
        return (device, None)

    # Check if Bearer token is provided
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.strip().lower().startswith("bearer"):
        user = await get_current_user(request)
        return (None, user)

    # If device API key was provided in headers with bad key, get_device_auth already raised 401.
    # If no recognized credential was provided:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide 'X-Device-API-Key' header or 'Authorization: Bearer <token>'."
    )
