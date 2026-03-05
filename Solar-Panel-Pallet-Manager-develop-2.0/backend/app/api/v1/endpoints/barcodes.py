from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.pallet import Pallet, PalletItem, SimPanel
from app.schemas.barcode import BarcodeSearchResponse, BarcodeSearchResult

router = APIRouter()


@router.get("/search", response_model=BarcodeSearchResponse)
def search_barcodes(
    q: str = Query(min_length=1),
    exact: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    db: Session = Depends(get_db),
) -> BarcodeSearchResponse:
    search_term = q.strip().upper()
    if exact:
        pallet_serial_filter = PalletItem.serial == search_term
        sim_serial_filter = SimPanel.serial == search_term
    else:
        like_term = f"%{search_term}%"
        pallet_serial_filter = PalletItem.serial.ilike(like_term)
        sim_serial_filter = SimPanel.serial.ilike(like_term)

    pallet_rows = (
        db.query(PalletItem, Pallet)
        .join(Pallet, Pallet.id == PalletItem.pallet_id)
        .filter(Pallet.deleted_at.is_(None), pallet_serial_filter)
        .all()
    )
    sim_rows = db.query(SimPanel).filter(sim_serial_filter).all()

    results: list[BarcodeSearchResult] = []
    for item, pallet in pallet_rows:
        results.append(
            BarcodeSearchResult(
                source="pallet_item",
                serial=item.serial,
                matched_exact=item.serial == search_term,
                pallet_id=pallet.id,
                pallet_number=pallet.pallet_number,
                pallet_status=pallet.status,
                slot_index=item.slot_index,
                customer_id=pallet.customer_id,
                created_at=item.added_at,
            )
        )
    for panel in sim_rows:
        results.append(
            BarcodeSearchResult(
                source="sim_panel",
                serial=panel.serial,
                matched_exact=panel.serial == search_term,
                sim_panel_id=panel.id,
                sim_batch_id=panel.batch_id,
                sim_test_timestamp=panel.test_timestamp,
                sim_panel_type=panel.panel_type,
                sim_result=panel.result,
                created_at=panel.created_at,
            )
        )

    reverse = order.lower() != "asc"
    if sort == "serial":
        results.sort(key=lambda x: (x.serial, x.source), reverse=reverse)
    elif sort == "source":
        results.sort(key=lambda x: (x.source, x.serial), reverse=reverse)
    else:
        def _created_key(result: BarcodeSearchResult) -> tuple[datetime, str]:
            timestamp = result.created_at or result.sim_test_timestamp or datetime.min
            return (timestamp, result.serial)

        results.sort(key=_created_key, reverse=reverse)

    total = len(results)
    page_results = results[offset : offset + limit]
    return BarcodeSearchResponse(query=search_term, exact=exact, total=total, results=page_results)
