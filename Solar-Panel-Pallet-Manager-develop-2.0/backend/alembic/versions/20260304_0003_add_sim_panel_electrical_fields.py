"""Add electrical fields to sim_panels for 2.0 electrical parity.

This stores Pm/Isc/Voc/Ipm/Vpm from simulator imports so exports can
rebuild 1.1-style electrical data per panel.
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
  op.add_column("sim_panels", sa.Column("pm", sa.Float(), nullable=True))
  op.add_column("sim_panels", sa.Column("isc", sa.Float(), nullable=True))
  op.add_column("sim_panels", sa.Column("voc", sa.Float(), nullable=True))
  op.add_column("sim_panels", sa.Column("ipm", sa.Float(), nullable=True))
  op.add_column("sim_panels", sa.Column("vpm", sa.Float(), nullable=True))


def downgrade() -> None:
  op.drop_column("sim_panels", "vpm")
  op.drop_column("sim_panels", "ipm")
  op.drop_column("sim_panels", "voc")
  op.drop_column("sim_panels", "isc")
  op.drop_column("sim_panels", "pm")

