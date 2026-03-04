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


def test_simulator_import_all_roles_allowed(monkeypatch) -> None:
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
    for idx, role in enumerate(["purchasing_manager", "packout_operator", "admin"], start=10):
        with _client_for(DummyUser(user_id=idx, roles=[role])) as client:
            response = client.post("/api/v1/simulator/imports", files=csv_file)
            assert response.status_code == 201


def test_export_create_all_roles_allowed() -> None:
    for idx, role in enumerate(["purchasing_manager", "packout_operator", "admin"], start=20):
        with _client_for(DummyUser(user_id=idx, roles=[role])) as client:
            response = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
            assert response.status_code in {200, 201, 409, 404}
