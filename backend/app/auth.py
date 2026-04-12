import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
SECRET_KEY = os.environ.get("SECRET_KEY", "politician-tracker-secret-key")

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


def _make_token(password: str) -> str:
    return hmac.new(
        SECRET_KEY.encode(), password.encode(), hashlib.sha256
    ).hexdigest()


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    token = _make_token(data.password)
    return {"token": token}


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Dependency that validates the Bearer token matches the admin token."""
    expected = _make_token(ADMIN_PASSWORD)
    if not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )
    return credentials.credentials
