from typing import Optional
from pydantic import BaseModel, Field

class AuthenticatedUser(BaseModel):
    """Represents a verified authenticated identity from a Supabase / JWT token."""
    id: str = Field(..., description="Supabase Auth UID (sub)")
    auth_user_id: str = Field(..., description="Supabase Auth UID")
    phone: Optional[str] = Field(None, description="Farmer phone number")
    email: Optional[str] = Field(None, description="Farmer email address")
    role: str = Field("authenticated", description="Token role")
    farmer_id: Optional[str] = Field(None, description="Mapped AgroGuard farmer record ID")

    model_config = {"extra": "allow"}
