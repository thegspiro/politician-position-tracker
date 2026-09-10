"""Add users and record who created or edited each record

Introduces named accounts with roles, and attribution columns on statements
and sources.

Attribution foreign keys use ON DELETE SET NULL: removing an account must not
delete the statements and sources that account produced. Existing rows get
NULL attribution, which reads as "recorded before accounts existed".

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ATTRIBUTED_TABLES = ("statements", "sources")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=12), nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_uid"), "users", ["uid"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    for table in ATTRIBUTED_TABLES:
        # Batch mode so SQLite, which cannot add a foreign key in place,
        # rebuilds the table instead.
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("updated_by_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_created_by", "users", ["created_by_id"], ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_foreign_key(
                f"fk_{table}_updated_by", "users", ["updated_by_id"], ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    for table in reversed(ATTRIBUTED_TABLES):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_updated_by", type_="foreignkey")
            batch_op.drop_constraint(f"fk_{table}_created_by", type_="foreignkey")
            batch_op.drop_column("updated_by_id")
            batch_op.drop_column("created_by_id")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_uid"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
