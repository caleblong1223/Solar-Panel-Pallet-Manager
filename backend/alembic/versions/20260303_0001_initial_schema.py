"""initial schema

Revision ID: 20260303_0001
Revises:
Create Date: 2026-03-03 08:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260303_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("business_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("display_name", name="uq_customers_display_name"),
    )

    op.create_table(
        "pallets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pallet_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("template_type", sa.String(length=32), nullable=True),
        sa.Column("max_panels", sa.Integer(), nullable=False, server_default=sa.text("25")),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("completed_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["completed_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "pallet_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pallet_id", sa.BigInteger(), nullable=False),
        sa.Column("serial", sa.String(length=128), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["pallet_id"], ["pallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("pallet_id", "serial", name="uq_pallet_items_pallet_serial"),
        sa.UniqueConstraint("pallet_id", "slot_index", name="uq_pallet_items_pallet_slot"),
    )

    op.create_table(
        "sim_import_batches",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_filename", sa.String(length=512), nullable=False),
        sa.Column("source_object_key", sa.String(length=1024), nullable=True),
        sa.Column("source_checksum", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("rows_total", sa.Integer(), nullable=True),
        sa.Column("rows_imported", sa.Integer(), nullable=True),
        sa.Column("rows_rejected", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("imported_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["imported_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "sim_panels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.BigInteger(), nullable=False),
        sa.Column("serial", sa.String(length=128), nullable=False),
        sa.Column("test_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("panel_type", sa.String(length=64), nullable=True),
        sa.Column("watts", sa.Numeric(10, 2), nullable=True),
        sa.Column("voc", sa.Numeric(10, 3), nullable=True),
        sa.Column("isc", sa.Numeric(10, 3), nullable=True),
        sa.Column("vmp", sa.Numeric(10, 3), nullable=True),
        sa.Column("imp", sa.Numeric(10, 3), nullable=True),
        sa.Column("ff", sa.Numeric(10, 3), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["batch_id"], ["sim_import_batches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("serial", "test_timestamp", name="uq_sim_panels_serial_test_ts"),
    )

    op.create_table(
        "exports",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pallet_id", sa.BigInteger(), nullable=False),
        sa.Column("template_type", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False, server_default=sa.text("'application/pdf'")),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["pallet_id"], ["pallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_pallet_items_serial", "pallet_items", ["serial"], unique=False)
    op.create_index("ix_pallets_completed_at", "pallets", ["completed_at"], unique=False)
    op.create_index("ix_pallets_status", "pallets", ["status"], unique=False)
    op.create_index("ix_pallets_customer_id", "pallets", ["customer_id"], unique=False)
    op.create_index("ix_sim_panels_serial", "sim_panels", ["serial"], unique=False)
    op.create_index("ix_exports_pallet_id", "exports", ["pallet_id"], unique=False)
    op.create_index("ix_exports_created_at", "exports", ["created_at"], unique=False)
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_exports_created_at", table_name="exports")
    op.drop_index("ix_exports_pallet_id", table_name="exports")
    op.drop_index("ix_sim_panels_serial", table_name="sim_panels")
    op.drop_index("ix_pallets_customer_id", table_name="pallets")
    op.drop_index("ix_pallets_status", table_name="pallets")
    op.drop_index("ix_pallets_completed_at", table_name="pallets")
    op.drop_index("ix_pallet_items_serial", table_name="pallet_items")

    op.drop_table("audit_events")
    op.drop_table("exports")
    op.drop_table("sim_panels")
    op.drop_table("sim_import_batches")
    op.drop_table("pallet_items")
    op.drop_table("pallets")
    op.drop_table("customers")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
