# Cursor Taskmaster Prompt Pack - Pallet Manager 2.0

Use this with your Cursor agent to generate a full task list from existing docs and scaffold.

## Primary Context Files

- `docs/PRD_PALLET_MANAGER_2_0.md`
- `docs/TDD_PALLET_MANAGER_2_0.md`
- `backend/alembic/versions/20260303_0001_initial_schema.py`
- `backend/schema_v1.sql`
- `docker-compose.intranet.yml`
- `backend/app/main.py`
- `frontend/src/App.tsx`

## Prompt to Generate Taskmaster Backlog

```text
You are generating an execution-grade task backlog for Pallet Manager 2.0.
Use these local files as source of truth:
- docs/PRD_PALLET_MANAGER_2_0.md
- docs/TDD_PALLET_MANAGER_2_0.md
- backend/alembic/versions/20260303_0001_initial_schema.py
- backend/schema_v1.sql
- docker-compose.intranet.yml
- backend/app/**
- frontend/src/**

Produce a task list grouped by milestone:
1) Platform foundation
2) Auth and RBAC
3) Pallet domain APIs
4) Simulator import pipeline
5) Export + MinIO integration
6) React/Tauri UI screens
7) Migration from legacy JSON/files
8) QA/UAT/Release

For every task include:
- ID
- Title
- Description
- Dependencies
- Acceptance criteria
- Estimated effort (S/M/L)
- Risk level
- Owner role (backend/frontend/fullstack/devops/qa)

Also output:
- Critical path tasks only
- Week-by-week suggested sequence
- First 10 tasks to start immediately
```
