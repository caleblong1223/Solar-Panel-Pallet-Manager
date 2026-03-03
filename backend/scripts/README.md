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

## 1) Dry run migration

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/migrate_legacy_data.py --dry-run
```

## 2) Apply migration

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/migrate_legacy_data.py --apply
```

## 3) Reconcile

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/reconcile_migration.py
```

## 4) Seed auth baseline manually

```bash
cd backend
export DATABASE_URL='postgresql://pallet_user:pallet_pass@localhost:5433/pallet_manager'
python scripts/seed_auth_data.py --username admin --email admin@local.test --password 'ChangeMe123!'
```

Notes:
- Customer import uses `data/CUSTOMERS/customers.xlsx` if available.
- Legacy pallet history import uses `data/PALLETS/pallet_history.json`.
- Export records are indexed from `exported_file` path in legacy history.
- If `--default-user-id` does not exist in `users`, migration falls back to `NULL` for `created_by`/`completed_by`/`added_by` fields to satisfy FK constraints.
