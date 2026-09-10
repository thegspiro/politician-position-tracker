"""Tests for named accounts, roles, attribution and the bootstrap cutover."""

import pytest
from fastapi.testclient import TestClient

from app import auth, passwords
from app.bootstrap import bootstrap_owner
from app.database import SessionLocal
from app.main import app
from app.models import ROLE_EDITOR, ROLE_OWNER, User
from tests.conftest import TEST_ADMIN_PASSWORD

STRONG_PASSWORD = "a-sufficiently-long-password"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_throttle():
    auth.login_throttle.reset("testclient")
    yield
    auth.login_throttle.reset("testclient")


@pytest.fixture()
def owner_auth(client):
    response = client.post(
        "/api/auth/login",
        json={"username": auth.ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def created_users():
    """Remove accounts made during a test, keeping the suite's owner."""
    made: list[str] = []
    yield made
    db = SessionLocal()
    try:
        for username in made:
            user = db.query(User).filter(User.username == username).first()
            if user:
                db.delete(user)
        db.commit()
    finally:
        db.close()


def make_user(client, owner_auth, created_users, **overrides):
    import uuid

    payload = {
        "username": f"editor-{uuid.uuid4().hex[:8]}",
        "password": STRONG_PASSWORD,
        "role": ROLE_EDITOR,
    }
    payload.update(overrides)
    response = client.post("/api/users", headers=owner_auth, json=payload)
    if response.status_code == 201:
        created_users.append(response.json()["username"])
    return response


# --- Password hashing ---------------------------------------------------


def test_a_password_verifies_against_its_hash():
    stored = passwords.hash_password(STRONG_PASSWORD)
    assert passwords.verify_password(STRONG_PASSWORD, stored)
    assert not passwords.verify_password("something else", stored)


def test_hashes_are_salted():
    """Two accounts with the same password must not share a hash."""
    first = passwords.hash_password(STRONG_PASSWORD)
    second = passwords.hash_password(STRONG_PASSWORD)
    assert first != second
    assert passwords.verify_password(STRONG_PASSWORD, second)


def test_the_hash_records_its_own_parameters():
    """So the cost can be raised later without invalidating old passwords."""
    stored = passwords.hash_password(STRONG_PASSWORD)
    algorithm, n, r, p, salt, digest = stored.split("$")
    assert algorithm == "scrypt"
    assert int(n) >= 2**14
    assert len(bytes.fromhex(salt)) == passwords.SALT_BYTES


@pytest.mark.parametrize("stored", ["", None, "not-a-hash", "scrypt$bad", "md5$1$1$1$aa$bb"])
def test_a_malformed_hash_is_a_failed_login_not_a_crash(stored):
    assert passwords.verify_password("anything", stored) is False


def test_the_plaintext_password_never_appears_in_the_hash():
    assert STRONG_PASSWORD not in passwords.hash_password(STRONG_PASSWORD)


# --- Bootstrap ----------------------------------------------------------


def test_bootstrap_is_a_no_op_once_an_account_exists():
    """The suite's owner already exists, so a second run must change nothing."""
    assert bootstrap_owner() is False


def test_the_bootstrap_account_is_an_owner():
    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.username == auth.ADMIN_USERNAME).one()
        assert owner.role == ROLE_OWNER
        assert owner.is_active == 1
    finally:
        db.close()


def test_the_shared_password_authenticates_only_through_its_account(client):
    """ADMIN_PASSWORD works because it hashed into the owner account, not as a
    credential of its own: a different username with it must fail."""
    response = client.post(
        "/api/auth/login",
        json={"username": "someone-else", "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 401


# --- Login --------------------------------------------------------------


def test_login_returns_the_account_identity(client):
    body = client.post(
        "/api/auth/login",
        json={"username": auth.ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    ).json()
    assert body["username"] == auth.ADMIN_USERNAME
    assert body["role"] == ROLE_OWNER
    assert body["token"]


def test_omitting_the_username_falls_back_to_the_bootstrap_account(client):
    """Keeps a client written against the single-password API working."""
    response = client.post("/api/auth/login", json={"password": TEST_ADMIN_PASSWORD})
    assert response.status_code == 200
    assert response.json()["username"] == auth.ADMIN_USERNAME


def test_a_wrong_password_does_not_reveal_whether_the_user_exists(client):
    missing = client.post(
        "/api/auth/login", json={"username": "no-such-user", "password": "whatever"}
    )
    wrong = client.post(
        "/api/auth/login",
        json={"username": auth.ADMIN_USERNAME, "password": "wrong-password"},
    )
    assert missing.status_code == wrong.status_code == 401
    assert missing.json()["detail"] == wrong.json()["detail"]


def test_login_records_the_time(client, owner_auth):
    me = client.get("/api/users/me", headers=owner_auth).json()
    assert me["last_login_at"] is not None


def test_a_new_account_can_log_in(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    response = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["role"] == ROLE_EDITOR


def test_a_deactivated_account_cannot_log_in(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    client.put(
        f"/api/users/{created['uid']}", headers=owner_auth, json={"is_active": False}
    )
    response = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    )
    assert response.status_code == 401


def test_a_token_stops_working_once_its_account_is_deactivated(
    client, owner_auth, created_users
):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/users/me", headers=headers).status_code == 200

    client.put(
        f"/api/users/{created['uid']}", headers=owner_auth, json={"is_active": False}
    )
    assert client.get("/api/users/me", headers=headers).status_code == 401


# --- Roles --------------------------------------------------------------


def test_an_editor_may_not_list_accounts(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_an_editor_may_not_create_accounts(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "sneaky", "password": STRONG_PASSWORD, "role": "owner"},
    )
    assert response.status_code == 403


def test_an_editor_may_still_edit_content(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    response = client.post(
        "/api/politicians",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Editor Made This", "party": "Independent", "office": "Senate"},
    )
    assert response.status_code == 201


# --- Managing accounts --------------------------------------------------


def test_creating_an_account_never_returns_the_hash(client, owner_auth, created_users):
    body = make_user(client, owner_auth, created_users).json()
    assert "password" not in body
    assert "password_hash" not in body


def test_listing_accounts_never_returns_hashes(client, owner_auth, created_users):
    make_user(client, owner_auth, created_users)
    for entry in client.get("/api/users", headers=owner_auth).json():
        assert "password_hash" not in entry


def test_a_duplicate_username_is_rejected(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    again = make_user(client, owner_auth, created_users, username=created["username"])
    assert again.status_code == 400


@pytest.mark.parametrize("password", ["short", "", "elevenchar"])
def test_a_weak_password_is_rejected(client, owner_auth, created_users, password):
    assert make_user(
        client, owner_auth, created_users, password=password
    ).status_code == 422


@pytest.mark.parametrize("username", ["ab", "has space", "has/slash", "x" * 200])
def test_an_invalid_username_is_rejected(client, owner_auth, created_users, username):
    assert make_user(
        client, owner_auth, created_users, username=username
    ).status_code == 422


def test_an_unknown_role_is_rejected(client, owner_auth, created_users):
    assert make_user(
        client, owner_auth, created_users, role="superuser"
    ).status_code == 422


def test_the_last_owner_cannot_be_demoted(client, owner_auth):
    me = client.get("/api/users/me", headers=owner_auth).json()
    response = client.put(
        f"/api/users/{me['uid']}", headers=owner_auth, json={"role": ROLE_EDITOR}
    )
    assert response.status_code == 400
    assert "only owner" in response.json()["detail"]


def test_the_last_owner_cannot_be_deleted(client, owner_auth):
    me = client.get("/api/users/me", headers=owner_auth).json()
    assert client.delete(f"/api/users/{me['uid']}", headers=owner_auth).status_code == 400


def test_an_owner_cannot_deactivate_themselves(client, owner_auth):
    me = client.get("/api/users/me", headers=owner_auth).json()
    response = client.put(
        f"/api/users/{me['uid']}", headers=owner_auth, json={"is_active": False}
    )
    assert response.status_code == 400


def test_demoting_an_owner_is_allowed_when_another_remains(
    client, owner_auth, created_users
):
    second = make_user(client, owner_auth, created_users, role=ROLE_OWNER).json()
    response = client.put(
        f"/api/users/{second['uid']}", headers=owner_auth, json={"role": ROLE_EDITOR}
    )
    assert response.status_code == 200
    assert response.json()["role"] == ROLE_EDITOR


def test_deleting_an_account_keeps_the_statements_it_created(
    client, owner_auth, created_users
):
    import uuid

    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    editor = {"Authorization": f"Bearer {token}"}

    suffix = uuid.uuid4().hex[:8]
    politician = client.post(
        "/api/politicians",
        headers=editor,
        json={"name": f"P {suffix}", "party": "Independent", "office": "Senate"},
    ).json()
    issue = client.post("/api/issues", headers=editor, json={"name": f"I {suffix}"}).json()
    statement = client.post(
        "/api/statements",
        headers=editor,
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": f"By the editor {suffix}",
            "analysis": "Body",
            "post_url": "https://x.com/e/status/1",
            "post_platform": "X",
        },
    ).json()

    assert client.delete(f"/api/users/{created['uid']}", headers=owner_auth).status_code == 204
    created_users.remove(created["username"])

    survived = client.get(f"/api/statements/{statement['id']}")
    assert survived.status_code == 200, "deleting an account must not delete its work"
    assert survived.json()["created_by"] is None


# --- Changing your own password -----------------------------------------


def test_changing_your_own_password(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    new_password = "an-even-longer-new-password"
    response = client.post(
        "/api/users/me/password",
        headers=headers,
        json={"current_password": STRONG_PASSWORD, "new_password": new_password},
    )
    assert response.status_code == 204

    assert client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": new_password},
    ).status_code == 200
    assert client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).status_code == 401


def test_changing_a_password_requires_the_current_one(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "not-it", "new_password": "a-brand-new-password"},
    )
    assert response.status_code == 400


def test_a_new_password_must_meet_the_strength_rule(client, owner_auth, created_users):
    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]
    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": STRONG_PASSWORD, "new_password": "short"},
    )
    assert response.status_code == 422


# --- Attribution --------------------------------------------------------


def test_a_statement_records_who_created_it(client, owner_auth):
    import uuid

    suffix = uuid.uuid4().hex[:8]
    politician = client.post(
        "/api/politicians",
        headers=owner_auth,
        json={"name": f"P {suffix}", "party": "Independent", "office": "Senate"},
    ).json()
    issue = client.post("/api/issues", headers=owner_auth, json={"name": f"I {suffix}"}).json()
    statement = client.post(
        "/api/statements",
        headers=owner_auth,
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": f"Attributed {suffix}",
            "analysis": "Body",
            "post_url": "https://x.com/e/status/1",
            "post_platform": "X",
            "sources": [
                {
                    "source_type": "analysis",
                    "title": "S",
                    "url": "https://e.test/s",
                }
            ],
        },
    ).json()

    assert statement["created_by"]["username"] == auth.ADMIN_USERNAME
    assert statement["updated_by"]["username"] == auth.ADMIN_USERNAME
    assert statement["sources"][0]["created_by"]["username"] == auth.ADMIN_USERNAME


def test_an_edit_records_the_editor_but_keeps_the_creator(
    client, owner_auth, created_users
):
    import uuid

    suffix = uuid.uuid4().hex[:8]
    politician = client.post(
        "/api/politicians",
        headers=owner_auth,
        json={"name": f"P {suffix}", "party": "Independent", "office": "Senate"},
    ).json()
    issue = client.post("/api/issues", headers=owner_auth, json={"name": f"I {suffix}"}).json()
    statement = client.post(
        "/api/statements",
        headers=owner_auth,
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": f"Original {suffix}",
            "analysis": "Body",
            "post_url": "https://x.com/e/status/1",
            "post_platform": "X",
        },
    ).json()

    created = make_user(client, owner_auth, created_users).json()
    token = client.post(
        "/api/auth/login",
        json={"username": created["username"], "password": STRONG_PASSWORD},
    ).json()["token"]

    updated = client.put(
        f"/api/statements/{statement['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "politician_id": politician["id"],
            "issue_ids": [issue["id"]],
            "title": f"Edited {suffix}",
            "analysis": "Body",
            "post_url": "https://x.com/e/status/1",
            "post_platform": "X",
        },
    ).json()

    assert updated["created_by"]["username"] == auth.ADMIN_USERNAME
    assert updated["updated_by"]["username"] == created["username"]
