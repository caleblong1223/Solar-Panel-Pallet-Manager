# Technical Design Document (TDD)
# Pallet Manager 2.0

**Date:** 2026-03-03  
**Status:** Draft v1  
**Source PRD:** `docs/PRD_PALLET_MANAGER_2_0.md`

## 1. Architecture Overview

Pallet Manager 2.0 is an intranet-first desktop system with a decoupled frontend and backend.

- Frontend: `Tauri + React + TypeScript`
- Backend API: `FastAPI`
- Database: `PostgreSQL`
- Object Storage: `MinIO` (S3-compatible)
- Optional background jobs: worker process (future phase)

### Design Principles

- DB is source of truth for operational state.
- Object storage is source of truth for binary artifacts (PDFs, optional upload originals).
- UI stays thin; business rules live in backend services.
- API-first boundaries to support future clients.
- Intranet deployment first, offline-friendly fallback supported.

## 2. Service Architecture

## 2.1 Components

1. `frontend/` (Desktop client)
- React app rendered in Tauri WebView.
- Talks to backend over HTTP (`/api/v1/*`).
- Auth token/session stored securely in local app storage.

2. `backend/` (Application service)
- FastAPI app with modular routers.
- SQLAlchemy ORM + Alembic migrations.
- Generates signed MinIO URLs for file access.
- Enforces auth, role checks, and audit trails.

3. `postgres`
- Stores users, customers, pallets, barcode mappings, simulator records, export metadata, and audit events.

4. `minio`
- Stores exported PDFs and optional raw simulator uploads.
- Organized by key convention:
  - `exports/{year}/{month}/{pallet_id}/{export_id}.pdf`
  - `imports/{year}/{month}/{batch_id}/{original_filename}`

## 2.2 Request Flow Example (Export)

1. User clicks Export in frontend.
2. Frontend calls `POST /api/v1/exports` with pallet + template info.
3. Backend validates role and pallet state, generates PDF.
4. Backend uploads PDF to MinIO, calculates checksum.
5. Backend writes export metadata row in Postgres.
6. Backend returns export record + signed URL.

## 3. API Boundaries

## 3.1 Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Security model:
- JWT access token (short TTL), refresh token (longer TTL).
- Passwords hashed with Argon2/bcrypt.
- Role-based authorization on protected endpoints.

## 3.2 Core Domain Endpoints

- `GET/POST /api/v1/customers`
- `GET/POST /api/v1/pallets`
- `GET/PATCH/DELETE /api/v1/pallets/{id}`
- `POST /api/v1/pallets/{id}/complete`
- `POST /api/v1/pallets/{id}/reset`
- `POST /api/v1/pallets/{id}/items` (add serial)
- `DELETE /api/v1/pallets/{id}/items/{item_id}`
- `GET /api/v1/barcodes/search?q=...`
- `POST /api/v1/simulator/imports`
- `GET /api/v1/simulator/imports/{id}`
- `POST /api/v1/exports`
- `GET /api/v1/exports/{id}/download-url`
- `GET /api/v1/audit/events`

## 3.3 API Standards

- Base path: `/api/v1`
- JSON request/response
- UTC timestamps in ISO-8601
- Standard pagination:
  - `page`, `page_size`, `sort`, `order`
- Standard filter style:
  - query params + optional POST search bodies for complex filters
- Error envelope:
  - `code`, `message`, `details`, `request_id`

## 4. Data Design

## 4.1 Core Tables

- `users`, `roles`, `user_roles`
- `customers`
- `pallets`
- `pallet_items`
- `sim_import_batches`
- `sim_panels`
- `exports`
- `audit_events`

## 4.2 Key Constraints

- Unique serial in `sim_panels` by `(serial, test_timestamp)`
- Unique serial per pallet in `pallet_items` by `(pallet_id, serial)`
- Soft-delete pallets via `deleted_at`, keep history/audit
- FK integrity for all references

## 4.3 Indexes

- `pallet_items(serial)` for fast barcode lookups
- `sim_panels(serial)` for simulator lookups
- `pallets(completed_at, status, customer_id)` for history filters
- `exports(pallet_id, created_at)` for export retrieval

## 5. Deployment Topology

## 5.1 Intranet Recommended

- One internal server hosts Docker services:
  - `api` (FastAPI)
  - `postgres`
  - `minio`
- Packout + purchasing clients run desktop app locally and connect via LAN.

## 5.2 Temporary Packout-Hosted Topology

- Same stack runs on packout PC in Docker.
- Purchasing connects over LAN.
- Acceptable for pilot, not ideal for long-term uptime.

## 5.3 Offline Mode

- Single workstation runs full stack locally.
- Client points to `http://localhost:8000`.
- No internet dependency.

## 6. Auth and Authorization Model

## 6.1 Roles

- `admin`: full access, user/config management.
- `packout_operator`: create/update/complete pallets, imports, exports.
- `purchasing_manager`: search/report/export retrieval, limited writes.

## 6.2 Policy Rules (Initial)

- Delete/reset pallet: `admin` or explicit privileged role.
- Import simulator: `packout_operator`, `admin`.
- View history/search: all authenticated roles.
- User management: `admin` only.

## 7. Security Model

- Argon2/bcrypt password hashing.
- JWT tokens with expiration and rotation.
- CORS locked to app origin(s).
- Secrets via environment variables only.
- MinIO credentials restricted by bucket policy.
- Audit logs include actor, action, resource, outcome.

## 8. Observability and Reliability

- `/health/live` and `/health/ready`
- Structured logs with request IDs.
- DB transaction boundaries in service layer.
- Retry strategy for MinIO transient failures.
- Daily backups for Postgres + MinIO volumes.

## 9. Backend Project Structure

```text
backend/
  app/
    api/v1/endpoints/
    core/
    db/
    models/
    main.py
  alembic/
    versions/
  pyproject.toml
  alembic.ini
```

## 10. Frontend Project Structure

```text
frontend/
  src/
    components/
    features/
    lib/
    styles/
    main.tsx
    App.tsx
  src-tauri/
```

## 11. Implementation Sequence

1. Stand up infrastructure (Postgres, MinIO, API skeleton).
2. Apply initial migration and seed roles/admin.
3. Build auth and session flow.
4. Build pallet APIs and history search.
5. Build import/export APIs with MinIO integration.
6. Build React/Tauri screens with API integration.
7. UAT, data migration, cutover.

## 12. Open Technical Decisions

- JWT-only vs JWT + server-side session table.
- Sync/queue behavior for temporary disconnections.
- Worker tech (RQ/Celery/Arq) for heavy imports/exports.
- Whether raw source simulator files are always retained.
