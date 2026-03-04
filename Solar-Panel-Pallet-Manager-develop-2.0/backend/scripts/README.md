# Migration Scripts

## 0) One-command local bootstrap (recommended)

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/bootstrap_local_stack.sh
```

This command will:
- start Docker services (`postgres`, `minio`, `backend`)
- set up backend virtualenv and dependencies
- run Alembic migrations
- seed baseline roles/admin
- apply legacy data migration
- run reconciliation

Defaults use:
- Postgres `localhost:5433`
- DB `pallet_manager`
- User `pallet_user`
- Password `pallet_pass`

Override defaults if needed:

```bash
DB_PORT=5434 DB_PASSWORD='your_pass' ./backend/scripts/bootstrap_local_stack.sh
```

Admin seed password is required for bootstrap/setup:

```bash
SEED_ADMIN_PASSWORD='set-a-strong-password' ./backend/scripts/bootstrap_local_stack.sh
```

## 0b) First-time setup wrapper

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
SEED_ADMIN_PASSWORD='set-a-strong-password' ./backend/scripts/first_time_setup.sh
```

Useful options:

```bash
./backend/scripts/first_time_setup.sh --dry-run --no-docker
```

This wrapper runs (in order): dependency install, alembic upgrade, auth seeding, legacy migration apply, and strict reconciliation.

## 1) Backup stack (Postgres + MinIO)

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/backup_stack.sh
```

## 2) Restore stack from backup directory

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/restore_stack.sh backups/<timestamp>
```

## 3) Run full restore drill (backup + restore + checks)

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/restore_drill.sh
```

See `docs/BACKUP_RESTORE_RUNBOOK.md` for schedule and drill evidence checklist.

## 4) Dry run migration

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/migrate_legacy_data.py --dry-run
```

## 5) Apply migration

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/migrate_legacy_data.py --apply
```

## 6) Reconcile

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/reconcile_migration.py
```

## 7) Seed auth baseline manually

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/seed_auth_data.py --username admin --email admin@local.test --password "$SEED_ADMIN_PASSWORD"
```

Notes:
- Customer import uses `data/CUSTOMERS/customers.xlsx` if available.
- Legacy pallet history import uses `data/PALLETS/pallet_history.json`.
- Export records are indexed from `exported_file` path in legacy history.
- If `--default-user-id` does not exist in `users`, migration falls back to `NULL` for `created_by`/`completed_by`/`added_by` fields to satisfy FK constraints.
