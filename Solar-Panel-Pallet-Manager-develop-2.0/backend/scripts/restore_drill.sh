#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"

"$ROOT_DIR/backend/scripts/backup_stack.sh"
LATEST_BACKUP="$(ls -1dt "$BACKUP_ROOT"/* | head -n 1)"

if [ -z "${LATEST_BACKUP:-}" ] || [ ! -d "$LATEST_BACKUP" ]; then
  echo "Failed to identify latest backup in $BACKUP_ROOT"
  exit 1
fi

"$ROOT_DIR/backend/scripts/restore_stack.sh" "$LATEST_BACKUP"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_NAME="${DB_NAME:-pallet_manager}"
DB_USER="${DB_USER:-pallet_user}"
DB_PASSWORD="${DB_PASSWORD:-pallet_pass}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://host.docker.internal:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET_EXPORTS="${MINIO_BUCKET_EXPORTS:-pallet-exports}"
MINIO_BUCKET_IMPORTS="${MINIO_BUCKET_IMPORTS:-simulator-imports}"

echo "[drill] Post-restore checks"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) AS users FROM users;"

docker run --rm --entrypoint /bin/sh minio/mc -c "
  mc alias set local '${MINIO_ENDPOINT}' '${MINIO_ACCESS_KEY}' '${MINIO_SECRET_KEY}' >/dev/null &&
  mc ls local/${MINIO_BUCKET_EXPORTS} >/dev/null &&
  mc ls local/${MINIO_BUCKET_IMPORTS} >/dev/null
"

echo "[drill] SUCCESS: backup+restore validation completed"
echo "[drill] Backup used: $LATEST_BACKUP"
