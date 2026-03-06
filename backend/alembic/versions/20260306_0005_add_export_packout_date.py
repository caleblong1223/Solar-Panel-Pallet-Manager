"""Add packout_date to exports for date-scoped export identity."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306_0005"
down_revision: Union[str, Sequence[str], None] = "20260304_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exports", sa.Column("packout_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("exports", "packout_date")
