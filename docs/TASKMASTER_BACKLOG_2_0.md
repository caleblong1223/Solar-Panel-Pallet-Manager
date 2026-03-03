# Pallet Manager 2.0 - Execution Backlog

Source docs:
- `docs/PRD_PALLET_MANAGER_2_0.md`
- `docs/TDD_PALLET_MANAGER_2_0.md`

Scale:
- Effort: `S` (<=1 day), `M` (2-4 days), `L` (5+ days)
- Risk: `Low`, `Medium`, `High`

## Milestone 1: Platform Foundation

### PM2-001
- Title: Stand up local dev stack (Postgres, MinIO, API)
- Description: Use `docker-compose.intranet.yml` to boot baseline services and validate connectivity.
- Dependencies: None
- Acceptance criteria: `postgres`, `minio`, and `backend` all healthy; API reachable at `/health/live`; MinIO console reachable.
- Effort: M
- Risk: Medium
- Owner role: devops

### PM2-002
- Title: Configure backend environment and secrets strategy
- Description: Create `.env` profile strategy for local/dev/prod, define secret handling and rotation process.
- Dependencies: PM2-001
- Acceptance criteria: Documented env matrix; no hardcoded secrets in code; startup succeeds with env only.
- Effort: S
- Risk: Low
- Owner role: devops

### PM2-003
- Title: Apply Alembic migration baseline
- Description: Run initial schema migration and verify table/index creation.
- Dependencies: PM2-001
- Acceptance criteria: Revision `20260303_0001` applied; all expected tables exist.
- Effort: S
- Risk: Low
- Owner role: backend

### PM2-004
- Title: Add CI checks for backend and frontend skeletons
- Description: Add lint/test/build workflows to prevent drift.
- Dependencies: PM2-001
- Acceptance criteria: CI pipeline runs on PR, fails on lint/test/build errors.
- Effort: M
- Risk: Medium
- Owner role: fullstack

## Milestone 2: Auth and RBAC

### PM2-010
- Title: Implement user/role models and repository layer
- Description: Add ORM models and data access layer for users, roles, user_roles.
- Dependencies: PM2-003
- Acceptance criteria: CRUD/query functions with tests for users and role assignments.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-011
- Title: Implement password hashing and JWT issuance
- Description: Login flow with secure password verification, access/refresh token creation.
- Dependencies: PM2-010
- Acceptance criteria: `/auth/login`, `/auth/me`, refresh and logout function as designed.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-012
- Title: Enforce endpoint role guards
- Description: Add reusable authorization decorators/dependencies and protect sensitive routes.
- Dependencies: PM2-011
- Acceptance criteria: Restricted operations return 403 for unauthorized roles.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-013
- Title: Build frontend auth shell
- Description: Login screen, auth context, route guard, token refresh handling.
- Dependencies: PM2-011
- Acceptance criteria: Unauthenticated users blocked from app routes; session persists and refreshes.
- Effort: M
- Risk: Medium
- Owner role: frontend

## Milestone 3: Pallet Domain APIs

### PM2-020
- Title: Implement customer endpoints
- Description: CRUD/list endpoints for customers with validation and pagination.
- Dependencies: PM2-012
- Acceptance criteria: Customers manageable via API and tested.
- Effort: M
- Risk: Low
- Owner role: backend

### PM2-021
- Title: Implement pallet lifecycle endpoints
- Description: Create/update/complete/reset/delete with state transitions and audit events.
- Dependencies: PM2-012
- Acceptance criteria: Valid transitions enforced; invalid transitions rejected.
- Effort: L
- Risk: High
- Owner role: backend

### PM2-022
- Title: Implement pallet item (serial) operations
- Description: Add/remove serials with duplicate constraints and slot index checks.
- Dependencies: PM2-021
- Acceptance criteria: Duplicate/overflow checks pass; tests cover edge cases.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-023
- Title: Implement barcode search endpoint
- Description: Fast exact/partial search over `pallet_items` and `sim_panels`.
- Dependencies: PM2-022
- Acceptance criteria: P95 target under load met; pagination/sort supported.
- Effort: M
- Risk: Medium
- Owner role: backend

## Milestone 4: Simulator Import Pipeline

### PM2-030
- Title: Implement upload/ingest API and batch tracking
- Description: File upload endpoint and batch status lifecycle.
- Dependencies: PM2-012
- Acceptance criteria: Batch rows created with pending/processing/completed/failed statuses.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-031
- Title: Build parser adapter for existing simulator format
- Description: Normalize current sun simulator sheet format to `sim_panels` schema.
- Dependencies: PM2-030
- Acceptance criteria: Known files parse reliably; row-level reject reasons captured.
- Effort: L
- Risk: High
- Owner role: backend

### PM2-032
- Title: Store raw source uploads in MinIO
- Description: Persist original upload objects and store object keys/checksums.
- Dependencies: PM2-030
- Acceptance criteria: Raw file retrieval works; metadata linked to batch.
- Effort: M
- Risk: Medium
- Owner role: backend

## Milestone 5: Export + MinIO Integration

### PM2-040
- Title: Implement export generation service
- Description: Generate PDF artifacts from completed pallet data.
- Dependencies: PM2-021, PM2-022
- Acceptance criteria: Export file generated for supported templates with tests.
- Effort: L
- Risk: High
- Owner role: backend

### PM2-041
- Title: Upload exports to MinIO and persist metadata
- Description: Object upload + `exports` row creation with checksum and size.
- Dependencies: PM2-040
- Acceptance criteria: Export record includes object key and signed URL retrieval works.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-042
- Title: Export retrieval/list APIs
- Description: Query exports by pallet/date/customer and download URL endpoint.
- Dependencies: PM2-041
- Acceptance criteria: Filtered export list works with pagination/sort.
- Effort: M
- Risk: Medium
- Owner role: backend

## Milestone 6: React/Tauri UI Screens

### PM2-050
- Title: Establish design system and layout shell
- Description: Theme tokens, typography, app frame, nav and global notifications.
- Dependencies: PM2-013
- Acceptance criteria: Reusable UI primitives available and documented.
- Effort: M
- Risk: Low
- Owner role: frontend

### PM2-051
- Title: Build Live Builder screen
- Description: Pallet create/add/remove/complete UX with keyboard-first flow.
- Dependencies: PM2-021, PM2-022, PM2-050
- Acceptance criteria: Operator can run complete build cycle without fallback UI.
- Effort: L
- Risk: High
- Owner role: frontend

### PM2-052
- Title: Build History Explorer screen
- Description: Server-side search, filters, table, details panel, and actions.
- Dependencies: PM2-023, PM2-050
- Acceptance criteria: Purchasing can locate pallet/export by serial in target time.
- Effort: L
- Risk: Medium
- Owner role: frontend

### PM2-053
- Title: Build Import Center and Export Library screens
- Description: Upload/import progress and export browsing/download UX.
- Dependencies: PM2-031, PM2-042, PM2-050
- Acceptance criteria: Import and export workflows complete from UI.
- Effort: L
- Risk: Medium
- Owner role: frontend

## Milestone 7: Legacy Migration

### PM2-060
- Title: Migrate legacy customers into DB
- Description: Import existing customer workbook into `customers` table.
- Dependencies: PM2-003
- Acceptance criteria: Customer count matches source after normalization.
- Effort: S
- Risk: Low
- Owner role: backend

### PM2-061
- Title: Migrate pallet history JSON into DB
- Description: Convert historical pallets + items + status to new tables.
- Dependencies: PM2-003
- Acceptance criteria: All pallets and serials loaded; spot checks pass.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-062
- Title: Index historical exports into DB/MinIO references
- Description: Create export metadata records for existing files.
- Dependencies: PM2-061
- Acceptance criteria: Existing exports searchable and openable by metadata.
- Effort: M
- Risk: Medium
- Owner role: backend

### PM2-063
- Title: Build migration reconciliation report
- Description: Compare legacy counts/keys vs DB and output mismatch report.
- Dependencies: PM2-060, PM2-061, PM2-062
- Acceptance criteria: Report generated with zero critical mismatches before cutover.
- Effort: S
- Risk: Medium
- Owner role: qa

## Milestone 8: QA, UAT, Release

### PM2-070
- Title: End-to-end test suite for critical workflows
- Description: Add API and UI integration tests for login, pallet build, import, export, search.
- Dependencies: PM2-053
- Acceptance criteria: Critical flows pass in CI against ephemeral stack.
- Effort: L
- Risk: Medium
- Owner role: qa

### PM2-071
- Title: Backup/restore validation and runbook
- Description: Script and test Postgres + MinIO backup/restore on schedule.
- Dependencies: PM2-001
- Acceptance criteria: Successful restore drill documented.
- Effort: M
- Risk: High
- Owner role: devops

### PM2-072
- Title: UAT with packout and purchasing workflows
- Description: Role-based acceptance sessions and sign-off criteria tracking.
- Dependencies: PM2-051, PM2-052, PM2-053, PM2-063
- Acceptance criteria: No critical blockers, formal sign-off achieved.
- Effort: M
- Risk: Medium
- Owner role: qa

### PM2-073
- Title: Production rollout and cutover
- Description: Deploy, migrate, monitor, and switch clients to 2.0 default.
- Dependencies: PM2-072, PM2-071
- Acceptance criteria: Stable operations for 2 weeks with no Sev-1 data issues.
- Effort: M
- Risk: High
- Owner role: devops

## Critical Path

1. PM2-001 -> PM2-003 -> PM2-010 -> PM2-011 -> PM2-012
2. PM2-021 -> PM2-022 -> PM2-023
3. PM2-030 -> PM2-031
4. PM2-040 -> PM2-041 -> PM2-042
5. PM2-050 -> PM2-051/PM2-052/PM2-053
6. PM2-061 -> PM2-062 -> PM2-063
7. PM2-070 -> PM2-072 -> PM2-073

## Week-by-Week Suggested Sequence

- Week 1: PM2-001/002/003/004/010
- Week 2: PM2-011/012/020/021
- Week 3: PM2-022/023/030/031
- Week 4: PM2-032/040/041
- Week 5: PM2-042/050/051
- Week 6: PM2-052/053
- Week 7: PM2-060/061/062/063
- Week 8: PM2-070/071/072/073

## First 10 Tasks to Start Immediately

1. PM2-001
2. PM2-003
3. PM2-002
4. PM2-010
5. PM2-011
6. PM2-012
7. PM2-021
8. PM2-022
9. PM2-050
10. PM2-060
