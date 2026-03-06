from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PalletItemCreate(BaseModel):
    serial: str = Field(min_length=1, max_length=128)
    slot_index: int | None = Field(default=None, ge=1)
    allow_missing_sim_data: bool = False


class PalletCreate(BaseModel):
    template_type: str | None = Field(default=None, max_length=32)
    max_panels: int = Field(default=25, ge=1, le=500)
    customer_id: int | None = None


class PalletUpdate(BaseModel):
    template_type: str | None = Field(default=None, max_length=32)
    customer_id: int | None = None
    max_panels: int | None = Field(default=None, ge=1, le=500)
    pallet_number: int | None = Field(default=None, ge=1, le=1000000)


class PalletItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial: str
    slot_index: int
    added_by: int | None
    added_at: datetime

class PalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pallet_number: int
    status: str
    template_type: str | None
    max_panels: int
    customer_id: int | None
    created_by: int | None
    completed_by: int | None
    created_at: datetime
    completed_at: datetime | None
    deleted_at: datetime | None
    item_count: int
    items: list[PalletItemResponse]

class PalletListResponse(BaseModel):
    total: int
    pallets: list[PalletResponse]


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    event_type: str
    resource_type: str
    resource_id: str | None
    outcome: str
    message: str | None
    metadata_json: dict | None
    created_at: datetime
