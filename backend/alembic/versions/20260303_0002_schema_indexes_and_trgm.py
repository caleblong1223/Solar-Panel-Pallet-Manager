"""Schema and index refinements for Pallet Manager 2.0 v1 data model.

This revision tightens indexes around the concrete query patterns described
in the PRD/TDD and enables trigram-based partial search for barcodes and
customer names.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260303_0002"
down_revision: Union[str, Sequence[str], None] = "20260303_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Ensure pg_trgm extension is available for trigram indexes
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Pallet history and filtering improvements
    op.create_index(
        "ix_pallets_pallet_number",
        "pallets",
        ["pallet_number"],
        unique=False,
    )
    op.create_index(
        "ix_pallets_customer_status_completed",
        "pallets",
        ["customer_id", "status", "completed_at"],
        unique=False,
    )
    op.create_index(
        "ix_pallets_completed_by",
        "pallets",
        ["completed_by"],
        unique=False,
    )

    # Simulator batch and panel access patterns
    op.create_index(
        "ix_sim_import_batches_status_created_at",
        "sim_import_batches",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_sim_import_batches_imported_by",
        "sim_import_batches",
        ["imported_by"],
        unique=False,
    )
    op.create_index(
        "ix_sim_panels_batch_id",
        "sim_panels",
        ["batch_id"],
        unique=False,
    )

    # Export listing convenience index
    op.create_index(
        "ix_exports_pallet_id_created_at",
        "exports",
        ["pallet_id", "created_at"],
        unique=False,
    )

    # Audit querying across multiple dimensions
    op.create_index(
        "ix_audit_events_resource",
        "audit_events",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_actor_created_at",
        "audit_events",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_event_type",
        "audit_events",
        ["event_type"],
        unique=False,
    )

    # Trigram indexes are Postgres-only.
    if is_postgres:
        op.create_index(
            "ix_pallet_items_serial_trgm",
            "pallet_items",
            ["serial"],
            postgresql_using="gin",
            postgresql_ops={"serial": "gin_trgm_ops"},
        )
        op.create_index(
            "ix_sim_panels_serial_trgm",
            "sim_panels",
            ["serial"],
            postgresql_using="gin",
            postgresql_ops={"serial": "gin_trgm_ops"},
        )
        op.create_index(
            "ix_customers_display_name_trgm",
            "customers",
            ["display_name"],
            postgresql_using="gin",
            postgresql_ops={"display_name": "gin_trgm_ops"},
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Drop trigram indexes first
    if is_postgres:
        op.drop_index("ix_customers_display_name_trgm", table_name="customers")
        op.drop_index("ix_sim_panels_serial_trgm", table_name="sim_panels")
        op.drop_index("ix_pallet_items_serial_trgm", table_name="pallet_items")

    # Drop audit indexes
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_resource", table_name="audit_events")

    # Drop export and simulator-related indexes
    op.drop_index("ix_exports_pallet_id_created_at", table_name="exports")
    op.drop_index("ix_sim_panels_batch_id", table_name="sim_panels")
    op.drop_index(
        "ix_sim_import_batches_imported_by",
        table_name="sim_import_batches",
    )
    op.drop_index(
        "ix_sim_import_batches_status_created_at",
        table_name="sim_import_batches",
    )

    # Drop pallet-related indexes
    op.drop_index("ix_pallets_completed_by", table_name="pallets")
    op.drop_index(
        "ix_pallets_customer_status_completed",
        table_name="pallets",
    )
    op.drop_index("ix_pallets_pallet_number", table_name="pallets")

    # Optionally drop pg_trgm extension (safe if unused elsewhere)
    if is_postgres:
        op.execute("DROP EXTENSION IF EXISTS pg_trgm")

