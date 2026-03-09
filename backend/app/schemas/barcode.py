from datetime import datetime

from pydantic import BaseModel


class BarcodeSearchResult(BaseModel):
    source: str
    serial: str
    matched_exact: bool
    pallet_id: int | None = None
    pallet_number: int | None = None
    pallet_status: str | None = None
    slot_index: int | None = None
    customer_id: int | None = None
    sim_panel_id: int | None = None
    sim_batch_id: int | None = None
    sim_test_timestamp: datetime | None = None
    sim_panel_type: str | None = None
    sim_result: str | None = None
    sim_watts: float | None = None
    sim_voc: float | None = None
    sim_isc: float | None = None
    sim_vmp: float | None = None
    sim_imp: float | None = None
    sim_ff: float | None = None
    created_at: datetime | None = None


class BarcodeSearchResponse(BaseModel):
    query: str
    exact: bool
    total: int
    results: list[BarcodeSearchResult]
