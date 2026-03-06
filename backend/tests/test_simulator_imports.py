from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
import json

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


def test_simulator_import_csv_creates_completed_batch_and_fetchable_status(monkeypatch) -> None:
    csv_content = "SerialNo,Watts\nSIM100,450\nSIM101,450\n"
    with _client_for(DummyUser(user_id=1, roles=["packout_operator"])) as client:
        from app.api.v1.endpoints import simulator as simulator_endpoint

        monkeypatch.setattr(
            simulator_endpoint,
            "upload_import_source",
            lambda batch_id, filename, content: (
                f"imports/2026/03/{batch_id}/{filename}",
                "abc123checksum",
            ),
        )
        response = client.post(
            "/api/v1/simulator/imports/anonymous",
            files={"file": ("sim.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["source_object_key"].endswith("/sim.csv")
        assert payload["source_checksum"] == "abc123checksum"
        assert payload["status"] == "completed"
        assert payload["rows_total"] == 2
        assert payload["rows_imported"] == 2
        assert payload["rows_rejected"] == 0
        batch_id = payload["id"]

        get_response = client.get(f"/api/v1/simulator/imports/{batch_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == batch_id


def test_simulator_import_rejects_unsupported_file_types(monkeypatch) -> None:
    with _client_for(DummyUser(user_id=2, roles=["admin"])) as client:
        from app.api.v1.endpoints import simulator as simulator_endpoint

        monkeypatch.setattr(
            simulator_endpoint,
            "upload_import_source",
            lambda batch_id, filename, content: (
                f"imports/2026/03/{batch_id}/{filename}",
                "abc123checksum",
            ),
        )
        response = client.post(
            "/api/v1/simulator/imports/anonymous",
            files={"file": ("sim.txt", "SerialNo\nX", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


def test_simulator_import_captures_row_level_rejections(monkeypatch) -> None:
    csv_content = "SerialNo,Result\n ,PASS\nDUP100,FAIL\nDUP100,PASS\n"
    with _client_for(DummyUser(user_id=3, roles=["packout_operator"])) as client:
        from app.api.v1.endpoints import simulator as simulator_endpoint

        monkeypatch.setattr(
            simulator_endpoint,
            "upload_import_source",
            lambda batch_id, filename, content: (
                f"imports/2026/03/{batch_id}/{filename}",
                "abc123checksum",
            ),
        )
        response = client.post(
            "/api/v1/simulator/imports/anonymous",
            files={"file": ("sim.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["rows_total"] == 3
        assert payload["rows_imported"] == 1
        assert payload["rows_rejected"] == 2
        assert payload["error_summary"] is not None
        rejections = json.loads(payload["error_summary"])
        reasons = {entry["reason"] for entry in rejections}
        assert "Empty serial" in reasons
        assert "Duplicate serial in batch" in reasons


def test_simulator_import_returns_502_when_storage_upload_fails(monkeypatch) -> None:
    with _client_for(DummyUser(user_id=4, roles=["admin"])) as client:
        from app.api.v1.endpoints import simulator as simulator_endpoint
        from app.services.object_storage import StorageError

        def _raise_storage_error(batch_id: int, filename: str, content: bytes) -> tuple[str, str]:
            raise StorageError("minio unavailable")

        monkeypatch.setattr(simulator_endpoint, "upload_import_source", _raise_storage_error)
        response = client.post(
            "/api/v1/simulator/imports/anonymous",
            files={"file": ("sim.csv", "SerialNo\nSIM001\n", "text/csv")},
        )
        assert response.status_code == 502
        assert "minio unavailable" in response.json()["detail"]
