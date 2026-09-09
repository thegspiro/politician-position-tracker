"""Tests for source persistence on the statements API.

Focused on the two behaviours primary-source embedding depends on: that a
source's stable uid survives a statement edit, and that the new fields
round-trip through create, update, export and import.
"""

import pytest
from fastapi.testclient import TestClient

from app.auth import ADMIN_PASSWORD
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth(client):
    response = client.post("/api/auth/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def politician(client, auth):
    response = client.post(
        "/api/politicians",
        headers=auth,
        json={"name": "Test Member", "party": "Independent", "office": "Senate"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def issue(client, auth):
    import uuid

    response = client.post(
        "/api/issues",
        headers=auth,
        json={"name": f"Issue {uuid.uuid4().hex[:8]}", "description": None},
    )
    assert response.status_code == 201, response.text
    return response.json()


def primary_source(**overrides):
    source = {
        "source_type": "analysis",
        "title": "H.R. 1234 as introduced",
        "url": "https://www.congress.gov/bill/hr1234",
        "description": "The bill text being described.",
        "media_type": "document",
        "publisher": "Congress.gov",
        "published_date": "2026-01-14T00:00:00",
        "excerpt": "Nothing in this section shall be construed to limit...",
        "locator": "sec. 203(b)",
        "archive_url": "https://web.archive.org/web/2026/https://www.congress.gov/bill/hr1234",
        "archived_at": "2026-01-20T00:00:00",
        "retrieved_at": "2026-01-20T00:00:00",
    }
    source.update(overrides)
    return source


def statement_payload(politician, issue, sources):
    return {
        "politician_id": politician["id"],
        "issue_ids": [issue["id"]],
        "title": "A tracked statement",
        "analysis": "Analysis body.",
        "post_url": "https://x.com/example/status/1",
        "post_platform": "X",
        "sources": sources,
    }


def create_statement(client, auth, politician, issue, sources):
    response = client.post(
        "/api/statements",
        headers=auth,
        json=statement_payload(politician, issue, sources),
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Round-tripping -----------------------------------------------------


def test_primary_source_fields_round_trip(client, auth, politician, issue):
    created = create_statement(client, auth, politician, issue, [primary_source()])
    source = created["sources"][0]

    assert source["media_type"] == "document"
    assert source["publisher"] == "Congress.gov"
    assert source["locator"] == "sec. 203(b)"
    assert source["excerpt"].startswith("Nothing in this section")
    assert source["archive_url"].startswith("https://web.archive.org/")
    assert source["uid"]


def test_a_source_without_the_new_fields_still_works(client, auth, politician, issue):
    """The pre-existing request shape must keep working unchanged."""
    legacy = {
        "source_type": "post",
        "title": "Legacy source",
        "url": "https://example.test/legacy",
        "description": "No primary source fields supplied.",
    }
    created = create_statement(client, auth, politician, issue, [legacy])
    source = created["sources"][0]

    assert source["media_type"] == "webpage"
    assert source["publisher"] is None
    assert source["sort_order"] == 0
    assert source["uid"]


# --- uid stability ------------------------------------------------------


def test_uid_survives_a_statement_edit(client, auth, politician, issue):
    created = create_statement(client, auth, politician, issue, [primary_source()])
    original_uid = created["sources"][0]["uid"]

    payload = statement_payload(
        politician,
        issue,
        [primary_source(uid=original_uid, title="H.R. 1234 as amended")],
    )
    updated = client.put(
        f"/api/statements/{created['id']}", headers=auth, json=payload
    )
    assert updated.status_code == 200, updated.text

    source = updated.json()["sources"][0]
    assert source["uid"] == original_uid, "a citation anchor must survive an edit"
    assert source["title"] == "H.R. 1234 as amended"


def test_editing_an_unrelated_field_keeps_every_source_uid(client, auth, politician, issue):
    created = create_statement(
        client,
        auth,
        politician,
        issue,
        [primary_source(title="First"), primary_source(title="Second")],
    )
    uids = [source["uid"] for source in created["sources"]]

    payload = statement_payload(
        politician,
        issue,
        [
            primary_source(uid=uids[0], title="First"),
            primary_source(uid=uids[1], title="Second"),
        ],
    )
    payload["title"] = "Retitled statement"
    updated = client.put(
        f"/api/statements/{created['id']}", headers=auth, json=payload
    )
    assert updated.status_code == 200, updated.text
    assert [source["uid"] for source in updated.json()["sources"]] == uids


def test_removing_a_source_deletes_only_that_source(client, auth, politician, issue):
    created = create_statement(
        client,
        auth,
        politician,
        issue,
        [primary_source(title="Keep"), primary_source(title="Drop")],
    )
    keep_uid = created["sources"][0]["uid"]

    payload = statement_payload(
        politician, issue, [primary_source(uid=keep_uid, title="Keep")]
    )
    updated = client.put(
        f"/api/statements/{created['id']}", headers=auth, json=payload
    )
    assert updated.status_code == 200, updated.text

    sources = updated.json()["sources"]
    assert len(sources) == 1
    assert sources[0]["uid"] == keep_uid


def test_a_new_source_added_during_an_edit_gets_its_own_uid(client, auth, politician, issue):
    created = create_statement(client, auth, politician, issue, [primary_source()])
    existing_uid = created["sources"][0]["uid"]

    payload = statement_payload(
        politician,
        issue,
        [primary_source(uid=existing_uid), primary_source(title="Added later")],
    )
    updated = client.put(
        f"/api/statements/{created['id']}", headers=auth, json=payload
    )
    assert updated.status_code == 200, updated.text

    uids = [source["uid"] for source in updated.json()["sources"]]
    assert existing_uid in uids
    assert len(set(uids)) == 2


# --- Ordering -----------------------------------------------------------


def test_sort_order_follows_the_submitted_order(client, auth, politician, issue):
    created = create_statement(
        client,
        auth,
        politician,
        issue,
        [primary_source(title="A"), primary_source(title="B"), primary_source(title="C")],
    )
    assert [s["title"] for s in created["sources"]] == ["A", "B", "C"]
    assert [s["sort_order"] for s in created["sources"]] == [0, 1, 2]


def test_reordering_sources_is_persisted(client, auth, politician, issue):
    created = create_statement(
        client, auth, politician, issue, [primary_source(title="A"), primary_source(title="B")]
    )
    uid_a, uid_b = (source["uid"] for source in created["sources"])

    payload = statement_payload(
        politician,
        issue,
        [primary_source(uid=uid_b, title="B"), primary_source(uid=uid_a, title="A")],
    )
    client.put(f"/api/statements/{created['id']}", headers=auth, json=payload)

    fetched = client.get(f"/api/statements/{created['id']}").json()
    assert [source["title"] for source in fetched["sources"]] == ["B", "A"]


# --- Validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(document.cookie)",
        "JavaScript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "not-a-url",
    ],
)
def test_unsafe_source_urls_are_rejected(client, auth, politician, issue, url):
    response = client.post(
        "/api/statements",
        headers=auth,
        json=statement_payload(politician, issue, [primary_source(url=url)]),
    )
    assert response.status_code == 422, response.text


def test_unsafe_post_urls_are_rejected(client, auth, politician, issue):
    payload = statement_payload(politician, issue, [primary_source()])
    payload["post_url"] = "javascript:alert(1)"
    response = client.post("/api/statements", headers=auth, json=payload)
    assert response.status_code == 422, response.text


def test_unknown_media_type_is_rejected(client, auth, politician, issue):
    response = client.post(
        "/api/statements",
        headers=auth,
        json=statement_payload(politician, issue, [primary_source(media_type="hologram")]),
    )
    assert response.status_code == 422, response.text


def test_unknown_source_type_is_rejected(client, auth, politician, issue):
    response = client.post(
        "/api/statements",
        headers=auth,
        json=statement_payload(politician, issue, [primary_source(source_type="rumour")]),
    )
    assert response.status_code == 422, response.text


def test_blank_archive_url_is_accepted_as_absent(client, auth, politician, issue):
    created = create_statement(
        client, auth, politician, issue, [primary_source(archive_url="")]
    )
    assert created["sources"][0]["archive_url"] is None


# --- Export / import ----------------------------------------------------


def test_export_includes_the_primary_source_fields(client, auth, politician, issue):
    create_statement(client, auth, politician, issue, [primary_source()])
    exported = client.get("/api/export", headers=auth).json()

    sources = [s for stmt in exported["statements"] for s in stmt["sources"]]
    assert any(s["media_type"] == "document" and s["uid"] for s in sources)


def test_import_assigns_a_uid_when_a_backup_omits_one(client, auth):
    backup = {
        "politicians": [
            {"id": 900, "name": "Imported Member", "party": "Independent", "office": "House"}
        ],
        "issues": [{"id": 900, "name": "Imported Issue", "description": None}],
        "statements": [
            {
                "politician_id": 900,
                "title": "Imported statement",
                "analysis": "Body",
                "post_url": "https://example.test/post",
                "post_platform": "X",
                "issues": [{"id": 900}],
                "sources": [
                    {
                        "source_type": "analysis",
                        "title": "Old backup source",
                        "url": "https://example.test/source",
                    }
                ],
            }
        ],
    }
    response = client.post("/api/import", headers=auth, json=backup)
    assert response.status_code == 200, response.text
    assert response.json()["imported"]["sources"] == 1

    exported = client.get("/api/export", headers=auth).json()
    imported = [
        s
        for stmt in exported["statements"]
        for s in stmt["sources"]
        if s["title"] == "Old backup source"
    ]
    assert len(imported) == 1
    assert imported[0]["uid"], "an imported source must be given a uid"
    assert imported[0]["media_type"] == "webpage"


def test_a_repeated_uid_in_one_submission_does_not_drop_a_source(
    client, auth, politician, issue
):
    """A duplicated uid must yield two rows, not one silently overwritten."""
    created = create_statement(client, auth, politician, issue, [primary_source()])
    uid = created["sources"][0]["uid"]

    payload = statement_payload(
        politician,
        issue,
        [primary_source(uid=uid, title="First"), primary_source(uid=uid, title="Second")],
    )
    updated = client.put(
        f"/api/statements/{created['id']}", headers=auth, json=payload
    )
    assert updated.status_code == 200, updated.text

    sources = updated.json()["sources"]
    assert [s["title"] for s in sources] == ["First", "Second"]
    assert len({s["uid"] for s in sources}) == 2


def test_a_uid_from_another_statement_is_not_hijacked(client, auth, politician, issue):
    other = create_statement(
        client, auth, politician, issue, [primary_source(title="Other statement source")]
    )
    other_uid = other["sources"][0]["uid"]

    mine = create_statement(client, auth, politician, issue, [primary_source(title="Mine")])
    payload = statement_payload(
        politician, issue, [primary_source(uid=other_uid, title="Mine")]
    )
    updated = client.put(f"/api/statements/{mine['id']}", headers=auth, json=payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["sources"][0]["uid"] != other_uid

    untouched = client.get(f"/api/statements/{other['id']}").json()
    assert untouched["sources"][0]["uid"] == other_uid
    assert untouched["sources"][0]["title"] == "Other statement source"
