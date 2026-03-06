from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.deps import require_roles
from app.db.session import get_db
from app.models.pallet import SimImportBatch, SimPanel
from app.models.user import User
from app.schemas.simulator import SimImportBatchResponse
from app.services.object_storage import StorageError, upload_import_source
from app.services.simulator_parser import RejectedSimRow, parse_simulator_file

router = APIRouter()


def _reject_rows_summary(rows: list[RejectedSimRow], max_items: int = 20) -> str | None:
    if not rows:
        return None
    payload = [
        {"row_number": row.row_number, "reason": row.reason, "raw_serial": row.raw_serial}
        for row in rows[:max_items]
    ]
    return json.dumps(payload)


@router.post("/imports", response_model=SimImportBatchResponse, status_code=status.HTTP_201_CREATED)
def import_simulator_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> SimImportBatchResponse:
    filename = file.filename or "upload"
    batch = SimImportBatch(
        source_filename=filename,
        status="processing",
        imported_by=current_user.id,
        rows_total=0,
        rows_imported=0,
        rows_rejected=0,
    )
    db.add(batch)
    db.flush()

    try:
        content = file.file.read()
        object_key, checksum = upload_import_source(batch.id, filename, content)
        batch.source_object_key = object_key
        batch.source_checksum = checksum
        parse_result = parse_simulator_file(filename, content)

        now = datetime.now(timezone.utc)
        imported = 0
        rejected_rows: list[RejectedSimRow] = list(parse_result.rejected_rows)
        seen_keys: set[tuple[str, datetime]] = set()
        for parsed_row in parse_result.accepted_rows:
            panel_ts = parsed_row.test_timestamp or now
            dedupe_key = (parsed_row.serial, panel_ts)
            if dedupe_key in seen_keys:
                rejected_rows.append(
                    RejectedSimRow(
                        row_number=parsed_row.row_number,
                        reason="Duplicate serial in batch",
                        raw_serial=parsed_row.serial,
                    )
                )
                continue
            seen_keys.add(dedupe_key)
            exists = (
                db.query(SimPanel.id)
                .filter(
                    SimPanel.batch_id == batch.id,
                    SimPanel.serial == parsed_row.serial,
                    SimPanel.test_timestamp == panel_ts,
                )
                .first()
            )
            if exists is not None:
                rejected_rows.append(
                    RejectedSimRow(
                        row_number=parsed_row.row_number,
                        reason="Duplicate serial in batch",
                        raw_serial=parsed_row.serial,
                    )
                )
                continue
            db.add(
                SimPanel(
                    batch_id=batch.id,
                    serial=parsed_row.serial,
                    test_timestamp=panel_ts,
                    panel_type=parsed_row.panel_type,
                    watts=parsed_row.watts,
                    voc=parsed_row.voc,
                    isc=parsed_row.isc,
                    vmp=parsed_row.vmp,
                    imp=parsed_row.imp,
                    ff=parsed_row.ff,
                    result=parsed_row.result,
                    raw_payload=None,
                    created_at=now,
                )
            )
            imported += 1

        batch.status = "completed"
        batch.rows_total = parse_result.rows_total
        batch.rows_imported = imported
        batch.rows_rejected = len(rejected_rows)
        batch.error_summary = _reject_rows_summary(rejected_rows)
        batch.completed_at = now
        db.commit()
        db.refresh(batch)
        return SimImportBatchResponse.model_validate(batch)
    except StorageError as exc:
        batch.status = "failed"
        batch.error_summary = str(exc)
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=batch.error_summary) from exc
    except Exception as exc:
        batch.status = "failed"
        batch.error_summary = str(exc)
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=batch.error_summary) from exc


@router.get("/imports/{batch_id}", response_model=SimImportBatchResponse)
def get_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator", "purchasing_manager")),
) -> SimImportBatchResponse:
    del current_user
    batch = db.query(SimImportBatch).filter(SimImportBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found")
    return SimImportBatchResponse.model_validate(batch)
