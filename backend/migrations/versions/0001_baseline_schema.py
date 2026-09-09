"""Baseline schema

Captures the schema that was previously created by Base.metadata.create_all:
politicians, issues, statements, sources and the statement_issues association
table. Existing databases created by create_all are already at this state and
can be stamped rather than upgraded (see the README).

Revision ID: 0001
Revises:
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "politicians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("party", sa.String(length=100), nullable=False),
        sa.Column("office", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_politicians_id"), "politicians", ["id"], unique=False)

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_issues_id"), "issues", ["id"], unique=False)

    op.create_table(
        "statements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("politician_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=False),
        sa.Column("post_url", sa.String(length=1000), nullable=False),
        sa.Column("post_platform", sa.String(length=50), nullable=False),
        sa.Column("post_content", sa.Text(), nullable=True),
        sa.Column("screenshot_url", sa.String(length=1000), nullable=True),
        sa.Column("post_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["politician_id"], ["politicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_statements_id"), "statements", ["id"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("statement_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["statement_id"], ["statements.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sources_id"), "sources", ["id"], unique=False)

    op.create_table(
        "statement_issues",
        sa.Column("statement_id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["statement_id"], ["statements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("statement_id", "issue_id"),
    )


def downgrade() -> None:
    op.drop_table("statement_issues")
    op.drop_index(op.f("ix_sources_id"), table_name="sources")
    op.drop_table("sources")
    op.drop_index(op.f("ix_statements_id"), table_name="statements")
    op.drop_table("statements")
    op.drop_index(op.f("ix_issues_id"), table_name="issues")
    op.drop_table("issues")
    op.drop_index(op.f("ix_politicians_id"), table_name="politicians")
    op.drop_table("politicians")
