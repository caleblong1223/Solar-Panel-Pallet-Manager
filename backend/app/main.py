from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.pallet import Customer
from app.models.user import Role, User
from app.services.export_workbook import verify_core_export_templates

app = FastAPI(title=settings.app_name)

# Allow Tauri/Web frontends to call the API across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "http://tauri.localhost",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    # Ensure the schema exists so the standalone desktop backend can run without running migrations first.
    Base.metadata.create_all(bind=engine)
    # First, verify that core Excel templates exist and look correct.
    verify_core_export_templates()

    db: Session = SessionLocal()
    try:
        is_sqlite = db.bind is not None and db.bind.dialect.name == "sqlite"
        default_customer = (
            db.query(Customer)
            .filter(Customer.display_name == "Josh Atwood")
            .first()
        )
        if default_customer is None:
            customer_kwargs = {
                "display_name": "Josh Atwood",
                "contact_name": "Josh Atwood",
                "business_name": "Future Solutions Inc",
                "address": "2616 Glenview Dr",
                "city": "Elkhart",
                "state": "IN",
                "zip_code": "46514",
                "is_active": True,
            }
            # Local SQLite fallback databases may use legacy schemas where id
            # is not auto-assigned. Ensure deterministic seeding works there.
            if is_sqlite:
                max_id = db.query(Customer.id).order_by(Customer.id.desc()).limit(1).scalar()
                customer_kwargs["id"] = (max_id or 0) + 1

            default_customer = Customer(**customer_kwargs)
            db.add(default_customer)

        if os.getenv("ENABLE_E2E_SEED"):
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
