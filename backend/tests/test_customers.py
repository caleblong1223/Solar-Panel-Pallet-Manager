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


def test_customer_crud_flow_for_packout_and_admin() -> None:
    with _client_for(DummyUser(user_id=1, roles=["packout_operator"])) as client:
        create = client.post(
            "/api/v1/customers",
            json={"display_name": "Acme Solar", "email": "ops@acme.com"},
        )
        assert create.status_code == 201
        customer_id = create.json()["id"]

        get_one = client.get(f"/api/v1/customers/{customer_id}")
        assert get_one.status_code == 200
        assert get_one.json()["display_name"] == "Acme Solar"

        update = client.patch(f"/api/v1/customers/{customer_id}", json={"phone": "555-1000"})
        assert update.status_code == 200
        assert update.json()["phone"] == "555-1000"

    with _client_for(DummyUser(user_id=2, roles=["admin"])) as client:
        create = client.post("/api/v1/customers", json={"display_name": "Beta Solar"})
        customer_id = create.json()["id"]
        delete = client.delete(f"/api/v1/customers/{customer_id}")
        assert delete.status_code == 204
        get_one = client.get(f"/api/v1/customers/{customer_id}")
        assert get_one.status_code == 200
        assert get_one.json()["is_active"] is False


def test_customer_permissions_and_conflict() -> None:
    with _client_for(DummyUser(user_id=3, roles=["purchasing_manager"])) as client:
        list_response = client.get("/api/v1/customers")
        assert list_response.status_code == 200
        create_denied = client.post("/api/v1/customers", json={"display_name": "Gamma Solar"})
        assert create_denied.status_code == 403

    with _client_for(DummyUser(user_id=4, roles=["admin"])) as client:
        create_a = client.post("/api/v1/customers", json={"display_name": "Dup Solar"})
        assert create_a.status_code == 201
        create_b = client.post("/api/v1/customers", json={"display_name": "Dup Solar"})
        assert create_b.status_code == 409
