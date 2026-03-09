from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.v1.endpoints.auth import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.pallet import Pallet, PalletItem, SimImportBatch, SimPanel


class DummyRole:
    def __init__(self, name: str) -> None:
        self.name = name


class DummyUser:
    def __init__(self, user_id: int, roles: list[str]) -> None:
        self.id = user_id
        self.roles = [DummyRole(role) for role in roles]


@contextmanager
def _client_with_seed_data(user: DummyUser) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
    Base.metadata.create_all(bind=engine)

    seed_db = testing_session_local()
    try:
        pallet = Pallet(pallet_number=7, status="active", max_panels=25, created_by=user.id)
        seed_db.add(pallet)
        seed_db.flush()
        seed_db.add_all(
            [
                PalletItem(
                    pallet_id=pallet.id,
                    serial="SN-ABC-001",
                    slot_index=1,
                    added_by=user.id,
                    added_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                ),
                PalletItem(
                    pallet_id=pallet.id,
                    serial="SN-XYZ-002",
                    slot_index=2,
                    added_by=user.id,
                    added_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
                ),
            ]
        )
        batch = SimImportBatch(source_filename="sim_upload.xlsx", status="completed")
        seed_db.add(batch)
        seed_db.flush()
        seed_db.add_all(
            [
                SimPanel(
                    batch_id=batch.id,
                    serial="SN-ABC-001",
                    test_timestamp=datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc),
                    panel_type="450WT",
                    result="PASS",
                    watts=450.12,
                    voc=49.321,
                    isc=11.234,
                    vmp=40.111,
                    imp=10.456,
                    ff=0.812,
                ),
                SimPanel(
                    batch_id=batch.id,
                    serial="SIM-ONLY-003",
                    test_timestamp=datetime(2026, 3, 2, 13, 0, tzinfo=timezone.utc),
                    panel_type="450WT",
                    result="PASS",
                ),
            ]
        )
        seed_db.commit()
    finally:
        seed_db.close()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_barcode_search_partial_returns_pallet_and_sim_matches() -> None:
    with _client_with_seed_data(DummyUser(user_id=1, roles=["purchasing_manager"])) as client:
        response = client.get("/api/v1/barcodes/search?q=ABC")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 2
        sources = {entry["source"] for entry in payload["results"]}
        assert sources == {"pallet_item", "sim_panel"}


def test_barcode_search_exact_and_pagination() -> None:
    with _client_with_seed_data(DummyUser(user_id=2, roles=["packout_operator"])) as client:
        exact_response = client.get("/api/v1/barcodes/search?q=SN-ABC-001&exact=true")
        assert exact_response.status_code == 200
        exact_payload = exact_response.json()
        assert exact_payload["total"] == 2
        assert all(item["matched_exact"] is True for item in exact_payload["results"])

        paged_response = client.get("/api/v1/barcodes/search?q=SN&limit=1&offset=1&sort=serial&order=asc")
        assert paged_response.status_code == 200
        paged_payload = paged_response.json()
        assert paged_payload["total"] == 3
        assert len(paged_payload["results"]) == 1


def test_barcode_search_includes_sim_electrical_values() -> None:
    with _client_with_seed_data(DummyUser(user_id=3, roles=["admin"])) as client:
        response = client.get("/api/v1/barcodes/search?q=SN-ABC-001&exact=true")
        assert response.status_code == 200
        payload = response.json()
        sim_rows = [row for row in payload["results"] if row["source"] == "sim_panel"]
        assert len(sim_rows) == 1
        sim_row = sim_rows[0]
        assert sim_row["sim_watts"] == 450.12
        assert sim_row["sim_voc"] == 49.321
        assert sim_row["sim_isc"] == 11.234
        assert sim_row["sim_vmp"] == 40.111
        assert sim_row["sim_imp"] == 10.456
        assert sim_row["sim_ff"] == 0.812
