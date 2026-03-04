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

USE_DOCKER=1
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --no-docker) USE_DOCKER=0 ;;
    --dry-run) DRY_RUN=1 ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--no-docker] [--dry-run]"
      exit 1
      ;;
  esac
done

log() {
  echo "[setup] $*"
}

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: $*"
  else
    eval "$@"
  fi
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: $name"
    exit 1
  fi
}

log "Starting first-time setup"
log "DB: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
require_env SEED_ADMIN_PASSWORD

if [ "$USE_DOCKER" -eq 1 ]; then
  run_cmd "docker compose -f '$COMPOSE_FILE' up -d"
fi

run_cmd "cd '$BACKEND_DIR' && python3 -m venv .venv || true"
run_cmd "cd '$BACKEND_DIR' && . .venv/bin/activate && python -m pip install --upgrade pip setuptools wheel"
run_cmd "cd '$BACKEND_DIR' && . .venv/bin/activate && pip install -e ."
run_cmd "cd '$BACKEND_DIR' && . .venv/bin/activate && DATABASE_URL='$ALEMBIC_DATABASE_URL' python -m alembic upgrade head"
run_cmd "cd '$BACKEND_DIR' && . .venv/bin/activate && DATABASE_URL='$SCRIPT_DATABASE_URL' python scripts/seed_auth_data.py --username '${SEED_ADMIN_USERNAME:-admin}' --email '${SEED_ADMIN_EMAIL:-admin@local.test}' --password '${SEED_ADMIN_PASSWORD}'"
run_cmd "cd '$BACKEND_DIR' && . .venv/bin/activate && DATABASE_URL='$SCRIPT_DATABASE_URL' python scripts/migrate_legacy_data.py --apply"
run_cmd "cd '$BACKEND_DIR' && . .venv/bin/activate && DATABASE_URL='$SCRIPT_DATABASE_URL' python scripts/reconcile_migration.py --strict"

log "Setup complete"
