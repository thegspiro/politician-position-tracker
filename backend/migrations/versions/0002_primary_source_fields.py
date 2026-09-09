"""Add primary source fields to sources

Adds the fields needed to treat a source as an embeddable primary source
rather than a bare hyperlink: a stable public identifier, a media type that
drives rendering, provenance (publisher/date), the verbatim excerpt and its
locator, archive details for link rot, and an explicit display order.

uid is added nullable, backfilled with a generated value for every existing
row, then made NOT NULL and unique, so the migration is safe on a populated
database.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import new_source_uid

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SOURCE_UID_LENGTH = 12


def upgrade() -> None:
    op.add_column("sources", sa.Column("uid", sa.String(length=SOURCE_UID_LENGTH), nullable=True))
    op.add_column(
        "sources",
        sa.Column(
            "media_type",
            sa.String(length=20),
            nullable=False,
            server_default="webpage",
        ),
    )
    op.add_column("sources", sa.Column("publisher", sa.String(length=200), nullable=True))
    op.add_column("sources", sa.Column("published_date", sa.DateTime(), nullable=True))
    op.add_column("sources", sa.Column("excerpt", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("locator", sa.String(length=100), nullable=True))
    op.add_column("sources", sa.Column("archive_url", sa.String(length=1000), nullable=True))
    op.add_column("sources", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("sources", sa.Column("retrieved_at", sa.DateTime(), nullable=True))
    op.add_column(
        "sources",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    _backfill_uids()

    with op.batch_alter_table("sources") as batch_op:
        batch_op.alter_column(
            "uid",
            existing_type=sa.String(length=SOURCE_UID_LENGTH),
            nullable=False,
        )
    op.create_index(op.f("ix_sources_uid"), "sources", ["uid"], unique=True)


def _backfill_uids() -> None:
    """Give every existing source a unique uid.

    Generated row by row rather than in SQL because the value must match the
    application's uid format, and uniqueness is enforced by the index created
    immediately afterwards.
    """
    connection = op.get_bind()
    sources = sa.table(
        "sources",
        sa.column("id", sa.Integer),
        sa.column("uid", sa.String),
    )
    rows = connection.execute(
        sa.select(sources.c.id).where(sources.c.uid.is_(None))
    ).fetchall()

    used: set[str] = set()
    for (source_id,) in rows:
        uid = new_source_uid()
        while uid in used:
            uid = new_source_uid()
        used.add(uid)
        connection.execute(
            sources.update().where(sources.c.id == source_id).values(uid=uid)
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_sources_uid"), table_name="sources")
    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_column("sort_order")
        batch_op.drop_column("retrieved_at")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("archive_url")
        batch_op.drop_column("locator")
        batch_op.drop_column("excerpt")
        batch_op.drop_column("published_date")
        batch_op.drop_column("publisher")
        batch_op.drop_column("media_type")
        batch_op.drop_column("uid")
