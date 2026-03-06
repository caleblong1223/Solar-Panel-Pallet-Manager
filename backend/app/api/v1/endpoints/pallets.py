from __future__ import annotations

from datetime import datetime, timezone
import random

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import require_roles
from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.pallet import AuditEvent, ClientOperation, Customer, Export, Pallet, PalletItem, SimImportBatch, SimPanel
from app.models.user import User
from app.schemas.pallet import (
    AuditEventResponse,
    PalletCreate,
    PalletItemCreate,
    PalletListResponse,
    PalletResponse,
    PalletUpdate,
)

router = APIRouter()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_serial(serial: str) -> str:
    normalized = serial.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "SERIAL_EMPTY", "message": "Serial cannot be empty"},
        )
    return normalized


def _random_sim_values(panel_type: str | None) -> dict[str, float]:
    pm_ranges: dict[str, tuple[float, float]] = {
        "200WT": (195.0, 206.0),
        "220WT": (214.0, 227.0),
        "220M6": (214.0, 227.0),
        "330WT": (320.0, 340.0),
        "450WT": (439.0, 463.5),
        "450BT": (439.0, 463.5),
    }

    normalized = (panel_type or "").strip().upper()
    pm_min, pm_max = pm_ranges.get(normalized, (350.0, 450.0))

    # Match 1.1 logic with non-deterministic Pm.
    pm = random.uniform(pm_min, pm_max)
    voc = random.uniform(38.0, 50.0)
    vmp = voc * random.uniform(0.75, 0.85)
    imp = pm / vmp if vmp > 0 else random.uniform(8.0, 12.0)
    isc = imp / random.uniform(0.90, 0.98)
    ff = (vmp * imp) / (voc * isc) if voc > 0 and isc > 0 else 0.0

    return {
        "watts": round(pm, 2),
        "voc": round(voc, 3),
        "isc": round(isc, 3),
        "vmp": round(vmp, 3),
        "imp": round(imp, 3),
        "ff": round(ff, 3),
    }


def _error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message})


def _read_client_operation_response(db: Session, operation_id: str | None) -> dict | None:
    if not operation_id:
        return None
    row = db.query(ClientOperation).filter(ClientOperation.operation_id == operation_id).first()
    return row.response_json if row is not None else None


def _record_client_operation_response(
    db: Session,
    *,
    operation_id: str | None,
    operation_type: str,
    response_json: dict | None,
) -> None:
    if not operation_id:
        return
    existing = db.query(ClientOperation.id).filter(ClientOperation.operation_id == operation_id).first()
    if existing is not None:
        return
    db.add(
        ClientOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            response_json=response_json,
        )
    )


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
        raise _error(status.HTTP_404_NOT_FOUND, "PALLET_NOT_FOUND", "Pallet not found")
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
    x_client_operation_id: str | None = Header(default=None),
) -> PalletResponse:
    replayed = _read_client_operation_response(db, x_client_operation_id)
    if replayed is not None:
        return PalletResponse.model_validate(replayed)

    if payload.customer_id is not None:
        customer_exists = db.query(Customer.id).filter(Customer.id == payload.customer_id).first()
        if customer_exists is None:
            raise _error(status.HTTP_404_NOT_FOUND, "CUSTOMER_NOT_FOUND", "Customer not found")

    max_exported_number = (
        db.query(func.max(Pallet.pallet_number))
        .join(Export, Export.pallet_id == Pallet.id)
        .filter(
            Pallet.deleted_at.is_(None),
            Pallet.template_type == payload.template_type,
        )
        .scalar()
    )
    pallet_number = (max_exported_number or 0) + 1
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
    response = _to_pallet_response(pallet)
    _record_client_operation_response(
        db,
        operation_id=x_client_operation_id,
        operation_type="pallet.create",
        response_json=response.model_dump(mode="json"),
    )
    db.commit()
    return response


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
        raise _error(status.HTTP_409_CONFLICT, "PALLET_NOT_ACTIVE", "Only active pallets can be updated")

    if payload.customer_id is not None:
        customer_exists = db.query(Customer.id).filter(Customer.id == payload.customer_id).first()
        if customer_exists is None:
            raise _error(status.HTTP_404_NOT_FOUND, "CUSTOMER_NOT_FOUND", "Customer not found")

    changes: dict[str, object] = {}
    target_template_type = payload.template_type if payload.template_type is not None else pallet.template_type
    if payload.template_type is not None and payload.template_type != pallet.template_type:
        template_conflict = (
            db.query(Pallet.id)
            .filter(
                Pallet.deleted_at.is_(None),
                Pallet.id != pallet.id,
                Pallet.pallet_number == pallet.pallet_number,
                Pallet.template_type == payload.template_type,
            )
            .first()
        )
        if template_conflict is not None:
            raise _error(
                status.HTTP_409_CONFLICT,
                "PALLET_NUMBER_ALREADY_EXISTS",
                "Pallet number already exists for this panel type",
            )
        changes["template_type"] = {"old": pallet.template_type, "new": payload.template_type}
        pallet.template_type = payload.template_type
    if payload.customer_id is not None and payload.customer_id != pallet.customer_id:
        changes["customer_id"] = {"old": pallet.customer_id, "new": payload.customer_id}
        pallet.customer_id = payload.customer_id
    if payload.max_panels is not None:
        if payload.max_panels < len(pallet.items):
            raise _error(
                status.HTTP_409_CONFLICT,
                "PALLET_CAPACITY_BELOW_ITEM_COUNT",
                "max_panels cannot be less than current item count",
            )
        if payload.max_panels != pallet.max_panels:
            changes["max_panels"] = {"old": pallet.max_panels, "new": payload.max_panels}
            pallet.max_panels = payload.max_panels
    if payload.pallet_number is not None and payload.pallet_number != pallet.pallet_number:
        number_taken = (
            db.query(Pallet.id)
            .filter(
                Pallet.deleted_at.is_(None),
                Pallet.id != pallet.id,
                Pallet.pallet_number == payload.pallet_number,
                Pallet.template_type == target_template_type,
            )
            .first()
        )
        if number_taken is not None:
            raise _error(
                status.HTTP_409_CONFLICT,
                "PALLET_NUMBER_ALREADY_EXISTS",
                "Pallet number already exists for this panel type",
            )
        changes["pallet_number"] = {"old": pallet.pallet_number, "new": payload.pallet_number}
        pallet.pallet_number = payload.pallet_number

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
    x_client_operation_id: str | None = Header(default=None),
) -> PalletResponse:
    replayed = _read_client_operation_response(db, x_client_operation_id)
    if replayed is not None:
        return PalletResponse.model_validate(replayed)

    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise _error(status.HTTP_409_CONFLICT, "PALLET_NOT_ACTIVE", "Cannot add serials to non-active pallet")
    if len(pallet.items) >= pallet.max_panels:
        raise _error(status.HTTP_409_CONFLICT, "PALLET_AT_CAPACITY", "Pallet is at capacity")

    serial = _normalize_serial(payload.serial)
    sim_row = (
        db.query(SimPanel.id)
        .filter(SimPanel.serial == serial)
        .order_by(SimPanel.test_timestamp.desc(), SimPanel.id.desc())
        .first()
    )
    if sim_row is None and not payload.allow_missing_sim_data:
        raise _error(
            status.HTTP_409_CONFLICT,
            "SIM_DATA_REQUIRED",
            "No sun simulator data found for this serial. Confirm to add with generated fallback values.",
        )
    if sim_row is None and payload.allow_missing_sim_data:
        now = _now_utc()
        fallback_batch = (
            db.query(SimImportBatch)
            .filter(
                SimImportBatch.source_filename == "manual-fallback-generated",
                SimImportBatch.status == "completed",
            )
            .order_by(SimImportBatch.id.desc())
            .first()
        )
        if fallback_batch is None:
            fallback_batch = SimImportBatch(
                source_filename="manual-fallback-generated",
                status="completed",
                rows_total=0,
                rows_imported=0,
                rows_rejected=0,
                imported_by=current_user.id,
                created_at=now,
                completed_at=now,
            )
            db.add(fallback_batch)
            db.flush()

        generated = _random_sim_values(pallet.template_type)
        db.add(
            SimPanel(
                batch_id=fallback_batch.id,
                serial=serial,
                test_timestamp=now,
                panel_type=pallet.template_type,
                watts=generated["watts"],
                voc=generated["voc"],
                isc=generated["isc"],
                vmp=generated["vmp"],
                imp=generated["imp"],
                ff=generated["ff"],
                result="GENERATED",
                raw_payload={"generated": True, "source": "manual_fallback"},
                created_at=now,
            )
        )
        fallback_batch.rows_total = (fallback_batch.rows_total or 0) + 1
        fallback_batch.rows_imported = (fallback_batch.rows_imported or 0) + 1

    same_pallet = next((item for item in pallet.items if item.serial == serial), None)
    if same_pallet is not None:
        raise _error(status.HTTP_409_CONFLICT, "SERIAL_ALREADY_ON_PALLET", "Serial already on this pallet")

    in_other_pallet = (
        db.query(PalletItem.id)
        .join(Pallet, Pallet.id == PalletItem.pallet_id)
        .filter(Pallet.deleted_at.is_(None), PalletItem.serial == serial, PalletItem.pallet_id != pallet.id)
        .first()
    )
    if in_other_pallet is not None:
        raise _error(
            status.HTTP_409_CONFLICT,
            "SERIAL_ALREADY_ASSIGNED_ELSEWHERE",
            "Serial already assigned to another pallet",
        )

    occupied_slots = {item.slot_index for item in pallet.items}
    if payload.slot_index is not None:
        if payload.slot_index in occupied_slots:
            raise _error(status.HTTP_409_CONFLICT, "SLOT_OCCUPIED", "Requested slot is already occupied")
        if payload.slot_index > pallet.max_panels:
            raise _error(
                status.HTTP_409_CONFLICT,
                "SLOT_EXCEEDS_CAPACITY",
                "Requested slot exceeds pallet capacity",
            )
        slot_index = payload.slot_index
    else:
        slot_index = 1
        while slot_index in occupied_slots:
            slot_index += 1
        if slot_index > pallet.max_panels:
            raise _error(status.HTTP_409_CONFLICT, "NO_SLOTS_REMAINING", "No remaining slots on pallet")

    db.add(
        PalletItem(
            pallet_id=pallet.id,
            serial=serial,
            slot_index=slot_index,
            added_by=current_user.id,
        )
    )
    db.flush()
    db.expire(pallet, ["items"])
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.item_added",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json={"serial": serial, "slot_index": slot_index},
    )
    response = _to_pallet_response(pallet)
    _record_client_operation_response(
        db,
        operation_id=x_client_operation_id,
        operation_type="pallet.item_add",
        response_json=response.model_dump(mode="json"),
    )
    db.commit()
    return response


@router.delete("/{pallet_id}/items/{item_id}", response_model=PalletResponse)
def remove_pallet_item(
    pallet_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
    x_client_operation_id: str | None = Header(default=None),
) -> PalletResponse:
    replayed = _read_client_operation_response(db, x_client_operation_id)
    if replayed is not None:
        return PalletResponse.model_validate(replayed)

    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise _error(status.HTTP_409_CONFLICT, "PALLET_NOT_ACTIVE", "Cannot remove serials from non-active pallet")

    item = (
        db.query(PalletItem)
        .filter(PalletItem.id == item_id, PalletItem.pallet_id == pallet.id)
        .first()
    )
    if item is None:
        raise _error(status.HTTP_404_NOT_FOUND, "PALLET_ITEM_NOT_FOUND", "Pallet item not found")
    serial = item.serial
    slot_index = item.slot_index
    db.delete(item)
    db.flush()
    db.expire(pallet, ["items"])
    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="pallet.item_removed",
        resource_type="pallet",
        resource_id=str(pallet.id),
        outcome="success",
        metadata_json={"serial": serial, "slot_index": slot_index, "item_id": item_id},
    )
    response = _to_pallet_response(pallet)
    _record_client_operation_response(
        db,
        operation_id=x_client_operation_id,
        operation_type="pallet.item_remove",
        response_json=response.model_dump(mode="json"),
    )
    db.commit()
    return response


@router.post("/{pallet_id}/complete", response_model=PalletResponse)
def complete_pallet(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
    x_client_operation_id: str | None = Header(default=None),
) -> PalletResponse:
    replayed = _read_client_operation_response(db, x_client_operation_id)
    if replayed is not None:
        return PalletResponse.model_validate(replayed)

    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "active":
        raise _error(status.HTTP_409_CONFLICT, "PALLET_NOT_ACTIVE", "Only active pallets can be completed")
    if len(pallet.items) != pallet.max_panels:
        raise _error(status.HTTP_409_CONFLICT, "PALLET_NOT_FULL", "Pallet must be full before completion")
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
    response = _to_pallet_response(pallet)
    _record_client_operation_response(
        db,
        operation_id=x_client_operation_id,
        operation_type="pallet.complete",
        response_json=response.model_dump(mode="json"),
    )
    db.commit()
    return response


@router.post("/{pallet_id}/reset", response_model=PalletResponse)
def reset_pallet(
    pallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
) -> PalletResponse:
    pallet = _get_pallet_or_404(db, pallet_id)
    if pallet.status != "completed":
        raise _error(status.HTTP_409_CONFLICT, "PALLET_NOT_COMPLETED", "Only completed pallets can be reset")
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
