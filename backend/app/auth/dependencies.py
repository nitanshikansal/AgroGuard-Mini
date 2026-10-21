from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from app.auth.models import AuthenticatedUser
from app.auth.jwt import decode_and_verify_token
from app.services.database import db_service

async def get_current_user(request: Request) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates the Bearer JWT token from
    the Authorization header, resolves the Supabase Auth UID (sub), maps it to
    an AgroGuard farmer profile (creating on first login), and attaches farmer_id.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    parts = auth_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = parts[1]

    try:
        payload = decode_and_verify_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

    auth_user_id = payload.get("sub") or payload.get("auth_user_id")
    if not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier ('sub').",
            headers={"WWW-Authenticate": "Bearer"}
        )

    phone = payload.get("phone", "")
    email = payload.get("email", "")
    role = payload.get("role", "authenticated")

    # Resolve or create the stable AgroGuard farmer profile for this Auth UID
    farmer = db_service.get_or_create_farmer_for_auth(
        auth_user_id=auth_user_id,
        phone=phone,
        email=email
    )

    user = AuthenticatedUser(
        id=auth_user_id,
        auth_user_id=auth_user_id,
        phone=phone,
        email=email,
        role=role,
        farmer_id=farmer.get("farmer_id")
    )
    return user

async def get_optional_current_user(request: Request) -> Optional[AuthenticatedUser]:
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth_header:
        return None
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

def verify_farm_ownership(farm_id: str, current_user: AuthenticatedUser) -> dict:
    """Verifies that the target farm belongs to the authenticated farmer. Raises 403 if not."""
    farm = db_service.get_farm(farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{farm_id}' not found."
        )
    farm_owner = farm.get("farmer_id") or farm.get("farmerId")
    if farm_owner != current_user.farmer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You do not have ownership of farm '{farm_id}'."
        )
    return farm

def verify_device_ownership(device_id: str, current_user: AuthenticatedUser) -> dict:
    """Verifies that the target device belongs to a farm owned by the authenticated farmer."""
    all_devices = db_service.get_devices()
    target_device = None
    for d in all_devices:
        if d.get("device_id") == device_id or d.get("deviceId") == device_id or d.get("id") == device_id:
            target_device = d
            break

    if not target_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found."
        )

    farm_id = target_device.get("farm_id") or target_device.get("farmId")
    if not farm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Device is not associated with an accessible farm."
        )

    verify_farm_ownership(farm_id, current_user)
    return target_device
