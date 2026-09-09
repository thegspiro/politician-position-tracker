"""Tests for the Alembic migration chain.

These run each migration against a throwaway SQLite database so that the
upgrade path a deployment takes is exercised on every test run, including the
uid backfill that has to cope with pre-existing rows.
"""

import sqlite3
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.database import Base
from tests.conftest import alembic_config


@pytest.fixture()
def db(tmp_path):
    """An empty database file plus its Alembic config."""
    path = tmp_path / "migrations.db"
    return path, alembic_config(f"sqlite:///{path}")


def columns(path: Path, table: str) -> list[str]:
    with sqlite3.connect(path) as connection:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def seed_sources(path: Path, count: int) -> None:
    """Insert sources using only the columns that exist at revision 0001."""
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO politicians (id, name, party, office)"
            " VALUES (1, 'Test', 'Independent', 'Senate')"
        )
        connection.execute(
            "INSERT INTO statements"
            " (id, politician_id, title, analysis, post_url, post_platform)"
            " VALUES (1, 1, 'Title', 'Analysis', 'https://example.test', 'x')"
        )
        for index in range(1, count + 1):
            connection.execute(
                "INSERT INTO sources (id, statement_id, source_type, title, url)"
                " VALUES (?, 1, 'analysis', ?, ?)",
                (index, f"Source {index}", f"https://example.test/{index}"),
            )


def test_upgrade_to_head_matches_the_models(db):
    path, config = db
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{path}")
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == [], f"schema drifted from models.py: {diff}"


def test_baseline_has_no_primary_source_columns(db):
    path, config = db
    command.upgrade(config, "0001")
    assert "uid" not in columns(path, "sources")


def test_upgrade_adds_every_primary_source_column(db):
    path, config = db
    command.upgrade(config, "head")
    present = set(columns(path, "sources"))
    expected = {
        "uid",
        "media_type",
        "publisher",
        "published_date",
        "excerpt",
        "locator",
        "archive_url",
        "archived_at",
        "retrieved_at",
        "sort_order",
    }
    assert expected <= present


def test_uid_is_backfilled_for_pre_existing_rows(db):
    path, config = db
    command.upgrade(config, "0001")
    seed_sources(path, 5)

    command.upgrade(config, "head")

    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT id, uid FROM sources ORDER BY id").fetchall()
    uids = [uid for _, uid in rows]
    assert len(uids) == 5
    assert all(uids), "every pre-existing source must receive a uid"
    assert len(set(uids)) == 5, "backfilled uids must be unique"
    assert all(len(uid) == models.SOURCE_UID_LENGTH for uid in uids)


def test_new_columns_get_usable_defaults_for_pre_existing_rows(db):
    path, config = db
    command.upgrade(config, "0001")
    seed_sources(path, 1)

    command.upgrade(config, "head")

    with sqlite3.connect(path) as connection:
        media_type, sort_order = connection.execute(
            "SELECT media_type, sort_order FROM sources WHERE id = 1"
        ).fetchone()
    assert media_type == "webpage"
    assert sort_order == 0


def test_uid_is_unique_across_rows(db):
    path, config = db
    command.upgrade(config, "head")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO politicians (id, name, party, office)"
            " VALUES (1, 'Test', 'Independent', 'Senate')"
        )
        connection.execute(
            "INSERT INTO statements"
            " (id, politician_id, title, analysis, post_url, post_platform)"
            " VALUES (1, 1, 'Title', 'Analysis', 'https://example.test', 'x')"
        )
        connection.execute(
            "INSERT INTO sources (id, uid, statement_id, source_type, title, url)"
            " VALUES (1, 'dupe00000001', 1, 'analysis', 'A', 'https://example.test/a')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO sources (id, uid, statement_id, source_type, title, url)"
                " VALUES (2, 'dupe00000001', 1, 'analysis', 'B', 'https://example.test/b')"
            )


def test_downgrade_removes_the_columns_and_keeps_the_rows(db):
    path, config = db
    command.upgrade(config, "0001")
    seed_sources(path, 3)
    command.upgrade(config, "head")

    command.downgrade(config, "0001")

    remaining = columns(path, "sources")
    assert "uid" not in remaining
    assert "media_type" not in remaining
    with sqlite3.connect(path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert count == 3, "downgrade must not drop source rows"
