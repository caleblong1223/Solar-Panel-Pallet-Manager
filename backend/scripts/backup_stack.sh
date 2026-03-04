#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

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

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }
}

log() {
  echo "[backup] $*"
}

require_cmd pg_dump
require_cmd docker

mkdir -p "$BACKUP_DIR/postgres" "$BACKUP_DIR/minio"

log "Backing up Postgres database ${DB_NAME}"
PGPASSWORD="$DB_PASSWORD" pg_dump \
  --host "$DB_HOST" \
  --port "$DB_PORT" \
  --username "$DB_USER" \
  --dbname "$DB_NAME" \
  --format custom \
  --file "$BACKUP_DIR/postgres/${DB_NAME}.dump"

log "Backing up MinIO buckets (${MINIO_BUCKET_EXPORTS}, ${MINIO_BUCKET_IMPORTS})"
docker run --rm \
  --entrypoint /bin/sh \
  -v "$BACKUP_DIR/minio:/backup" \
  minio/mc -c "
    mc alias set local '${MINIO_ENDPOINT}' '${MINIO_ACCESS_KEY}' '${MINIO_SECRET_KEY}' >/dev/null &&
    mc mb local/${MINIO_BUCKET_EXPORTS} >/dev/null 2>&1 || true &&
    mc mb local/${MINIO_BUCKET_IMPORTS} >/dev/null 2>&1 || true &&
    mc mirror --overwrite local/${MINIO_BUCKET_EXPORTS} /backup/${MINIO_BUCKET_EXPORTS} &&
    mc mirror --overwrite local/${MINIO_BUCKET_IMPORTS} /backup/${MINIO_BUCKET_IMPORTS}
  "

cat > "$BACKUP_DIR/metadata.env" <<META
TIMESTAMP=${TIMESTAMP}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
MINIO_ENDPOINT=${MINIO_ENDPOINT}
MINIO_BUCKET_EXPORTS=${MINIO_BUCKET_EXPORTS}
MINIO_BUCKET_IMPORTS=${MINIO_BUCKET_IMPORTS}
META

log "Backup complete: ${BACKUP_DIR}"
