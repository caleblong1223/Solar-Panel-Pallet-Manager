#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
COMPOSE_FILE="$ROOT_DIR/docker-compose.intranet.yml"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_NAME="${DB_NAME:-pallet_manager}"
DB_USER="${DB_USER:-pallet_user}"
DB_PASSWORD="${DB_PASSWORD:-pallet_pass}"

ALEMBIC_DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
SCRIPT_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

log() {
  echo "[bootstrap] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: $name"
    exit 1
  fi
}

wait_for_postgres() {
  log "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
  local attempts=0
  until PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 60 ]; then
      echo "Postgres did not become ready in time."
      exit 1
    fi
    sleep 2
  done
  log "Postgres is ready."
}

require_cmd docker
require_cmd psql
require_env SEED_ADMIN_PASSWORD

log "Starting Docker services..."
docker compose -f "$COMPOSE_FILE" up -d

cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  log "Creating backend virtualenv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

log "Installing/updating backend dependencies..."
python -m pip install --upgrade pip setuptools wheel >/dev/null
pip install -e . >/dev/null

wait_for_postgres

log "Running Alembic migrations..."
DATABASE_URL="$ALEMBIC_DATABASE_URL" python -m alembic upgrade head

log "Seeding baseline roles and admin user..."
DATABASE_URL="$SCRIPT_DATABASE_URL" python scripts/seed_auth_data.py --username "${SEED_ADMIN_USERNAME:-admin}" --email "${SEED_ADMIN_EMAIL:-admin@local.test}" --password "${SEED_ADMIN_PASSWORD}"

log "Applying legacy data migration..."
DATABASE_URL="$SCRIPT_DATABASE_URL" python scripts/migrate_legacy_data.py --apply

log "Running reconciliation report..."
DATABASE_URL="$SCRIPT_DATABASE_URL" python scripts/reconcile_migration.py --strict

log "Done."
log "API: http://localhost:8000"
log "MinIO Console: http://localhost:9001"
log "Postgres: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
