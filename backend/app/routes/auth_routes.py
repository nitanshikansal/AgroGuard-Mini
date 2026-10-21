from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth import get_current_user, AuthenticatedUser, create_access_token
from app.services.database import db_service

router = APIRouter(prefix="/auth", tags=["Authentication & Session"])

class DemoTokenRequest(BaseModel):
    phone: Optional[str] = "+919876543210"
    auth_user_id: Optional[str] = None
    email: Optional[str] = None

@router.post('/demo-token', summary="Generate a valid demo JWT access token for offline/development mode")
async def generate_demo_token(req: DemoTokenRequest):
    """
    Issues a valid JWT access token for local development or mock OTP flow.
    Automatically provisions the farmer profile in the database.
    """
    phone = req.phone or "+919876543210"
    clean_digits = "".join(c for c in phone if c.isdigit())
    auth_user_id = req.auth_user_id or f"auth_user_{clean_digits[-10:] if len(clean_digits) >= 10 else 'demo'}"
    
    # Auto-provision farmer
    farmer = db_service.get_or_create_farmer_for_auth(
        auth_user_id=auth_user_id,
        phone=phone,
        email=req.email or ""
    )
    
    token = create_access_token(
        auth_user_id=auth_user_id,
        phone=phone,
        email=req.email or "",
        role="authenticated"
    )
    
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "auth_user_id": auth_user_id,
        "farmer_id": farmer.get("farmer_id"),
        "farmer": farmer
    }

@router.get('/me', summary="Get authenticated farmer session information (Protected)")
async def get_current_session(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Validates the Bearer token and returns authenticated farmer profile."""
    farmer = db_service.get_farmer(current_user.farmer_id)
    if not farmer:
        farmer = db_service.get_or_create_farmer_for_auth(current_user.auth_user_id)
    return {
        "success": True,
        "auth_user_id": current_user.auth_user_id,
        "farmer_id": current_user.farmer_id,
        "phone": current_user.phone,
        "role": current_user.role,
        "farmer": farmer
    }
