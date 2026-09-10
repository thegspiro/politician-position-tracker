"""Authentication.

Logins are per-user. ADMIN_PASSWORD exists only to bootstrap the first owner
account on a fresh install; once any account exists it no longer authenticates,
so there is never an unprotected window and never a shared credential whose
actions cannot be attributed to a person.

Sessions are short-lived signed tokens rather than a value derived from a
password, so they expire on their own and a logout is meaningful.
"""

import logging
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import ROLE_OWNER, User
from .passwords import verify_password

logger = logging.getLogger(__name__)

# Values that shipped as defaults. Booting with either on a reachable
# deployment means the admin panel is open to anyone who has read the README.
INSECURE_PASSWORDS = {"", "changeme"}
INSECURE_SECRETS = {"", "politician-tracker-secret-key", "change-this-to-a-random-string"}

ALGORITHM = "HS256"
TOKEN_SUBJECT = "admin"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
# Username given to the account bootstrapped from ADMIN_PASSWORD.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin").strip() or "admin"
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "12"))

# Escape hatch for local development and for anyone upgrading who is not ready
# to set credentials yet. It must be set deliberately.
ALLOW_INSECURE_DEFAULTS = os.environ.get("ALLOW_INSECURE_DEFAULTS", "").lower() in {
    "1",
    "true",
    "yes",
}

# Failed logins allowed per client address before further attempts are refused.
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "900"))


def _resolve_secret_key() -> str:
    """Return the signing key, refusing to run on a published default."""
    configured = os.environ.get("SECRET_KEY", "")
    if configured and configured not in INSECURE_SECRETS:
        return configured

    if not ALLOW_INSECURE_DEFAULTS:
        raise RuntimeError(
            "SECRET_KEY is unset or still set to a published default value. "
            "Set SECRET_KEY to a long random string (for example: "
            "`openssl rand -base64 32`). To run without it anyway, set "
            "ALLOW_INSECURE_DEFAULTS=1 -- do not do this on a reachable host."
        )

    # Development fallback: a per-process key. Sessions do not survive a
    # restart, which is the correct trade for never shipping a known key.
    logger.warning(
        "SECRET_KEY is unset or insecure; generating an ephemeral key. "
        "Sessions will be invalidated on restart. Do not use this in production."
    )
    return secrets.token_urlsafe(48)


def _validate_password() -> None:
    if ADMIN_PASSWORD in INSECURE_PASSWORDS and not ALLOW_INSECURE_DEFAULTS:
        raise RuntimeError(
            "ADMIN_PASSWORD is unset or still set to the default 'changeme'. "
            "Set ADMIN_PASSWORD to a strong password before starting. To run "
            "without it anyway, set ALLOW_INSECURE_DEFAULTS=1 -- do not do this "
            "on a reachable host."
        )
    if ADMIN_PASSWORD in INSECURE_PASSWORDS:
        logger.warning(
            "ADMIN_PASSWORD is unset or insecure and ALLOW_INSECURE_DEFAULTS is "
            "set. The admin panel is effectively unprotected."
        )


_validate_password()
SECRET_KEY = _resolve_secret_key()

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class _LoginThrottle:
    """Per-address sliding window over failed login attempts.

    Held in memory, so the limit applies per process rather than per cluster.
    That is the right scope for this single-container application; a multi
    replica deployment would need shared state.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - self._window_seconds
        for key in list(self._attempts):
            recent = [t for t in self._attempts[key] if t > cutoff]
            if recent:
                self._attempts[key] = recent
            else:
                del self._attempts[key]

    def retry_after(self, key: str) -> int | None:
        """Seconds the caller must wait, or None if an attempt is allowed."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            attempts = self._attempts.get(key, [])
            if len(attempts) < self._max_attempts:
                return None
            return max(1, int(self._window_seconds - (now - attempts[0])))

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            self._attempts.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_throttle = _LoginThrottle(LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def create_access_token(subject: str = TOKEN_SUBJECT) -> tuple[str, int]:
    """Return a signed token and its lifetime in seconds."""
    expires_in = SESSION_TTL_HOURS * 3600
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), expires_in


class LoginRequest(BaseModel):
    password: str
    # Optional so a client written against the single-password API keeps
    # working: an omitted username means the bootstrap account.
    username: str | None = None


class LoginResponse(BaseModel):
    token: str
    expires_in: int
    username: str
    role: str
    display_name: str | None = None


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Return the user these credentials identify, or None.

    ADMIN_PASSWORD is accepted only while no account exists, to bootstrap the
    first owner. Once one does, it stops working entirely.
    """
    user = (
        db.query(User)
        .filter(User.username == username, User.is_active == 1)
        .first()
    )
    if user is None:
        # Hash anyway so a missing username takes the same time as a wrong
        # password, rather than being distinguishable by how fast it fails.
        verify_password(password, None)
        return None

    if not verify_password(password, user.password_hash):
        return None
    return user


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client = _client_key(request)

    retry_after = login_throttle.retry_after(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    username = (data.username or ADMIN_USERNAME).strip()
    user = authenticate(db, username, data.password)

    if user is None:
        login_throttle.record_failure(client)
        logger.warning("Failed login for %r from %s", username, client)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Deliberately does not say which half was wrong.
            detail="Invalid username or password",
        )

    login_throttle.reset(client)
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    token, expires_in = create_access_token(user.uid)
    return {
        "token": token,
        "expires_in": expires_in,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
    }


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to the account it belongs to."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise unauthorized

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        # Covers a bad signature, a malformed token and an expired one.
        raise unauthorized from None

    subject = payload.get("sub")
    if not subject:
        raise unauthorized

    user = db.query(User).filter(User.uid == subject, User.is_active == 1).first()
    if user is None:
        # The account was deleted or deactivated after the token was issued.
        raise unauthorized
    return user


# Any signed-in account may edit content.
require_admin = current_user


def require_owner(user: User = Depends(current_user)) -> User:
    """Restrict an endpoint to owners, who alone manage accounts."""
    if user.role != ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an owner account",
        )
    return user
