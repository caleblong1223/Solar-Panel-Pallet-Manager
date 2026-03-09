from __future__ import annotations

from datetime import datetime, time, timezone
import mimetypes
from pathlib import Path
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import require_roles
from app.db.session import get_db
from app.models.pallet import AuditEvent, Export, Pallet, SimPanel
from app.models.user import User
from app.schemas.export import (
    ExportCreateRequest,
    ExportDownloadUrlResponse,
    ExportListResponse,
    ExportResponse,
)
from app.services.export_generator import generate_export_pdf_bytes
from app.services.export_workbook import ExportWorkbookError, generate_export_workbook_bytes
from app.services.object_storage import (
    StorageError,
    generate_export_download_url,
    upload_export_artifact,
    upload_export_artifact_at_key,
)

router = APIRouter()

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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


def _xlsx_object_key(export: Export) -> tuple[str, str]:
    pdf_path = PurePosixPath(export.object_key)
    base_dir = str(pdf_path.parent)
    xlsx_name = export.file_name[:-4] + ".xlsx" if export.file_name.lower().endswith(".pdf") else f"{export.file_name}.xlsx"
    return f"{base_dir}/{xlsx_name}", xlsx_name


def _latest_sim_values_for_serials(db: Session, serials: list[str]) -> dict[str, dict[str, float | None]]:
    values: dict[str, dict[str, float | None]] = {}
    for serial in serials:
        latest = (
            db.query(SimPanel)
            .filter(SimPanel.serial == serial)
            .order_by(SimPanel.test_timestamp.desc(), SimPanel.id.desc())
            .first()
        )
        if latest is None:
            continue
        values[serial] = {
            "pm": float(latest.watts) if latest.watts is not None else None,
            "isc": float(latest.isc) if latest.isc is not None else None,
            "voc": float(latest.voc) if latest.voc is not None else None,
            "ipm": float(latest.imp) if latest.imp is not None else None,
            "vpm": float(latest.vmp) if latest.vmp is not None else None,
            "ff": float(latest.ff) if latest.ff is not None else None,
        }
    return values


@router.get("", response_model=ExportListResponse)
def list_exports(
    pallet_id: int | None = None,
    template_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator", "purchasing_manager")),
) -> ExportListResponse:
    del current_user
    query = db.query(Export)
    if pallet_id is not None:
        query = query.filter(Export.pallet_id == pallet_id)
    if template_type is not None:
        query = query.filter(Export.template_type == template_type)
    if created_from is not None:
        query = query.filter(Export.created_at >= created_from)
    if created_to is not None:
        query = query.filter(Export.created_at <= created_to)
    total = query.count()
    rows = query.order_by(Export.created_at.desc(), Export.id.desc()).offset(offset).limit(limit).all()
    return ExportListResponse(total=total, exports=[ExportResponse.model_validate(row) for row in rows])


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
def create_export(
    payload: ExportCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> ExportResponse:
    pallet = (
        db.query(Pallet)
        .options(selectinload(Pallet.items))
        .filter(Pallet.id == payload.pallet_id, Pallet.deleted_at.is_(None))
        .first()
    )
    if pallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pallet not found")
    if pallet.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pallet must be completed before export",
        )
    if not pallet.items:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot export empty pallet")

    effective_packout_date = payload.packout_date or datetime.now(timezone.utc).date()
    export_dt = datetime.combine(effective_packout_date, time.min).replace(tzinfo=timezone.utc)

    duplicate_count = (
        db.query(Export.id)
        .join(Pallet, Pallet.id == Export.pallet_id)
        .filter(
            Export.template_type == payload.template_type,
            Export.packout_date == effective_packout_date,
            Pallet.pallet_number == pallet.pallet_number,
        )
        .count()
    )
    duplicate_index = duplicate_count + 1
    duplicate_suffix = f"-{duplicate_index}" if duplicate_index > 1 else ""

    xlsx_file_name = f"pallet-{payload.template_type}-{effective_packout_date.isoformat()}-{pallet.pallet_number}{duplicate_suffix}.xlsx"
    pdf_file_name = f"pallet-{payload.template_type}-{effective_packout_date.isoformat()}-{pallet.pallet_number}{duplicate_suffix}.pdf"
    workbook_artifact: bytes | None
    try:
        serials = [item.serial.strip().upper() for item in pallet.items if item.serial]
        sim_values_by_serial = _latest_sim_values_for_serials(db, serials)
        workbook_artifact = generate_export_workbook_bytes(
            pallet,
            payload.template_type,
            export_dt=export_dt,
            sim_values_by_serial=sim_values_by_serial,
        )
    except ExportWorkbookError:
        # For unsupported capacities or missing templates, continue with PDF-only export.
        workbook_artifact = None
    pdf_artifact = generate_export_pdf_bytes(pallet, payload.template_type)

    export = Export(
        pallet_id=pallet.id,
        template_type=payload.template_type,
        packout_date=effective_packout_date,
        object_key="pending",
        file_name=pdf_file_name,
        mime_type="application/pdf",
        size_bytes=len(pdf_artifact),
        created_by=current_user.id,
    )
    db.add(export)
    db.flush()
    try:
        if workbook_artifact is not None:
            upload_export_artifact(
                export_id=export.id,
                pallet_id=pallet.id,
                filename=xlsx_file_name,
                content=workbook_artifact,
            )
        object_key, checksum = upload_export_artifact(
            export_id=export.id,
            pallet_id=pallet.id,
            filename=pdf_file_name,
            content=pdf_artifact,
        )
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    export.object_key = object_key
    export.checksum_sha256 = checksum
    db.commit()
    db.refresh(export)
    return ExportResponse.model_validate(export)


@router.get("/{export_id}/download-url", response_model=ExportDownloadUrlResponse)
def get_export_download_url(
    export_id: int,
    format: str = Query(default="pdf", pattern="^(pdf|xlsx)$"),
    expires_in_seconds: int = Query(default=900, ge=60, le=86400),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator", "purchasing_manager")),
) -> ExportDownloadUrlResponse:
    del current_user
    export = db.query(Export).filter(Export.id == export_id).first()
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    try:
        if format == "xlsx":
            object_key, file_name = _xlsx_object_key(export)
        else:
            object_key = export.object_key
            file_name = export.file_name

        url = generate_export_download_url(object_key, expires_in_seconds=expires_in_seconds)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ExportDownloadUrlResponse(
        export_id=export.id,
        format=format,
        file_name=file_name,
        object_key=object_key,
        download_url=url,
        expires_in_seconds=expires_in_seconds,
    )


@router.get("/{export_id}/download")
def download_export(
    export_id: int,
    format: str = Query(default="pdf", pattern="^(pdf|xlsx)$"),
    expires_in_seconds: int = Query(default=900, ge=60, le=86400),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator", "purchasing_manager")),
):
    del current_user
    export = db.query(Export).filter(Export.id == export_id).first()
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    if format == "xlsx":
        object_key, file_name = _xlsx_object_key(export)
    else:
        object_key = export.object_key
        file_name = export.file_name

    local_path = Path(object_key)
    if local_path.exists():
        media_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return FileResponse(
            path=str(local_path),
            media_type=media_type,
            filename=file_name,
        )

    try:
        url = generate_export_download_url(object_key, expires_in_seconds=expires_in_seconds)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post("/{export_id}/replace", response_model=ExportResponse)
def replace_export_workbook(
    export_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator")),
) -> ExportResponse:
    export = db.query(Export).filter(Export.id == export_id).first()
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if not filename.endswith(".xlsx") and content_type != XLSX_MIME_TYPE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .xlsx files are supported")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        object_key, xlsx_name = _xlsx_object_key(export)
        _, checksum = upload_export_artifact_at_key(
            object_key=object_key,
            filename=xlsx_name,
            content=content,
            content_type=XLSX_MIME_TYPE,
        )
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    _record_audit(
        db,
        actor_user_id=current_user.id,
        event_type="export.replaced",
        resource_type="pallet",
        resource_id=str(export.pallet_id),
        outcome="success",
        metadata_json={
            "export_id": export.id,
            "xlsx_object_key": object_key,
            "xlsx_size_bytes": len(content),
            "xlsx_checksum_sha256": checksum,
        },
    )
    db.commit()
    db.refresh(export)
    return ExportResponse.model_validate(export)
