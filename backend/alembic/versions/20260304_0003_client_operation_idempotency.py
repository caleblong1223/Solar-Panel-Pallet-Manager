"""Add client operation idempotency table.

Revision ID: 20260304_0003
Revises: 20260303_0002
Create Date: 2026-03-04 10:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260304_0003"
down_revision: Union[str, Sequence[str], None] = "20260303_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_operations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("operation_type", sa.String(length=100), nullable=True),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("operation_id", name="uq_client_operations_operation_id"),
    )
    op.create_index("ix_client_operations_created_at", "client_operations", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_client_operations_created_at", table_name="client_operations")
    op.drop_table("client_operations")

