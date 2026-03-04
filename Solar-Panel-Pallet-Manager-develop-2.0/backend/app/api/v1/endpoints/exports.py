from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import require_roles
from app.db.session import get_db
from app.models.pallet import Export, Pallet
from app.models.user import User
from app.schemas.export import (
    ExportCreateRequest,
    ExportDownloadUrlResponse,
    ExportListResponse,
    ExportResponse,
)
from app.services.export_generator import generate_export_pdf_bytes, write_legacy_excel_export
from app.services.object_storage import (
    StorageError,
    generate_export_download_url,
    upload_export_artifact,
)

router = APIRouter()


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
    if pallet.status not in ("active", "completed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only active or completed pallets can be exported",
        )
    if not pallet.items:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot export empty pallet")

    artifact = generate_export_pdf_bytes(pallet, payload.template_type)
    file_name = f"pallet-{pallet.pallet_number}-export.pdf"

    export = Export(
        pallet_id=pallet.id,
        template_type=payload.template_type,
        object_key="pending",
        file_name=file_name,
        mime_type="application/pdf",
        size_bytes=len(artifact),
        created_by=current_user.id,
    )
    db.add(export)
    db.flush()
    try:
        object_key, checksum = upload_export_artifact(
            export_id=export.id,
            pallet_id=pallet.id,
            filename=file_name,
            content=artifact,
        )
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    export.object_key = object_key
    export.checksum_sha256 = checksum
    db.commit()
    db.refresh(export)

    # Excel parity: write a legacy-style .xlsx file to disk using DB-backed data.
    try:
        write_legacy_excel_export(pallet, payload.template_type, db)
    except Exception:
        # Do not fail the API if Excel export fails.
        pass

    return ExportResponse.model_validate(export)


@router.get("/{export_id}/download-url", response_model=ExportDownloadUrlResponse)
def get_export_download_url(
    export_id: int,
    expires_in_seconds: int = Query(default=900, ge=60, le=86400),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "packout_operator", "purchasing_manager")),
) -> ExportDownloadUrlResponse:
    del current_user
    export = db.query(Export).filter(Export.id == export_id).first()
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    try:
        url = generate_export_download_url(export.object_key, expires_in_seconds=expires_in_seconds)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ExportDownloadUrlResponse(
        export_id=export.id,
        object_key=export.object_key,
        download_url=url,
        expires_in_seconds=expires_in_seconds,
    )
