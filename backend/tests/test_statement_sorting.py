"""Tests for statement list ordering.

The timeline shows one page of results, so ordering must happen in the
database. Sorting the rows the client already holds reorders only that page:
asking for the oldest statements would return the oldest of the newest page,
which is wrong in a way that looks plausible.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_ADMIN_PASSWORD


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth(client):
    response = client.post("/api/auth/login", json={"password": TEST_ADMIN_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def dataset(client, auth):
    """Statements from three politicians across a known range of dates.

    Titles encode the intended chronological position so assertions read
    clearly. Returns the issue id used for filtering.
    """
    import uuid

    suffix = uuid.uuid4().hex[:8]
    issue = client.post(
        "/api/issues", headers=auth, json={"name": f"Sorting {suffix}"}
    ).json()

    # Deliberately not alphabetical, so an alphabetical sort has to do work.
    people = ["Zara Young", "Alice Adams", "Mia Nolan"]
    politicians = [
        client.post(
            "/api/politicians",
            headers=auth,
            json={"name": f"{name} {suffix}", "party": "Independent", "office": "Senate"},
        ).json()
        for name in people
    ]

    base = datetime(2026, 1, 1)
    created = []
    for index in range(9):
        politician = politicians[index % 3]
        post_date = base + timedelta(days=index)
        response = client.post(
            "/api/statements",
            headers=auth,
            json={
                "politician_id": politician["id"],
                "issue_ids": [issue["id"]],
                "title": f"{suffix} day {index:02d}",
                "analysis": "Body",
                "post_url": f"https://x.com/example/status/{index}",
                "post_platform": "X",
                "post_date": post_date.isoformat(),
            },
        )
        assert response.status_code == 201, response.text
        created.append(response.json())
    return {"issue_id": issue["id"], "suffix": suffix, "statements": created}


def titles(client, **params) -> list[str]:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    response = client.get(f"/api/statements?{query}")
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


def days(client, **params) -> list[int]:
    return [int(title.split()[-1]) for title in titles(client, **params)]


# --- Ordering across the whole result set -------------------------------


def test_newest_first_by_default(client, dataset):
    assert days(client, issue_id=dataset["issue_id"]) == [8, 7, 6, 5, 4, 3, 2, 1, 0]


def test_oldest_first(client, dataset):
    assert days(client, issue_id=dataset["issue_id"], sort="oldest") == [
        0, 1, 2, 3, 4, 5, 6, 7, 8
    ]


def test_sorting_is_applied_before_the_page_is_cut(client, dataset):
    """The heart of the bug: a page of oldest results must be the oldest overall.

    Sorting in the client returned the oldest of whichever page had loaded --
    here that would have been days 6, 7, 8 rather than 0, 1, 2.
    """
    assert days(client, issue_id=dataset["issue_id"], sort="oldest", limit=3) == [0, 1, 2]
    assert days(client, issue_id=dataset["issue_id"], sort="newest", limit=3) == [8, 7, 6]


def test_paging_walks_the_sorted_set(client, dataset):
    first = days(client, issue_id=dataset["issue_id"], sort="oldest", limit=4, skip=0)
    second = days(client, issue_id=dataset["issue_id"], sort="oldest", limit=4, skip=4)
    assert first == [0, 1, 2, 3]
    assert second == [4, 5, 6, 7]
    assert not set(first) & set(second), "pages must not repeat a statement"


def test_politician_alphabetical(client, dataset):
    names = [
        item["politician"]["name"]
        for item in client.get(
            f"/api/statements?issue_id={dataset['issue_id']}&sort=politician-az"
        ).json()["items"]
    ]
    assert names == sorted(names)
    assert names[0].startswith("Alice Adams")
    assert names[-1].startswith("Zara Young")


def test_politician_sort_orders_each_politician_newest_first(client, dataset):
    items = client.get(
        f"/api/statements?issue_id={dataset['issue_id']}&sort=politician-az"
    ).json()["items"]
    for name in {item["politician"]["name"] for item in items}:
        theirs = [
            int(item["title"].split()[-1])
            for item in items
            if item["politician"]["name"] == name
        ]
        assert theirs == sorted(theirs, reverse=True)


# --- Dating rule --------------------------------------------------------


def test_post_date_orders_ahead_of_created_at(client, auth, dataset):
    """A statement recorded now but posted long ago sorts as an old statement."""
    politician = dataset["statements"][0]["politician_id"]
    response = client.post(
        "/api/statements",
        headers=auth,
        json={
            "politician_id": politician,
            "issue_ids": [dataset["issue_id"]],
            "title": f"{dataset['suffix']} day -1",
            "analysis": "Body",
            "post_url": "https://x.com/example/status/old",
            "post_platform": "X",
            "post_date": "2025-06-01T00:00:00",
        },
    )
    assert response.status_code == 201, response.text

    ordered = titles(client, issue_id=dataset["issue_id"], sort="oldest")
    assert ordered[0].endswith("day -1"), "the oldest post must lead, not the newest row"


def test_a_statement_without_a_post_date_falls_back_to_created_at(client, auth, dataset):
    response = client.post(
        "/api/statements",
        headers=auth,
        json={
            "politician_id": dataset["statements"][0]["politician_id"],
            "issue_ids": [dataset["issue_id"]],
            "title": f"{dataset['suffix']} day 99",
            "analysis": "Body",
            "post_url": "https://x.com/example/status/undated",
            "post_platform": "X",
        },
    )
    assert response.status_code == 201, response.text

    # Created now, so it is the newest by the fallback.
    assert titles(client, issue_id=dataset["issue_id"])[0].endswith("day 99")


# --- Interaction with filters and validation ----------------------------


def test_sorting_combines_with_a_search_filter(client, dataset):
    result = days(
        client, issue_id=dataset["issue_id"], search=dataset["suffix"], sort="oldest"
    )
    assert result == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_sorting_combines_with_a_politician_filter(client, dataset):
    politician_id = dataset["statements"][0]["politician_id"]
    result = days(client, politician_id=politician_id, sort="oldest")
    assert result == sorted(result)


def test_total_is_unaffected_by_sorting(client, dataset):
    totals = {
        sort: client.get(
            f"/api/statements?issue_id={dataset['issue_id']}&sort={sort}&limit=2"
        ).json()["total"]
        for sort in ("newest", "oldest", "politician-az")
    }
    assert set(totals.values()) == {9}


def test_an_unknown_sort_is_rejected(client):
    assert client.get("/api/statements?sort=sideways").status_code == 422


def test_omitting_sort_keeps_working(client, dataset):
    """Existing API consumers that never sent a sort are unaffected."""
    assert client.get("/api/statements").status_code == 200
