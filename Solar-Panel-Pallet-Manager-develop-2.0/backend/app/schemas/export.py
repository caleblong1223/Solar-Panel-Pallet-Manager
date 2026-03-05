from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ExportCreateRequest(BaseModel):
    pallet_id: int
    template_type: str = Field(min_length=1, max_length=64)
    packout_date: date | None = None


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pallet_id: int
    template_type: str
    object_key: str
    file_name: str
    mime_type: str
    size_bytes: int | None
    checksum_sha256: str | None
    created_by: int | None
    created_at: datetime

class ExportListResponse(BaseModel):
    total: int
    exports: list[ExportResponse]


class ExportDownloadUrlResponse(BaseModel):
    export_id: int
    object_key: str
    download_url: str
    expires_in_seconds: int
