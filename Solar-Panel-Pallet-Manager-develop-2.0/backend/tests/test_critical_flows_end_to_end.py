from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import Role, User


TEST_USERNAME = "critical_e2e_user"
TEST_PASSWORD = "critical-e2e-password"


@contextmanager
def _client_with_seeded_user() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
    Base.metadata.create_all(bind=engine)

    seed_db = testing_session_local()
    try:
        role = Role(name="packout_operator")
        user = User(
            username=TEST_USERNAME,
            email="critical-e2e@example.com",
            password_hash=hash_password(TEST_PASSWORD),
            is_active=True,
        )
        user.roles.append(role)
        seed_db.add_all([role, user])
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
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _login_and_get_headers(client: TestClient) -> dict[str, str]:
    login_response = client.post(
        "/api/v1/auth/login-json",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_pallet_build_export_and_download_flow(monkeypatch) -> None:
    with _client_with_seeded_user() as client:
        from app.api.v1.endpoints import exports as exports_endpoint

        headers = _login_and_get_headers(client)

        create_pallet = client.post(
            "/api/v1/pallets",
            json={"max_panels": 2, "template_type": "450WT"},
            headers=headers,
        )
        assert create_pallet.status_code == 201
        pallet = create_pallet.json()
        pallet_id = pallet["id"]

        add_first = client.post(
            f"/api/v1/pallets/{pallet_id}/items",
            json={"serial": "E2E-PALLET-001"},
            headers=headers,
        )
        assert add_first.status_code == 200

        add_second = client.post(
            f"/api/v1/pallets/{pallet_id}/items",
            json={"serial": "E2E-PALLET-002"},
            headers=headers,
        )
        assert add_second.status_code == 200

        complete = client.post(f"/api/v1/pallets/{pallet_id}/complete", headers=headers)
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

        monkeypatch.setattr(
            exports_endpoint,
            "upload_export_artifact",
            lambda export_id, pallet_id, filename, content: (
                f"exports/2026/03/{pallet_id}/{export_id}/{filename}",
                "critical-checksum",
            ),
        )

        create_export = client.post(
            "/api/v1/exports",
            json={"pallet_id": pallet_id, "template_type": "450WT"},
            headers=headers,
        )
        assert create_export.status_code == 201
        export_payload = create_export.json()
        export_id = export_payload["id"]
        assert export_payload["pallet_id"] == pallet_id
        assert export_payload["checksum_sha256"] == "critical-checksum"

        monkeypatch.setattr(
            exports_endpoint,
            "generate_export_download_url",
            lambda object_key, expires_in_seconds=900: f"https://minio.local/{object_key}?exp={expires_in_seconds}",
        )

        download = client.get(
            f"/api/v1/exports/{export_id}/download-url?expires_in_seconds=600",
            headers=headers,
        )
        assert download.status_code == 200
        download_payload = download.json()
        assert download_payload["export_id"] == export_id
        assert "https://minio.local/" in download_payload["download_url"]


def test_simulator_import_and_barcode_search_flow(monkeypatch) -> None:
    with _client_with_seeded_user() as client:
        from app.api.v1.endpoints import simulator as simulator_endpoint

        headers = _login_and_get_headers(client)

        monkeypatch.setattr(
            simulator_endpoint,
            "upload_import_source",
            lambda batch_id, filename, content: (
                f"imports/2026/03/{batch_id}/{filename}",
                "critical-import-checksum",
            ),
        )

        csv_content = "SerialNo,Result\nSN-E2E-001,PASS\n"
        import_response = client.post(
            "/api/v1/simulator/imports",
            files={"file": ("sim.csv", csv_content, "text/csv")},
            headers=headers,
        )
        assert import_response.status_code == 201
        import_payload = import_response.json()
        assert import_payload["rows_total"] == 1
        assert import_payload["rows_imported"] == 1
        assert import_payload["rows_rejected"] == 0

        pallet_create = client.post(
            "/api/v1/pallets",
            json={"max_panels": 5, "template_type": "450WT"},
            headers=headers,
        )
        assert pallet_create.status_code == 201
        pallet_id = pallet_create.json()["id"]

        add_item = client.post(
            f"/api/v1/pallets/{pallet_id}/items",
            json={"serial": "SN-E2E-001"},
            headers=headers,
        )
        assert add_item.status_code == 200

        search = client.get(
            "/api/v1/barcodes/search?q=SN-E2E-001&exact=true",
            headers=headers,
        )
        assert search.status_code == 200
        payload = search.json()
        assert payload["total"] >= 2
        sources = {entry["source"] for entry in payload["results"]}
        assert "pallet_item" in sources
        assert "sim_panel" in sources

