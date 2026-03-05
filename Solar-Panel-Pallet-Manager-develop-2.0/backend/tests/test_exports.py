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
from app.models.pallet import Export, Pallet, PalletItem


class DummyRole:
    def __init__(self, name: str) -> None:
        self.name = name


class DummyUser:
    def __init__(self, user_id: int, roles: list[str]) -> None:
        self.id = user_id
        self.roles = [DummyRole(role) for role in roles]


@contextmanager
def _client_with_pallet(user: DummyUser, *, pallet_status: str = "completed") -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
    Base.metadata.create_all(bind=engine)

    seed_db = testing_session_local()
    try:
        pallet = Pallet(
            pallet_number=9,
            status=pallet_status,
            max_panels=2,
            created_by=user.id,
            completed_at=datetime.now(timezone.utc) if pallet_status == "completed" else None,
        )
        seed_db.add(pallet)
        seed_db.flush()
        seed_db.add_all(
            [
                PalletItem(pallet_id=pallet.id, serial="EXP001", slot_index=1, added_by=user.id),
                PalletItem(pallet_id=pallet.id, serial="EXP002", slot_index=2, added_by=user.id),
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


def test_create_export_success(monkeypatch) -> None:
    with _client_with_pallet(DummyUser(user_id=1, roles=["packout_operator"])) as client:
        from app.api.v1.endpoints import exports as exports_endpoint

        monkeypatch.setattr(
            exports_endpoint,
            "upload_export_artifact",
            lambda export_id, pallet_id, filename, content: (
                f"exports/2026/03/{pallet_id}/{export_id}/{filename}",
                "checksum123",
            ),
        )
        response = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        print("DEBUG create_export_success", response.status_code, response.text)
        assert response.status_code == 201
        payload = response.json()
        assert payload["pallet_id"] == 1
        assert payload["checksum_sha256"] == "checksum123"
        assert payload["object_key"].startswith("exports/")


def test_create_export_requires_completed_pallet(monkeypatch) -> None:
    with _client_with_pallet(DummyUser(user_id=2, roles=["admin"]), pallet_status="active") as client:
        from app.api.v1.endpoints import exports as exports_endpoint

        monkeypatch.setattr(
            exports_endpoint,
            "upload_export_artifact",
            lambda export_id, pallet_id, filename, content: (
                f"exports/2026/03/{pallet_id}/{export_id}/{filename}",
                "checksum123",
            ),
        )
        response = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        assert response.status_code == 409


def test_list_exports_and_filters(monkeypatch) -> None:
    with _client_with_pallet(DummyUser(user_id=3, roles=["purchasing_manager"])) as client:
        from app.api.v1.endpoints import exports as exports_endpoint

        monkeypatch.setattr(
            exports_endpoint,
            "upload_export_artifact",
            lambda export_id, pallet_id, filename, content: (
                f"exports/2026/03/{pallet_id}/{export_id}/{filename}",
                f"checksum{export_id}",
            ),
        )
        create_a = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        create_b = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "550WT"})
        assert create_a.status_code == 201
        assert create_b.status_code == 201

        list_all = client.get("/api/v1/exports")
        assert list_all.status_code == 200
        assert list_all.json()["total"] == 2

        filtered = client.get("/api/v1/exports?template_type=450WT")
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1
        assert filtered.json()["exports"][0]["template_type"] == "450WT"


def test_export_download_url_endpoint(monkeypatch) -> None:
    with _client_with_pallet(DummyUser(user_id=5, roles=["admin"])) as client:
        from app.api.v1.endpoints import exports as exports_endpoint

        monkeypatch.setattr(
            exports_endpoint,
            "upload_export_artifact",
            lambda export_id, pallet_id, filename, content: (
                f"exports/2026/03/{pallet_id}/{export_id}/{filename}",
                f"checksum{export_id}",
            ),
        )
        created = client.post("/api/v1/exports", json={"pallet_id": 1, "template_type": "450WT"})
        export_id = created.json()["id"]

        monkeypatch.setattr(
            exports_endpoint,
            "generate_export_download_url",
            lambda object_key, expires_in_seconds=900: f"https://minio.local/{object_key}?exp={expires_in_seconds}",
        )
        dl = client.get(f"/api/v1/exports/{export_id}/download-url?expires_in_seconds=600")
        assert dl.status_code == 200
        assert dl.json()["export_id"] == export_id
        assert "https://minio.local/" in dl.json()["download_url"]

        missing = client.get("/api/v1/exports/999/download-url")
        assert missing.status_code == 404
