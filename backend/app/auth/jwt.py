import time
from typing import Dict, Any, Optional
import jwt
try:
    from app.config import Config
except ImportError:
    from config import Config

ALGORITHMS = ["HS256"]

def get_jwt_secret() -> str:
    """Returns the JWT signing/verification secret."""
    return Config.SUPABASE_JWT_SECRET or Config.SECRET_KEY

def create_access_token(
    auth_user_id: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    expires_in_seconds: int = 86400,
    role: str = "authenticated",
    secret: Optional[str] = None
) -> str:
    """Creates a signed JWT access token compatible with Supabase Auth schema."""
    now = int(time.time())
    payload = {
        "sub": auth_user_id,
        "auth_user_id": auth_user_id,
        "phone": phone or "+919876543210",
        "email": email or "",
        "role": role,
        "aud": "authenticated",
        "iss": "supabase",
        "iat": now,
        "exp": now + expires_in_seconds
    }
    signing_key = secret or get_jwt_secret()
    return jwt.encode(payload, signing_key, algorithm="HS256")

def decode_and_verify_token(token: str) -> Dict[str, Any]:
    """
    Verifies and decodes a Bearer JWT token.
    Validates expiration and signature against Supabase JWT secret or local secret key.
    """
    signing_key = get_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=ALGORITHMS,
            options={"verify_aud": False, "verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError as e:
        # Fallback to Config.SECRET_KEY if configured differently
        if signing_key != Config.SECRET_KEY:
            try:
                payload = jwt.decode(
                    token,
                    Config.SECRET_KEY,
                    algorithms=ALGORITHMS,
                    options={"verify_aud": False, "verify_exp": True}
                )
                return payload
            except jwt.ExpiredSignatureError:
                raise ValueError("Token has expired.")
            except Exception:
                pass
        raise ValueError(f"Invalid authentication token: {e}")
