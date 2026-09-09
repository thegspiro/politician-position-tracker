"""Add citation fields to sources

Adds the data a Chicago-style citation needs beyond a title and URL: structured
authors, the container title (the newspaper, site or journal the source sits
in), edition, and the fields legislative and legal material requires.

All columns are nullable, so existing sources and older JSON backups remain
valid; a source with none of them set still formats, just with less detail.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Nullable with no server default: MySQL before 8.0.13 rejects DEFAULT on a
# JSON column, and a nullable column needs no backfill.
CITATION_COLUMNS = (
    ("authors", sa.JSON()),
    ("container_title", sa.String(length=300)),
    ("edition", sa.String(length=100)),
    ("document_type", sa.String(length=40)),
    ("bill_number", sa.String(length=50)),
    ("congress_number", sa.Integer()),
    ("congress_session", sa.String(length=20)),
    ("committee", sa.String(length=300)),
    ("report_number", sa.String(length=50)),
)


def upgrade() -> None:
    for name, column_type in CITATION_COLUMNS:
        op.add_column("sources", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sources") as batch_op:
        for name, _ in reversed(CITATION_COLUMNS):
            batch_op.drop_column(name)
