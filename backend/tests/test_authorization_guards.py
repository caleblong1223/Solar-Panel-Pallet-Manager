from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.v1.endpoints.auth import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app


class DummyRole:
    def __init__(self, name: str) -> None:
        self.name = name


class DummyUser:
    def __init__(self, user_id: int, roles: list[str]) -> None:
        self.id = user_id
        self.roles = [DummyRole(role) for role in roles]


@contextmanager
def _client_for(user: DummyUser) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
    Base.metadata.create_all(bind=engine)

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


def test_all_authenticated_roles_can_access_read_search_endpoints() -> None:
    for idx, role in enumerate(["admin", "packout_operator", "purchasing_manager"], start=1):
        with _client_for(DummyUser(user_id=idx, roles=[role])) as client:
            customers_response = client.get("/api/v1/customers")
            assert customers_response.status_code == 200
            barcode_response = client.get("/api/v1/barcodes/search?q=SN")
            assert barcode_response.status_code == 200


def test_simulator_import_requires_packout_or_admin(monkeypatch) -> None:
    from app.api.v1.endpoints import simulator as simulator_endpoint

    monkeypatch.setattr(
        simulator_endpoint,
        "upload_import_source",
        lambda batch_id, filename, content: (
            f"imports/2026/03/{batch_id}/{filename}",
            "abc123checksum",
        ),
    )
    csv_file = {"file": ("sim.csv", "SerialNo\nABC001\n", "text/csv")}
    with _client_for(DummyUser(user_id=10, roles=["purchasing_manager"])) as client:
        denied = client.post("/api/v1/simulator/imports", files=csv_file)
        assert denied.status_code == 403

    with _client_for(DummyUser(user_id=11, roles=["packout_operator"])) as client:
        allowed = client.post("/api/v1/simulator/imports", files=csv_file)
        assert allowed.status_code == 201

    with _client_for(DummyUser(user_id=12, roles=["admin"])) as client:
        allowed = client.post("/api/v1/simulator/imports", files=csv_file)
        assert allowed.status_code == 201


def test_export_create_requires_packout_or_admin() -> None:
    with _client_for(DummyUser(user_id=20, roles=["purchasing_manager"])) as client:
        denied = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        assert denied.status_code == 403

    with _client_for(DummyUser(user_id=21, roles=["packout_operator"])) as client:
        allowed = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        assert allowed.status_code != 403

    with _client_for(DummyUser(user_id=22, roles=["admin"])) as client:
        allowed = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        assert allowed.status_code != 403
