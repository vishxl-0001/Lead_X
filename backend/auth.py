import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "vishxl")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "7023568437")
SECRET_KEY = os.environ.get("SECRET_KEY", "lead_x_super_secret_auth_key_2026_secure").encode()


def authenticate_user(username: str, password: str) -> bool:
    """Constant-time comparison for username and password to prevent timing attacks."""
    user_match = hmac.compare_digest(username.strip(), ADMIN_USERNAME)
    pass_match = hmac.compare_digest(password.strip(), ADMIN_PASSWORD)
    return user_match and pass_match


def create_token(username: str, expires_in_sec: int = 7 * 86400) -> str:
    """Generates an HMAC-SHA256 signed bearer token with 7-day expiration."""
    now = int(time.time())
    payload = {
        "sub": username,
        "exp": now + expires_in_sec,
        "iat": now
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies HMAC signature and expiration of bearer token."""
    if not token:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None

        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode())
        payload = json.loads(payload_bytes.decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency to secure endpoints.
    Requires 'Authorization: Bearer <token>' header.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload.get("sub", ADMIN_USERNAME)
