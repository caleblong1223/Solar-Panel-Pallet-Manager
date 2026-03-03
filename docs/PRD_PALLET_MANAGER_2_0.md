# Product Requirements Document (PRD)
# Pallet Manager 2.0

**Document Owner:** Crossroads Solar  
**Product:** Pallet Manager  
**Version Target:** 2.0.0  
**Date:** 2026-03-03  
**Status:** Draft for implementation kickoff

## 1. Executive Summary

Pallet Manager 2.0 is a full platform upgrade from a local-file, Tkinter-based desktop app to a modern, searchable, multi-user system with a premium UI and reliable centralized data.

The product will support:
- Modern desktop UX via `Tauri + React`
- Python backend services via `FastAPI`
- Reliable relational data via `PostgreSQL`
- Exported PDF/object artifact storage via S3-compatible object storage (`MinIO` on intranet)
- Multi-computer synchronized access (packout + purchasing manager)
- Intranet-first operation with offline-tolerant behavior

## 2. Problem Statement

Current 1.1 workflows are constrained by:
- Legacy UI look/feel and limited interaction patterns
- File/JSON-based state becoming hard to maintain and audit
- Harder searching/filtering for barcodes, pallets, and exports at scale
- Data fragmentation between users/computers
- Risk of operational drift when records and files diverge

## 3. Goals and Non-Goals

## Goals
- Deliver a premium, modern desktop experience.
- Centralize pallet, barcode, simulator, and export metadata in a shared database.
- Enable fast search/filter across key operational records.
- Support multi-user synchronized access over intranet.
- Track PDF exports in object storage with strong traceability.
- Preserve core business workflows and minimize retraining.

## Non-Goals (2.0)
- Internet/cloud dependency as a requirement.
- Full mobile app.
- Complete workflow redesign of pallet operations logic.
- Advanced analytics dashboards beyond operational reporting.

## 4. Users and Roles

## Primary Users
- Packout Operator: scans barcodes, builds/completes pallets, exports sheets/PDFs.
- Purchasing Manager: searches history, verifies records, reviews/export documents, filters by customer/date/serial.

## Secondary Users
- Admin/IT: manages deployment, backups, user permissions, and health monitoring.

## 5. Product Scope

## In Scope
- New desktop UI app (Tauri shell + React frontend).
- API backend (FastAPI).
- PostgreSQL data model and migrations.
- MinIO object storage integration for PDFs and optional raw upload retention.
- Authentication and role-based authorization.
- Search/filter APIs and UI.
- Migration tools from existing data files.
- Packaging and deployment for intranet use.

## Out of Scope
- Cloud-hosted SaaS deployment.
- Native mobile clients.
- ERP integration in 2.0 baseline.

## 6. Functional Requirements

## 6.1 Authentication and Access Control
- Users must sign in with credentials.
- Role model:
  - `packout_operator`
  - `purchasing_manager`
  - `admin`
- Role-based permissions must restrict destructive operations (delete/reset) and admin settings.
- Session timeout and secure re-auth supported.

## 6.2 Pallet Lifecycle
- Create pallet with daily numbering rules.
- Add/remove serials with validation and duplicate protection.
- Enforce pallet capacity rules (configurable by template type).
- Complete/finalize pallet.
- Reset pallet (authorized roles only).
- Delete pallet (authorized roles only) with audit trail.

## 6.3 Barcode and Serial Search
- Search by exact or partial serial.
- Return:
  - pallet association
  - status (active/completed/reset/deleted)
  - timestamps
  - customer context
- Results should support pagination, sorting, and filter combinations.

## 6.4 Pallet History and Filtering
- Query pallets by:
  - date range
  - customer
  - operator
  - status
  - pallet number
  - serial presence
- Support bulk select actions for approved workflows.
- Show clear details panel and item-level audit summary.

## 6.5 Sun Simulator Data Ingestion
- Upload simulator files in existing operational format.
- Parse and normalize simulator records into DB.
- Preserve source file metadata.
- Optional source file retention in MinIO.
- Validate schema/headers and provide clear import error diagnostics.

## 6.6 Export Generation and Storage
- Generate pallet export sheets/PDF artifacts.
- Store PDFs in object storage (MinIO bucket).
- Record DB metadata:
  - object key
  - checksum
  - size
  - template type
  - created timestamp
  - created by
  - linked pallet id
- UI must allow quick retrieval and download/open via signed URLs.

## 6.7 Audit and Traceability
- Log all critical actions:
  - create/update/reset/delete pallet
  - serial add/remove
  - import/upload actions
  - export generation/download
  - login/security events
- Audit entries immutable and queryable by admins.

## 6.8 Notifications and Feedback
- Standardized success/warning/error messages.
- Long operations show progress/loading states.
- Errors must return actionable operator-safe messaging.

## 7. Non-Functional Requirements

## 7.1 Performance
- Search response target: P95 < 500ms for common filters on operational dataset.
- Pallet history list initial load target: < 2s for default filters.
- Import processing target: progress visible within 1s and non-blocking UI.

## 7.2 Reliability
- ACID persistence for operational records.
- No data loss on app restart/crash for committed actions.
- Idempotent import safeguards to prevent duplicate ingest.

## 7.3 Availability
- Intranet deployment target uptime: 99% during business hours.
- Graceful degradation when server temporarily unavailable (read-only cache view + retry).

## 7.4 Security
- Password hashing (`bcrypt`/Argon2).
- TLS on intranet where feasible.
- Signed URLs for object storage access.
- Principle of least privilege for DB/object credentials.
- Audit logging for privileged actions.

## 7.5 Maintainability
- Versioned DB migrations.
- Structured logs and health endpoints.
- Centralized configuration by environment files.

## 8. System Architecture

## 8.1 High-Level Components
- `Desktop App`: Tauri wrapper with React UI.
- `API Service`: FastAPI app exposing REST endpoints.
- `Database`: PostgreSQL for transactional/relational data.
- `Object Storage`: MinIO for PDFs and optional source uploads.
- `Worker/Jobs`: background tasks for imports/exports (Celery/RQ or FastAPI background + queue).

## 8.2 Deployment Modes
- **Preferred**: Dedicated intranet server hosts API + Postgres + MinIO (Docker Compose).
- **Fallback**: Packout computer hosts services; other clients connect over LAN.
- **Offline Option**: Single-machine local deployment with localhost endpoints.

## 8.3 Data Ownership
- PostgreSQL is source of truth for records and relationships.
- Object storage is source of truth for binary export artifacts.
- Filesystem folders are operational caches, not authoritative state.

## 9. Data Model Requirements (Logical)

Core entities:
- `users`
- `roles`
- `customers`
- `pallets`
- `pallet_items`
- `sim_import_batches`
- `sim_panels`
- `exports`
- `audit_events`

Required constraints:
- Unique serial constraints according to business rules.
- Referential integrity between pallets, items, exports, customers, and users.
- Soft delete for pallets with hard audit retention.

Required indexes:
- `sim_panels.serial`
- `pallet_items.serial`
- `pallets.pallet_number`, `pallets.completed_at`, `pallets.status`
- `exports.pallet_id`, `exports.created_at`
- Optional trigram indexes for partial barcode search.

## 10. API Requirements (v1)

Representative endpoint groups:
- `/auth/*` login/session/refresh/logout
- `/customers/*` CRUD/list
- `/pallets/*` create/update/complete/reset/delete/list/detail
- `/barcodes/search`
- `/simulator/imports/*` upload, validate, process, status
- `/exports/*` create, list, retrieve signed URL
- `/audit/*` query admin events
- `/health/*` liveness/readiness

API requirements:
- Pagination and sorting for list endpoints.
- Strong input validation and typed response contracts.
- Correlation/request IDs for traceability.

## 11. UI/UX Requirements

## 11.1 Visual Direction
- Modern industrial/professional interface with clear hierarchy.
- High contrast and large touch-friendly targets for shop-floor use.
- Light and dark themes.

## 11.2 Core Screens
- Login
- Dashboard/Home
- Live Pallet Builder
- Pallet History Explorer
- Sun Simulator Import Center
- Export Library
- Admin/Settings (role-limited)

## 11.3 Interaction Patterns
- Keyboard-first scan flow with minimal clicks.
- Fast global search for barcode/pallet/customer.
- Side detail panes and bulk actions.
- Clear destructive action confirmations.

## 11.4 Accessibility
- Readable default font size and scalable UI.
- Keyboard navigable core workflows.
- Color usage not solely relied on for status meaning.

## 12. Migration and Backward Compatibility

## 12.1 Data Migration
- Migrate existing JSON history into PostgreSQL.
- Index existing export files into `exports` table.
- Preserve mapping to current pallet numbers and timestamps.
- Import legacy customer definitions into DB.

## 12.2 Cutover Strategy
- Phase 1: Dual-write (legacy + DB) for validation.
- Phase 2: DB-first reads with legacy fallback.
- Phase 3: Legacy writes disabled after verification.

## 12.3 Rollback Plan
- Keep legacy artifacts unchanged during rollout window.
- Versioned backups before each migration run.
- Rollback scripts for schema and service deployment.

## 13. Reporting and Search Capabilities

Must support:
- Filtered pallet lists by time/customer/status/operator.
- Barcode trace report: serial -> pallet -> export artifact.
- Export audit report by date/template/user.
- Import quality report: successful rows, rejected rows, reason codes.

## 14. DevOps and Deployment Requirements

## 14.1 Containerization
- Docker Compose baseline services:
  - `api`
  - `postgres`
  - `minio`
  - optional `worker`
- Persistent volumes for DB and object storage.

## 14.2 Environment Configuration
- Central `.env` with secrets in secure storage.
- Separate configs for `local`, `intranet-prod`.

## 14.3 Backups
- PostgreSQL: daily full backup + point-in-time/WAL optional.
- MinIO: daily bucket backup/snapshot.
- Test restore procedure monthly.

## 14.4 Monitoring
- Service health checks.
- Error-rate and latency logs.
- Backup success/failure alerts.

## 15. Success Metrics

Operational metrics:
- 50% reduction in average time to locate a pallet/export by search.
- 80% reduction in “missing/misplaced export file” incidents.
- <1% import failure rate due to system errors (excluding bad source files).
- 0 critical data-loss incidents post-cutover.

Adoption metrics:
- 100% of packout operations performed in 2.0 within rollout period.
- Purchasing manager actively using shared search/filter workflows weekly.

## 16. Risks and Mitigations

- **Risk:** Single point of failure if hosted on packout PC.
  - **Mitigation:** Move services to dedicated intranet host ASAP.
- **Risk:** Migration mismatches from legacy data quirks.
  - **Mitigation:** Dry-run migrations + validation reports + sampled reconciliation.
- **Risk:** User resistance to UI changes.
  - **Mitigation:** Keep workflow parity, provide quick-reference training.
- **Risk:** Object storage misconfiguration.
  - **Mitigation:** Automated integration tests and backup verification.

## 17. Release Plan and Milestones

## Phase 0: Foundations (2-3 weeks)
- Architecture setup, repo structure, Docker services, auth baseline.

## Phase 1: Data Core (2-3 weeks)
- Postgres schema/migrations, core APIs, MinIO integration, audit model.

## Phase 2: UI Core (3-4 weeks)
- React/Tauri shell, login, pallet builder, history explorer, search/filter.

## Phase 3: Import/Export + Migration (2-3 weeks)
- Simulator ingestion flows, export generation/storage, migration scripts.

## Phase 4: Stabilization and Cutover (2 weeks)
- UAT, performance tuning, training, rollout, monitoring/backup drills.

## 18. Acceptance Criteria

2.0 release is accepted when:
- Both packout and purchasing clients can use the same synchronized intranet database.
- Barcode/pallet/customer search and filtering meet response targets.
- PDF exports are stored and retrieved from MinIO with DB-tracked metadata.
- Legacy data has been migrated and validated.
- Role-based access and audit logs are active.
- Backup and restore procedures are tested successfully.
- Core daily operations run without blocking issues for 2 consecutive weeks.

## 19. Open Questions

- Final hosting choice at launch: dedicated server or temporary packout-hosted stack?
- Required retention period for simulator source files and exports?
- Exact role permission boundaries for delete/reset/export operations?
- Need for barcode scanner device abstraction beyond keyboard wedge mode?

## 20. Immediate Next Actions

1. Approve this PRD baseline and lock scope for 2.0.
2. Define technical design doc (TDD) and API contract spec.
3. Build initial schema + migration scripts.
4. Stand up intranet Docker stack (Postgres + MinIO + API skeleton).
5. Start UI prototype for Builder + History with real API data.
