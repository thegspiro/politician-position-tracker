"""Tests for authentication, upload handling and security headers."""

import importlib
import io
import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app import auth, main
from app.main import app
from tests.conftest import TEST_ADMIN_PASSWORD

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
GIF_BYTES = b"GIF89a" + b"\x00" * 64
WEBP_BYTES = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 64


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_throttle():
    """Each test starts with a clean rate-limit window."""
    auth.login_throttle.reset("testclient")
    yield
    auth.login_throttle.reset("testclient")


def login(client) -> str:
    response = client.post("/api/auth/login", json={"password": TEST_ADMIN_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth_header(client) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client)}"}


# --- Tokens -------------------------------------------------------------


def test_login_returns_a_token_and_its_lifetime(client):
    body = client.post(
        "/api/auth/login", json={"password": TEST_ADMIN_PASSWORD}
    ).json()
    assert body["token"]
    assert body["expires_in"] == auth.SESSION_TTL_HOURS * 3600


def test_token_carries_a_subject_and_an_expiry(client):
    claims = jwt.decode(login(client), auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert claims["sub"] == "admin"
    assert claims["exp"] > claims["iat"]


def test_token_is_not_derived_from_the_password(client):
    """The old scheme returned HMAC(secret, password): a static, eternal token."""
    first = login(client)
    time.sleep(1.1)
    second = login(client)
    assert first != second, "each login must mint a distinct session"


def test_a_valid_token_is_accepted(client):
    response = client.get("/api/export", headers=auth_header(client))
    assert response.status_code == 200


def test_an_expired_token_is_rejected(client):
    expired = jwt.encode(
        {"sub": "admin", "iat": 0, "exp": 1},
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )
    response = client.get("/api/export", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_a_token_signed_with_another_key_is_rejected(client):
    forged = jwt.encode(
        {"sub": "admin", "exp": 9999999999}, "not-the-real-key", algorithm="HS256"
    )
    response = client.get("/api/export", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


@pytest.mark.parametrize("value", ["", "Bearer", "Bearer not-a-token", "Bearer  "])
def test_malformed_authorization_headers_are_rejected(client, value):
    response = client.get("/api/export", headers={"Authorization": value})
    assert response.status_code in (401, 403)


def test_missing_token_is_rejected(client):
    assert client.get("/api/export").status_code in (401, 403)


# --- Login throttling ---------------------------------------------------


def test_repeated_failures_are_throttled(client):
    for _ in range(auth.LOGIN_MAX_ATTEMPTS):
        assert (
            client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
        )

    blocked = client.post("/api/auth/login", json={"password": "wrong"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_throttling_also_blocks_the_correct_password(client):
    """Otherwise the limit could be probed around with a known-good guess."""
    for _ in range(auth.LOGIN_MAX_ATTEMPTS):
        client.post("/api/auth/login", json={"password": "wrong"})

    response = client.post(
        "/api/auth/login", json={"password": TEST_ADMIN_PASSWORD}
    )
    assert response.status_code == 429


def test_a_successful_login_clears_the_failure_count(client):
    for _ in range(auth.LOGIN_MAX_ATTEMPTS - 1):
        client.post("/api/auth/login", json={"password": "wrong"})

    assert login(client)

    for _ in range(auth.LOGIN_MAX_ATTEMPTS - 1):
        assert (
            client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
        )


# --- Insecure defaults --------------------------------------------------


@pytest.mark.parametrize("password", ["changeme", ""])
def test_the_app_refuses_to_load_with_a_default_password(monkeypatch, password):
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    monkeypatch.setenv("SECRET_KEY", "a-real-secret-key-value")
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        importlib.reload(auth)


@pytest.mark.parametrize(
    "secret", ["", "politician-tracker-secret-key", "change-this-to-a-random-string"]
)
def test_the_app_refuses_to_load_with_a_published_secret(monkeypatch, secret):
    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password")
    monkeypatch.setenv("SECRET_KEY", secret)
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        importlib.reload(auth)


def test_insecure_defaults_can_be_opted_into_explicitly(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "changeme")
    monkeypatch.setenv("SECRET_KEY", "")
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "1")

    reloaded = importlib.reload(auth)
    assert reloaded.SECRET_KEY, "an ephemeral key is generated rather than a known one"
    assert reloaded.SECRET_KEY not in reloaded.INSECURE_SECRETS


@pytest.fixture(autouse=True)
def restore_auth_module():
    """Reload auth with the test environment after any module-level reload."""
    yield
    importlib.reload(auth)


# --- Uploads ------------------------------------------------------------


def upload(client, filename: str, content: bytes):
    return client.post(
        "/api/uploads",
        headers=auth_header(client),
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
    )


def test_a_png_upload_succeeds(client):
    response = upload(client, "shot.png", PNG_BYTES)
    assert response.status_code == 200, response.text
    assert response.json()["url"].startswith("/uploads/")


@pytest.mark.parametrize(
    ("name", "content"), [("a.gif", GIF_BYTES), ("a.webp", WEBP_BYTES)]
)
def test_other_raster_formats_are_accepted(client, name, content):
    assert upload(client, name, content).status_code == 200


def test_svg_uploads_are_rejected(client):
    """An SVG served from our origin can run script against the admin session."""
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    response = upload(client, "payload.svg", svg)
    assert response.status_code == 400
    assert ".svg" in response.json()["detail"]


def test_content_must_match_the_extension(client):
    """A script renamed to .png must not be stored as an image."""
    response = upload(client, "payload.png", b"<script>alert(1)</script>")
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_an_oversized_upload_is_refused(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024)
    response = upload(client, "big.png", PNG_BYTES + b"\x00" * 4096)
    assert response.status_code == 413


def test_a_refused_upload_leaves_no_file_behind(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 1024)
    before = set(main.UPLOAD_DIR.iterdir())
    upload(client, "big.png", PNG_BYTES + b"\x00" * 4096)
    assert set(main.UPLOAD_DIR.iterdir()) == before


def test_uploads_require_authentication(client):
    response = client.post(
        "/api/uploads",
        files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert response.status_code in (401, 403)


# --- Security headers ---------------------------------------------------


def test_api_responses_carry_the_baseline_headers(client):
    headers = client.get("/api/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_the_csp_allows_the_embed_hosts_but_not_arbitrary_script(client):
    csp = client.get("/api/health").headers["Content-Security-Policy"]
    assert "https://platform.twitter.com" in csp
    assert "https://embed.bsky.app" in csp
    assert "frame-src https:" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "'unsafe-eval'" not in csp
    assert "script-src 'self' https://platform.twitter.com" in csp


def test_uploaded_files_get_a_locked_down_policy(client):
    url = upload(client, "shot.png", PNG_BYTES).json()["url"]
    headers = client.get(url).headers
    assert headers["Content-Security-Policy"] == main.UPLOAD_CSP
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "sandbox" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_cors_is_off_unless_configured(client):
    response = client.get(
        "/api/health", headers={"Origin": "https://attacker.example"}
    )
    assert "access-control-allow-origin" not in {
        key.lower() for key in response.headers
    }
