"""Tests for Wayback Machine archiving.

Every test stubs the HTTP layer: the suite must not depend on reaching
archive.org, and must not submit anything there when it runs.
"""

from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app import archiving
from app.main import app
from app.routers import statements as statements_router
from tests.conftest import TEST_ADMIN_PASSWORD

SNAPSHOT = "https://web.archive.org/web/20260114000000/https://congress.gov/bill"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth(client):
    response = client.post("/api/auth/login", json={"password": TEST_ADMIN_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def make_statement(client, auth, sources):
    import uuid

    suffix = uuid.uuid4().hex[:8]
    politician = client.post(
        "/api/politicians",
        headers=auth,
        json={"name": f"P {suffix}", "party": "Independent", "office": "Senate"},
    ).json()
    issue = client.post(
        "/api/issues", headers=auth, json={"name": f"I {suffix}"}
    ).json()
    response = client.post(
        "/api/statements",
        headers=auth,
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": f"T {suffix}",
            "analysis": "Body",
            "post_url": "https://x.com/e/status/1",
            "post_platform": "X",
            "sources": sources,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def source(**overrides):
    payload = {
        "source_type": "analysis",
        "title": "A bill",
        "url": "https://congress.gov/bill",
    }
    payload.update(overrides)
    return payload


# --- Which URLs may be submitted ----------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://congress.gov/bill", True),
        ("http://example.test/a", True),
        ("javascript:alert(1)", False),
        ("file:///etc/passwd", False),
        ("ftp://example.test/a", False),
        ("https://", False),
        ("", False),
        (None, False),
        # Re-submitting a snapshot would archive the archive.
        (f"{archiving.WAYBACK_PREFIX}2026/https://e.test", False),
    ],
)
def test_is_submittable(url, expected):
    assert archiving.is_submittable(url) is expected


# --- Reading the save response ------------------------------------------


def stub_response(status=200, headers=None, url=archiving.SAVE_ENDPOINT):
    request = httpx.Request("GET", url)
    return httpx.Response(status, headers=headers or {}, request=request)


def test_snapshot_is_read_from_the_content_location_header(monkeypatch):
    monkeypatch.setattr(
        archiving,
        "_snapshot_url_from_response",
        archiving._snapshot_url_from_response,
    )
    response = stub_response(headers={"content-location": "/web/2026/https://e.test"})
    assert archiving._snapshot_url_from_response(response, "https://e.test") == (
        "https://web.archive.org/web/2026/https://e.test"
    )


def test_absolute_content_location_is_used_as_is():
    response = stub_response(headers={"content-location": SNAPSHOT})
    assert archiving._snapshot_url_from_response(response, "https://e.test") == SNAPSHOT


def test_a_redirect_to_the_snapshot_is_accepted():
    response = stub_response(url=SNAPSHOT)
    assert archiving._snapshot_url_from_response(response, "https://e.test") == SNAPSHOT


# --- archive_url --------------------------------------------------------


def install_stub(monkeypatch, response=None, error=None, record=None):
    """Replace the HTTP client so no request leaves the test process."""

    class StubClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, **kwargs):
            if record is not None:
                record.append(url)
            if error is not None:
                raise error
            return response

    monkeypatch.setattr(archiving.httpx, "Client", StubClient)


def test_a_successful_capture_returns_the_snapshot(monkeypatch):
    install_stub(monkeypatch, stub_response(headers={"content-location": SNAPSHOT}))
    result = archiving.archive_url("https://congress.gov/bill")
    assert result.ok
    assert result.url == SNAPSHOT
    assert isinstance(result.timestamp, datetime)


def test_a_network_error_is_reported_not_raised(monkeypatch):
    install_stub(monkeypatch, error=httpx.ConnectError("no route to host"))
    result = archiving.archive_url("https://congress.gov/bill")
    assert not result.ok
    assert "no route to host" in result.error


def test_a_timeout_is_reported_not_raised(monkeypatch):
    install_stub(monkeypatch, error=httpx.ReadTimeout("timed out"))
    result = archiving.archive_url("https://congress.gov/bill")
    assert not result.ok


def test_an_error_status_is_reported(monkeypatch):
    install_stub(monkeypatch, stub_response(status=503))
    result = archiving.archive_url("https://congress.gov/bill")
    assert not result.ok
    assert "503" in result.error


def test_a_response_without_a_snapshot_is_a_failure(monkeypatch):
    install_stub(monkeypatch, stub_response())
    assert not archiving.archive_url("https://congress.gov/bill").ok


def test_an_unsubmittable_url_is_never_sent(monkeypatch):
    sent: list[str] = []
    install_stub(monkeypatch, stub_response(), record=sent)
    result = archiving.archive_url("javascript:alert(1)")
    assert not result.ok
    assert sent == [], "an unsafe URL must not reach the archive service"


def test_the_target_url_is_appended_to_the_save_endpoint(monkeypatch):
    sent: list[str] = []
    install_stub(
        monkeypatch, stub_response(headers={"content-location": SNAPSHOT}), record=sent
    )
    archiving.archive_url("https://congress.gov/bill")
    assert sent == [archiving.SAVE_ENDPOINT + "https://congress.gov/bill"]


# --- Automatic archiving on save ----------------------------------------


def test_saving_does_not_archive_when_the_feature_is_off(client, auth, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", False)
    monkeypatch.setattr(
        archiving, "archive_url", lambda url, **kw: calls.append(url) or None
    )
    make_statement(client, auth, [source()])
    assert calls == [], "archiving is opt-in and must stay off by default"


def test_saving_archives_pending_sources_when_enabled(client, auth, monkeypatch):
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", True)
    monkeypatch.setattr(
        archiving,
        "archive_url",
        lambda url, **kw: archiving.ArchiveResult(SNAPSHOT, datetime(2026, 1, 14)),
    )
    statement = make_statement(client, auth, [source()])

    # BackgroundTasks run once the response is delivered.
    refreshed = client.get(f"/api/statements/{statement['id']}").json()
    assert refreshed["sources"][0]["archive_url"] == SNAPSHOT
    assert refreshed["sources"][0]["archived_at"] is not None


def test_a_source_that_already_has_an_archive_is_left_alone(client, auth, monkeypatch):
    existing = "https://web.archive.org/web/2025/https://congress.gov/bill"
    calls: list[str] = []
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", True)

    def record(url, **kwargs):
        calls.append(url)
        return archiving.ArchiveResult(SNAPSHOT, datetime(2026, 1, 14))

    monkeypatch.setattr(archiving, "archive_url", record)
    statement = make_statement(client, auth, [source(archive_url=existing)])

    refreshed = client.get(f"/api/statements/{statement['id']}").json()
    assert refreshed["sources"][0]["archive_url"] == existing
    assert calls == [], "an existing snapshot must not be replaced"


def test_a_failed_capture_leaves_the_save_intact(client, auth, monkeypatch):
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", True)
    monkeypatch.setattr(
        archiving,
        "archive_url",
        lambda url, **kw: archiving.ArchiveResult(None, None, error="unreachable"),
    )
    statement = make_statement(client, auth, [source()])

    refreshed = client.get(f"/api/statements/{statement['id']}").json()
    assert refreshed["sources"][0]["archive_url"] is None
    assert refreshed["title"], "the statement itself must still be saved"


def test_one_failure_does_not_lose_another_sources_snapshot(client, auth, monkeypatch):
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", True)

    def sometimes(url, **kwargs):
        if "fails" in url:
            return archiving.ArchiveResult(None, None, error="unreachable")
        return archiving.ArchiveResult(SNAPSHOT, datetime(2026, 1, 14))

    monkeypatch.setattr(archiving, "archive_url", sometimes)
    statement = make_statement(
        client,
        auth,
        [
            source(title="Fails", url="https://congress.gov/fails"),
            source(title="Works", url="https://congress.gov/works"),
        ],
    )

    sources = {
        s["title"]: s
        for s in client.get(f"/api/statements/{statement['id']}").json()["sources"]
    }
    assert sources["Fails"]["archive_url"] is None
    assert sources["Works"]["archive_url"] == SNAPSHOT


# --- Manual archiving ---------------------------------------------------


def test_archive_now_stores_the_snapshot(client, auth, monkeypatch):
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", False)
    statement = make_statement(client, auth, [source()])
    uid = statement["sources"][0]["uid"]

    monkeypatch.setattr(
        archiving,
        "archive_url",
        lambda url, **kw: archiving.ArchiveResult(SNAPSHOT, datetime(2026, 1, 14)),
    )
    response = client.post(
        f"/api/statements/{statement['id']}/sources/{uid}/archive", headers=auth
    )
    assert response.status_code == 200, response.text
    assert response.json()["archive_url"] == SNAPSHOT

    refreshed = client.get(f"/api/statements/{statement['id']}").json()
    assert refreshed["sources"][0]["archive_url"] == SNAPSHOT


def test_archive_now_works_even_when_automatic_archiving_is_off(client, auth, monkeypatch):
    """A deployment that keeps archiving off can still archive deliberately."""
    monkeypatch.setattr(archiving, "ARCHIVE_ENABLED", False)
    statement = make_statement(client, auth, [source()])
    monkeypatch.setattr(
        archiving,
        "archive_url",
        lambda url, **kw: archiving.ArchiveResult(SNAPSHOT, datetime(2026, 1, 14)),
    )
    response = client.post(
        f"/api/statements/{statement['id']}/sources/{statement['sources'][0]['uid']}/archive",
        headers=auth,
    )
    assert response.status_code == 200


def test_archive_now_reports_a_service_failure_as_a_gateway_error(client, auth, monkeypatch):
    statement = make_statement(client, auth, [source()])
    monkeypatch.setattr(
        archiving,
        "archive_url",
        lambda url, **kw: archiving.ArchiveResult(None, None, error="unreachable"),
    )
    response = client.post(
        f"/api/statements/{statement['id']}/sources/{statement['sources'][0]['uid']}/archive",
        headers=auth,
    )
    assert response.status_code == 502
    assert "unreachable" in response.json()["detail"]


def test_archive_now_requires_authentication(client, auth):
    statement = make_statement(client, auth, [source()])
    response = client.post(
        f"/api/statements/{statement['id']}/sources/{statement['sources'][0]['uid']}/archive"
    )
    assert response.status_code in (401, 403)


def test_archive_now_404s_for_an_unknown_source(client, auth):
    statement = make_statement(client, auth, [source()])
    response = client.post(
        f"/api/statements/{statement['id']}/sources/nosuchuid00/archive", headers=auth
    )
    assert response.status_code == 404


def test_archive_now_will_not_cross_statements(client, auth):
    """A uid from another statement must not be archivable through this one."""
    first = make_statement(client, auth, [source()])
    second = make_statement(client, auth, [source(title="Other")])
    response = client.post(
        f"/api/statements/{second['id']}/sources/{first['sources'][0]['uid']}/archive",
        headers=auth,
    )
    assert response.status_code == 404
