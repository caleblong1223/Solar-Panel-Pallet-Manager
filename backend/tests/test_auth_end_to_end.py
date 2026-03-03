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


TEST_USERNAME = "qa_operator"
TEST_PASSWORD = "test-password-123"


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
            email="qa@example.com",
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


def test_login_and_use_token_for_me_and_customers() -> None:
    with _client_with_seeded_user() as client:
        login_response = client.post(
            "/api/v1/auth/login-json",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_payload = me_response.json()
        assert me_payload["username"] == TEST_USERNAME
        assert me_payload["is_active"] is True

        customers_response = client.get("/api/v1/customers", headers=headers)
        assert customers_response.status_code == 200

