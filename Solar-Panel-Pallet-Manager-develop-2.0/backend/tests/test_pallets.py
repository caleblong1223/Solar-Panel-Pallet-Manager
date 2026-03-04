from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

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
def _make_test_client(user: DummyUser) -> Generator[TestClient, None, None]:
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


def test_pallet_lifecycle_and_history() -> None:
    user = DummyUser(user_id=101, roles=["packout_operator"])
    with _make_test_client(user) as client:
        create_response = client.post("/api/v1/pallets", json={"max_panels": 2, "template_type": "450WT"})
        assert create_response.status_code == 201
        pallet = create_response.json()
        pallet_id = pallet["id"]
        assert pallet["status"] == "active"
        assert pallet["item_count"] == 0

        add_1 = client.post(f"/api/v1/pallets/{pallet_id}/items", json={"serial": "abc123"})
        assert add_1.status_code == 200
        assert add_1.json()["item_count"] == 1

        duplicate = client.post(f"/api/v1/pallets/{pallet_id}/items", json={"serial": "ABC123"})
        assert duplicate.status_code == 409

        incomplete_complete = client.post(f"/api/v1/pallets/{pallet_id}/complete")
        assert incomplete_complete.status_code == 409

        add_2 = client.post(f"/api/v1/pallets/{pallet_id}/items", json={"serial": "abc124"})
        assert add_2.status_code == 200
        assert add_2.json()["item_count"] == 2

        over_capacity = client.post(f"/api/v1/pallets/{pallet_id}/items", json={"serial": "abc125"})
        assert over_capacity.status_code == 409

        complete_response = client.post(f"/api/v1/pallets/{pallet_id}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

        history_response = client.get(f"/api/v1/pallets/{pallet_id}/history")
        assert history_response.status_code == 200
        event_types = [event["event_type"] for event in history_response.json()]
        assert "pallet.created" in event_types
        assert "pallet.item_added" in event_types
        assert "pallet.completed" in event_types


def test_reset_and_delete_allowed_for_all_roles() -> None:
    for idx, role in enumerate(["packout_operator", "admin"], start=201):
        user = DummyUser(user_id=idx, roles=[role])
        with _make_test_client(user) as client:
            create_response = client.post("/api/v1/pallets", json={"max_panels": 1})
            pallet_id = create_response.json()["id"]
            client.post(f"/api/v1/pallets/{pallet_id}/items", json={"serial": f"SER{idx}"})
            client.post(f"/api/v1/pallets/{pallet_id}/complete")

            reset_response = client.post(f"/api/v1/pallets/{pallet_id}/reset")
            assert reset_response.status_code == 200
            assert reset_response.json()["status"] == "active"

            delete_response = client.delete(f"/api/v1/pallets/{pallet_id}")
            assert delete_response.status_code == 200

            get_deleted = client.get(f"/api/v1/pallets/{pallet_id}")
            assert get_deleted.status_code == 404
