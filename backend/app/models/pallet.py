from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )


class Pallet(Base):
    __tablename__ = "pallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pallet_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    template_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_panels: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    customer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["PalletItem"]] = relationship(
        "PalletItem",
        back_populates="pallet",
        cascade="all, delete-orphan",
        order_by="PalletItem.slot_index",
    )


class PalletItem(Base):
    __tablename__ = "pallet_items"
    __table_args__ = (
        UniqueConstraint("pallet_id", "serial", name="uq_pallet_items_pallet_serial"),
        UniqueConstraint("pallet_id", "slot_index", name="uq_pallet_items_pallet_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pallets.id", ondelete="CASCADE"),
        nullable=False,
    )
    serial: Mapped[str] = mapped_column(String(128), nullable=False)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    added_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    pallet: Mapped[Pallet] = relationship("Pallet", back_populates="items")


class SimImportBatch(Base):
    __tablename__ = "sim_import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    rows_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_rejected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    panels: Mapped[list["SimPanel"]] = relationship(
        "SimPanel",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class SimPanel(Base):
    __tablename__ = "sim_panels"
    __table_args__ = (
        UniqueConstraint("serial", "test_timestamp", name="uq_sim_panels_serial_test_ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sim_import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    serial: Mapped[str] = mapped_column(String(128), nullable=False)
    test_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    panel_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    watts: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    voc: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    isc: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    vmp: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    imp: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    ff: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    batch: Mapped[SimImportBatch] = relationship("SimImportBatch", back_populates="panels")


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pallets.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    packout_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )


class ClientOperation(Base):
    __tablename__ = "client_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    operation_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
