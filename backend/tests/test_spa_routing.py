"""Regression tests for the SPA catch-all route.

The catch-all previously passed the request path straight to ``FileResponse``,
so a percent-encoded traversal such as ``/%2e%2e/data/politician_tracker.db``
escaped the static directory and served arbitrary files -- including the SQLite
database and the application source. These tests pin the confinement behaviour
against the real application object.
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

# A real file outside STATIC_DIR that must never be reachable over HTTP.
ESCAPE_TARGET = "app/main.py"
ESCAPE_MARKER = "resolve_static_file"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


# --- resolve_static_file ------------------------------------------------


def test_resolves_a_real_file_inside_the_static_dir():
    resolved = main.resolve_static_file("assets/app.js")
    assert resolved == (main.STATIC_DIR / "assets" / "app.js").resolve()


def test_unknown_path_resolves_to_none():
    assert main.resolve_static_file("politicians/42") is None


def test_directory_is_not_served_as_a_file():
    assert main.resolve_static_file("assets") is None


@pytest.mark.parametrize(
    "path",
    [
        f"../{ESCAPE_TARGET}",
        f"../../backend/{ESCAPE_TARGET}",
        f"assets/../../{ESCAPE_TARGET}",
        "/etc/hostname",
        "..",
    ],
)
def test_traversal_attempts_are_rejected(path):
    assert main.resolve_static_file(path) is None


def test_symlink_escaping_the_static_dir_is_rejected():
    link = main.STATIC_DIR / "leak.py"
    link.symlink_to(main.STATIC_DIR.parent / ESCAPE_TARGET)
    try:
        assert main.resolve_static_file("leak.py") is None
    finally:
        link.unlink()


# --- HTTP behaviour -----------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        f"/%2e%2e/{ESCAPE_TARGET}",
        f"/..%2f{ESCAPE_TARGET}",
        f"/%2e%2e%2f{ESCAPE_TARGET.replace('/', '%2f')}",
    ],
)
def test_encoded_traversal_over_http_falls_back_to_the_spa(client, url):
    response = client.get(url)
    assert response.status_code == 200
    assert ESCAPE_MARKER not in response.text


def test_client_side_route_serves_the_spa_shell(client):
    response = client.get("/politicians/42")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_real_static_asset_is_still_served(client):
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


def test_api_routes_are_unaffected(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
