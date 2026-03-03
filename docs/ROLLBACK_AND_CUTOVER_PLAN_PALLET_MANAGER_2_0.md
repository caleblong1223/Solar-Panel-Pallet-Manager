# Pallet Manager 2.0 – Production Rollout & Cutover (PM2-073)

This runbook describes how to deploy Pallet Manager 2.0 to production, switch users over, and roll back safely if needed.

It assumes:

- Backend is the FastAPI service in `backend/`.
- Frontend is the Tauri/React client in `frontend/` (or a Vite-built static bundle).
- Database is Postgres; exports/imports are in MinIO or S3-compatible storage.

---

## 1. Pre-Cutover Checklist

- [ ] PM2-071 – backup/restore validation completed and documented.
- [ ] PM2-072 – UAT sign-off recorded in `UAT_PLAN_PALLET_MANAGER_2_0.md`.
- [ ] All schema migrations applied and version in production DB matches QA.
- [ ] Monitoring/alerts configured for:
  - API errors (5xx, 4xx rates).
  - DB connectivity.
  - Object storage connectivity.
- [ ] Legacy 1.1 system is still available and can be re-pointed to if rollback is required.

---

## 2. Backup & Snapshot (Before Cutover)

1. **Database snapshot**
   - Take a full logical backup of the production Postgres database:
     - `pg_dump -Fc -h $DB_HOST -U $DB_USER -d $DB_NAME -f pallet_manager_prod_$(date +%Y%m%d%H%M).dump`
   - Verify backup size is non-zero and stored in your standard backup location.

2. **Object storage snapshot**
   - Ensure MinIO/S3 lifecycle/backup is active for:
     - `exports/` prefix.
     - `imports/` prefix.
   - Optionally, run a one-off sync to secondary storage (if available).

3. **Configuration snapshot**
   - Save a copy of production `.env` / config files for backend and any Tauri packaging settings.

---

## 3. Deployment Steps (Backend & Frontend)

1. **Backend deploy**
   - Build and deploy the Pallet Manager 2.0 backend container or service to production hosts.
   - Apply latest Alembic migrations:
     - `cd backend && alembic upgrade head`
   - Start the service with production settings:
     - `uvicorn app.main:app --host 0.0.0.0 --port 8000` (or via your process manager/container orchestrator).

2. **Frontend deploy**
   - Build the frontend:
     - `cd frontend && npm install && npm run build`
   - Package or deploy the Tauri/desktop build or static assets as appropriate for your environment.
   - Confirm the app is configured to point at the production API base URL.

3. **Sanity checks**
   - Hit `/health/live` and `/health/ready` on the backend.
   - Launch the frontend against production and verify:
     - App loads.
     - Shared session initializes (no visible login).

---

## 4. Cutover Steps (Switching Users to 2.0)

1. **Announce maintenance window (if needed)**
   - Notify operators of the expected switchover time and brief testing steps.

2. **Freeze legacy writes**
   - For the old 1.1 process, pause new pallet builds or coordinate a short “quiet” window.

3. **Point users to 2.0**
   - Install or distribute the new desktop app to packout stations and purchasing.
   - Update any launcher shortcuts to open the 2.0 client instead of the legacy one.

4. **Smoke test with real users**
   - With live data, ask one operator and one purchasing user to walk through:
     - A pallet build and completion.
     - A simulator import.
     - An export creation and open.
     - A barcode search and history lookup.
   - Confirm results match expectations and there are no Sev-1/2 issues.

5. **Declare 2.0 as default**
   - Once basic smoke tests pass, mark 2.0 as the primary system for day-to-day operations.

---

## 5. Monitoring During the First 2 Weeks

For PM2-073 acceptance criteria (“Stable operations for 2 weeks with no Sev-1 data issues”):

- Daily checks:
  - [ ] API error rates stay within normal bounds.
  - [ ] No failed exports/imports without explanation in logs.
  - [ ] No mismatches in critical counts vs legacy (if still used for reference).
- Incident logging:
  - [ ] Any Sev-1/2 bugs recorded with timestamps, affected pallets/customers, and root cause.

If the two-week period completes with no Sev-1 data issues, mark PM2-073 as **done**.

---

## 6. Rollback Plan

Use this if a Sev-1 data issue or major instability is discovered shortly after cutover.

1. **Trigger rollback decision**
   - Criteria:
     - Data corruption or loss in pallets, customers, or exports.
     - Critical downtime that cannot be resolved quickly.

2. **Stop 2.0 writes**
   - Temporarily disable operator access to the 2.0 app (e.g., stop backend or block network access).

3. **Restore from backups**
   - Restore Postgres from the snapshot taken prior to cutover:
     - `pg_restore -c -d $DB_NAME pallet_manager_prod_<timestamp>.dump`
   - Confirm MinIO/S3 objects are intact (usually no restore needed if read-only issues).

4. **Re-enable legacy 1.1**
   - Point operators back to the 1.1 process.
   - Communicate clearly which data entry period might be “lost” in 2.0 and should be re-keyed in 1.1 if necessary.

5. **Post-mortem and fix**
   - Identify root cause and plan fixes for 2.0 before attempting another cutover.

---

## 7. Post-Stabilization Cleanup

After 2.0 is stable and accepted:

- [ ] Decommission any 1.1-only scripts or cron jobs.
- [ ] Archive legacy artifacts that are no longer needed.
- [ ] Update documentation and training materials to refer only to 2.0.
- [ ] Close PM2-073 in the backlog with a short summary of the cutover date and outcome.

