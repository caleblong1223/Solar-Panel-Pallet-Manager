from __future__ import annotations

import os

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Role, User
from app.services.export_workbook import verify_core_export_templates

app = FastAPI(title=settings.app_name)


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    return {"status": "ready"}


@app.on_event("startup")
def validate_templates_and_seed_e2e_user() -> None:
    """Optionally seed a QA user for end-to-end tests.

    Controlled by ENABLE_E2E_SEED=1 to avoid impacting normal environments.
    """
    # First, verify that core Excel templates exist and look correct.
    verify_core_export_templates()

    # Optionally seed the E2E user for QA/test environments.
    if not os.getenv("ENABLE_E2E_SEED"):
        return

    db: Session = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "packout_operator").first()
        if role is None:
            role = Role(name="packout_operator", description="E2E test role")
            db.add(role)
            db.flush()

        user = db.query(User).filter(User.username == "critical_e2e_user").first()
        if user is None:
            user = User(
                username="critical_e2e_user",
                email="critical-e2e@example.com",
                password_hash=hash_password("critical-e2e-password"),
                is_active=True,
            )
            user.roles.append(role)
            db.add(user)
        else:
            user.is_active = True
            if role not in user.roles:
                user.roles.append(role)

        db.commit()
    finally:
        db.close()


app.include_router(api_router, prefix="/api/v1")
