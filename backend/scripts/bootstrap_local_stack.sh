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

seed_admin_and_roles() {
  log "Seeding baseline roles and admin user..."
  DATABASE_URL="$SCRIPT_DATABASE_URL" python - <<'PY'
import os
import psycopg

db_url = os.environ["DATABASE_URL"]
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO roles (id,name,description) VALUES (1,'admin','Administrator') ON CONFLICT (name) DO NOTHING")
        cur.execute("INSERT INTO roles (id,name,description) VALUES (2,'packout_operator','Packout Operator') ON CONFLICT (name) DO NOTHING")
        cur.execute("INSERT INTO roles (id,name,description) VALUES (3,'purchasing_manager','Purchasing Manager') ON CONFLICT (name) DO NOTHING")
        cur.execute(
            """
            INSERT INTO users (id, username, email, password_hash, is_active)
            VALUES (1, 'admin', 'admin@local', 'bootstrap-reset-required', true)
            ON CONFLICT (username) DO NOTHING
            """
        )
        cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (1,1) ON CONFLICT DO NOTHING")
    conn.commit()
print("seeded")
PY
}

require_cmd docker
require_cmd psql

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

seed_admin_and_roles

log "Applying legacy data migration..."
DATABASE_URL="$SCRIPT_DATABASE_URL" python scripts/migrate_legacy_data.py --apply

log "Running reconciliation report..."
DATABASE_URL="$SCRIPT_DATABASE_URL" python scripts/reconcile_migration.py

log "Done."
log "API: http://localhost:8000"
log "MinIO Console: http://localhost:9001"
log "Postgres: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
