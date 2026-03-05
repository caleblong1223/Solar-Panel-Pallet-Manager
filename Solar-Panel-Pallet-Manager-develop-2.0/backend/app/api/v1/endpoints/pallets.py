from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import require_roles
from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.pallet import AuditEvent, Customer, Pallet, PalletItem, SimPanel
from app.models.user import User
from app.schemas.pallet import (
    AuditEventResponse,
    PalletCreate,
    PalletItemCreate,
    PalletListResponse,
    PalletResponse,
    PalletUpdate,
)
from app.services.export_generator import generate_multi_pallets_pdf_bytes, write_legacy_excel_export

router = APIRouter()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_serial(serial: str) -> str:
    normalized = serial.strip().upper()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Serial cannot be empty")
    return normalized


def _record_audit(
    db: Session,
    *,
    actor_user_id: int | None,
    event_type: str,
    resource_type: str,
    resource_id: str | None,
    outcome: str,
    message: str | None = None,
    metadata_json: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            message=message,
            metadata_json=metadata_json,
        )
    )


def _get_pallet_or_404(db: Session, pallet_id: int) -> Pallet:
    pallet = (
        db.query(Pallet)
        .options(selectinload(Pallet.items))
        .filter(Pallet.id == pallet_id, Pallet.deleted_at.is_(None))
        .first()
    )
    if pallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pallet not found")
    return pallet


def _to_pallet_response(pallet: Pallet) -> PalletResponse:
    return PalletResponse(
        id=pallet.id,
        pallet_number=pallet.pallet_number,
        status=pallet.status,
        template_type=pallet.template_type,
        max_panels=pallet.max_panels,
        customer_id=pallet.customer_id,
        created_by=pallet.created_by,
        completed_by=pallet.completed_by,
        created_at=pallet.created_at,
        completed_at=pallet.completed_at,
        deleted_at=pallet.deleted_at,
        item_count=len(pallet.items),
        items=pallet.items,
    )


@router.get("", response_model=PalletListResponse)
def list_pallets(
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    completed_from: datetime | None = None,
    completed_to: datetime | None = None,
    include_deleted: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PalletListResponse:
    del current_user
    base_query = db.query(Pallet).options(selectinload(Pallet.items))
    if not include_deleted:
        base_query = base_query.filter(Pallet.deleted_at.is_(None))
    if status_filter:
        base_query = base_query.filter(Pallet.status == status_filter)
    if customer_id is not None:
        base_query = base_query.filter(Pallet.customer_id == customer_id)
    if created_from is not None:
        base_query = base_query.filter(Pallet.created_at >= created_from)
    if created_to is not None:
        base_query = base_query.filter(Pallet.created_at <= created_to)
    if completed_from is not None:
        base_query = base_query.filter(Pallet.completed_at >= completed_from)
    if completed_to is not None:
        base_query = base_query.filter(Pallet.completed_at <= completed_to)

    total = base_query.count()
    pallets = (
        base_query.order_by(Pallet.created_at.desc(), Pallet.id.desc()).offset(offset).limit(limit).all()
    )
    return PalletListResponse(total=total, pallets=[_to_pallet_response(p) for p in pallets])


@router.post("", response_model=PalletResponse, status_code=status.HTTP_201_CREATED)
def create_pallet(
    payload: PalletCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> PalletResponse:
    if payload.customer_id is not None:
        customer_exists = db.query(Customer.id).filter(Customer.id == payload.customer_id).first()
        if customer_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    max_number = db.query(func.max(Pallet.pallet_number)).filter(Pallet.deleted_at.is_(None)).scalar()
    pallet_number = (max_number or 0) + 1
    pallet = Pallet(
        pallet_number=pallet_number,
        status="active",
        template_type=payload.template_type,
        max_panels=payload.max_panels,
        customer_id=payload.customer_id,
        created_by=current_user.id,
    )
    db.add(pallet)
    db.flush()
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.created",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json={"pallet_number": pallet.pallet_number},
    )
    db.commit()
    db.refresh(pallet)
    return _to_pallet_response(pallet)


@router.get("/{pallet_id}", response_model=PalletResponse)
def get_pallet(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PalletResponse:
    del current_user
    pallet = _get_pallet_or_404(db, pallet_id)
    return _to_pallet_response(pallet)


@router.patch("/{pallet_id}", response_model=PalletResponse)
def update_pallet(
    pallet_id: int,
    payload: PalletUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> PalletResponse:
    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active pallets can be updated")

    if payload.customer_id is not None:
        customer_exists = db.query(Customer.id).filter(Customer.id == payload.customer_id).first()
        if customer_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    changes: dict[str, object] = {}
    if payload.template_type is not None and payload.template_type != pallet.template_type:
        changes["template_type"] = {"old": pallet.template_type, "new": payload.template_type}
        pallet.template_type = payload.template_type
    if payload.customer_id is not None and payload.customer_id != pallet.customer_id:
        changes["customer_id"] = {"old": pallet.customer_id, "new": payload.customer_id}
        pallet.customer_id = payload.customer_id
    if payload.max_panels is not None:
        if payload.max_panels < len(pallet.items):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="max_panels cannot be less than current item count",
            )
        if payload.max_panels != pallet.max_panels:
            changes["max_panels"] = {"old": pallet.max_panels, "new": payload.max_panels}
            pallet.max_panels = payload.max_panels

    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.updated",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json=changes,
    )
    db.commit()
    db.refresh(pallet)
    return _to_pallet_response(pallet)


@router.post("/{pallet_id}/items", response_model=PalletResponse)
def add_pallet_item(
    pallet_id: int,
    payload: PalletItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> PalletResponse:
    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot add serials to non-active pallet")
    if len(pallet.items) >= pallet.max_panels:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pallet is at capacity")

    serial = _normalize_serial(payload.serial)
    same_pallet = next((item for item in pallet.items if item.serial == serial), None)
    if same_pallet is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Serial already on this pallet")

    in_other_pallet = (
        db.query(PalletItem.id)
        .join(Pallet, Pallet.id == PalletItem.pallet_id)
        .filter(Pallet.deleted_at.is_(None), PalletItem.serial == serial, PalletItem.pallet_id != pallet.id)
        .first()
    )
    if in_other_pallet is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Serial already assigned to another pallet")

    # Require that the serial exists in imported simulator data before it can be added to any pallet.
    exists_in_sim_data = db.query(SimPanel.id).filter(SimPanel.serial == serial).first()
    if exists_in_sim_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serial not found in simulator data. Import latest simulator file before scanning this panel.",
        )

    occupied_slots = {item.slot_index for item in pallet.items}
    if payload.slot_index is not None:
        if payload.slot_index in occupied_slots:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested slot is already occupied")
        if payload.slot_index > pallet.max_panels:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested slot exceeds pallet capacity")
        slot_index = payload.slot_index
    else:
        slot_index = 1
        while slot_index in occupied_slots:
            slot_index += 1
        if slot_index > pallet.max_panels:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No remaining slots on pallet")

    db.add(
        PalletItem(
            pallet_id=pallet.id,
            serial=serial,
            slot_index=slot_index,
            added_by=current_user.id,
        )
    )
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.item_added",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json={"serial": serial, "slot_index": slot_index},
    )
    db.commit()
    pallet = _get_pallet_or_404(db, pallet_id)
    return _to_pallet_response(pallet)


@router.delete("/{pallet_id}/items/{item_id}", response_model=PalletResponse)
def remove_pallet_item(
    pallet_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> PalletResponse:
    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove serials from non-active pallet",
        )

    item = (
        db.query(PalletItem)
        .filter(PalletItem.id == item_id, PalletItem.pallet_id == pallet.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pallet item not found")
    serial = item.serial
    slot_index = item.slot_index
    db.delete(item)
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.item_removed",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json={"serial": serial, "slot_index": slot_index, "item_id": item_id},
    )
    db.commit()
    pallet = _get_pallet_or_404(db, pallet_id)
    return _to_pallet_response(pallet)


@router.post("/{pallet_id}/complete", response_model=PalletResponse)
def complete_pallet(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> PalletResponse:
    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active pallets can be completed")
    if len(pallet.items) != pallet.max_panels:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pallet must be full before completion",
        )
    pallet.status = "completed"
    pallet.completed_at = _now_utc()
    pallet.completed_by = current_user.id
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.completed",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json={"item_count": len(pallet.items)},
    )
    db.commit()
    db.refresh(pallet)
    return _to_pallet_response(pallet)


@router.post("/{pallet_id}/reset", response_model=PalletResponse)
def reset_pallet(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
) -> PalletResponse:
    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only completed pallets can be reset")
    pallet.status = "active"
    pallet.completed_at = None
    pallet.completed_by = None
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.reset",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
    )
    db.commit()
    db.refresh(pallet)
    return _to_pallet_response(pallet)


@router.delete(
    "/{pallet_id}",
    status_code=status.HTTP_200_OK,
)
def delete_pallet(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
) -> None:
    pallet = _get_pallet_or_404(db, pallet_id)
    pallet.status = "deleted"
    pallet.deleted_at = _now_utc()
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.deleted",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
    )
    db.commit()


@router.get("/{pallet_id}/history", response_model=list[AuditEventResponse])
def pallet_history(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditEventResponse]:
    del current_user
    _get_pallet_or_404(db, pallet_id)
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.resource_type == "pallet", AuditEvent.resource_id == str(pallet_id))
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .all()
    )
    return [AuditEventResponse.model_validate(event) for event in events]


@router.get("/{pallet_id}/excel")
def download_pallet_excel(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> FileResponse:
    """Generate (or regenerate) and download a 1.1-style Excel pallet sheet for a pallet."""
    del current_user
    pallet = _get_pallet_or_404(db, pallet_id)
    template_type = pallet.template_type or "200WT"
    path = write_legacy_excel_export(pallet, template_type, db)
    if path is None or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Excel export not available for this pallet",
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.post("/combined-pdf")
def combined_pallets_pdf(
    pallet_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> Response:
    """Generate a lightweight combined PDF for one or more pallets, optimized for printing."""
    del current_user
    if not pallet_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pallet_ids is required")
    pallets: Sequence[Pallet] = (
        db.query(Pallet)
        .options(selectinload(Pallet.items))
        .filter(Pallet.id.in_(pallet_ids), Pallet.deleted_at.is_(None))
        .order_by(Pallet.pallet_number.asc())
        .all()
    )
    if not pallets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pallets found for requested IDs")
    pdf_bytes = generate_multi_pallets_pdf_bytes(pallets)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="pallets-combined.pdf"'},
    )
