#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_dir>"
  exit 1
fi

BACKUP_DIR="$1"
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory does not exist: $BACKUP_DIR"
  exit 1
fi

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

DUMP_FILE="$BACKUP_DIR/postgres/${DB_NAME}.dump"
if [ ! -f "$DUMP_FILE" ]; then
  echo "Postgres dump not found: $DUMP_FILE"
  exit 1
fi

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }
}

log() {
  echo "[restore] $*"
}

require_cmd psql
require_cmd pg_restore
require_cmd docker

log "Restoring Postgres database ${DB_NAME}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${DB_NAME};
CREATE DATABASE ${DB_NAME};
SQL

PGPASSWORD="$DB_PASSWORD" pg_restore \
  --host "$DB_HOST" \
  --port "$DB_PORT" \
  --username "$DB_USER" \
  --dbname "$DB_NAME" \
  --clean \
  --if-exists \
  --no-owner \
  "$DUMP_FILE"

log "Restoring MinIO buckets (${MINIO_BUCKET_EXPORTS}, ${MINIO_BUCKET_IMPORTS})"
docker run --rm \
  --entrypoint /bin/sh \
  -v "$BACKUP_DIR/minio:/backup" \
  minio/mc -c "
    mc alias set local '${MINIO_ENDPOINT}' '${MINIO_ACCESS_KEY}' '${MINIO_SECRET_KEY}' >/dev/null &&
    mc rb --force local/${MINIO_BUCKET_EXPORTS} >/dev/null 2>&1 || true &&
    mc rb --force local/${MINIO_BUCKET_IMPORTS} >/dev/null 2>&1 || true &&
    mc mb local/${MINIO_BUCKET_EXPORTS} >/dev/null &&
    mc mb local/${MINIO_BUCKET_IMPORTS} >/dev/null &&
    if [ -d /backup/${MINIO_BUCKET_EXPORTS} ]; then mc mirror --overwrite /backup/${MINIO_BUCKET_EXPORTS} local/${MINIO_BUCKET_EXPORTS}; fi &&
    if [ -d /backup/${MINIO_BUCKET_IMPORTS} ]; then mc mirror --overwrite /backup/${MINIO_BUCKET_IMPORTS} local/${MINIO_BUCKET_IMPORTS}; fi
  "

log "Restore complete from: ${BACKUP_DIR}"
