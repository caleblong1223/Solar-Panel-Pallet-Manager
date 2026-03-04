from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SimImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_filename: str
    source_object_key: str | None
    source_checksum: str | None
    status: str
    rows_total: int | None
    rows_imported: int | None
    rows_rejected: int | None
    error_summary: str | None
    imported_by: int | None
    created_at: datetime
    completed_at: datetime | None
