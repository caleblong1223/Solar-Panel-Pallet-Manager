# Backup and Restore Runbook (PM2-071)

This runbook defines backup schedule, restore steps, and restore drill evidence requirements for Pallet Manager 2.0.

## Scope

- PostgreSQL database (`pallet_manager`)
- MinIO object storage buckets:
  - `pallet-exports`
  - `simulator-imports`

## Scripts

- `backend/scripts/backup_stack.sh`
- `backend/scripts/restore_stack.sh`
- `backend/scripts/restore_drill.sh`

## Required Tools

- `psql`, `pg_dump`, `pg_restore`
- `docker` (used to run `minio/mc` client)

## Environment Variables

Optional overrides:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `MINIO_BUCKET_EXPORTS`, `MINIO_BUCKET_IMPORTS`
- `BACKUP_ROOT`

## Backup Procedure

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/backup_stack.sh
```

Output:

- `backups/<timestamp>/postgres/<db>.dump`
- `backups/<timestamp>/minio/<bucket>/*`
- `backups/<timestamp>/metadata.env`

## Restore Procedure

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/restore_stack.sh backups/<timestamp>
```

Notes:

- Postgres DB is dropped and recreated before restore.
- Target MinIO buckets are recreated and mirrored from backup.

## Restore Drill Procedure

```bash
cd "/Users/caleblong/Documents/Crossroads Solar/Pallet Manager 1.1"
./backend/scripts/restore_drill.sh
```

The drill executes:

1. New backup capture
2. Full restore from latest backup
3. Validation checks:
   - SQL connectivity and `users` table row count query
   - MinIO bucket accessibility checks

Success criteria:

- Script exits with code `0`
- Output contains `SUCCESS: backup+restore validation completed`

## Schedule Recommendation

- Daily backup at `02:00` local time.
- Monthly restore drill on first Monday at `09:00` local time.

Example cron entries:

```cron
0 2 * * * cd /Users/caleblong/Documents/Crossroads\ Solar/Pallet\ Manager\ 1.1 && ./backend/scripts/backup_stack.sh >> LOGS/backup.log 2>&1
0 9 1-7 * 1 cd /Users/caleblong/Documents/Crossroads\ Solar/Pallet\ Manager\ 1.1 && ./backend/scripts/restore_drill.sh >> LOGS/restore_drill.log 2>&1
```

## Drill Evidence to Capture

- Timestamped command output
- Backup directory name used
- Post-restore SQL query result
- MinIO bucket check result
- Any remediation actions if failure occurs
