"""Add address fields to customers for 1.1 A3 parity."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260304_0004"
down_revision: Union[str, Sequence[str], None] = "20260304_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("customers", sa.Column("city", sa.String(length=255), nullable=True))
    op.add_column("customers", sa.Column("state", sa.String(length=64), nullable=True))
    op.add_column("customers", sa.Column("zip_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "zip_code")
    op.drop_column("customers", "state")
    op.drop_column("customers", "city")
    op.drop_column("customers", "address")
