#!/usr/bin/env python3
"""Run the backend locally with a SQLite database and optional auth seeding."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Pallet Manager backend locally without Docker.")
    parser.add_argument("--database-url", default="", help="Override DATABASE_URL (default: sqlite:///./local_offline.db)")
    parser.add_argument("--db-file", default="local_offline.db", help="SQLite file path when --database-url is not provided")
    parser.add_argument("--host", default="0.0.0.0", help="Uvicorn host (default: 0.0.0.0)")
    parser.add_argument("--port", default=8000, type=int, help="Uvicorn port (default: 8000)")
    parser.add_argument("--seed-admin-username", default="admin", help="Admin username for optional seed")
    parser.add_argument("--seed-admin-email", default="admin@local.test", help="Admin email for optional seed")
    parser.add_argument(
        "--seed-admin-password",
        default="",
        help="If provided, run scripts/seed_auth_data.py before startup",
    )
    return parser.parse_args()


def run(cmd: list[str], env: dict[str, str], cwd: Path) -> None:
    print(f"[run_local_backend] {' '.join(cmd)}")
    subprocess.run(cmd, env=env, cwd=str(cwd), check=True)


def main() -> None:
    args = parse_args()
    backend_dir = Path(__file__).resolve().parents[1]

    database_url = args.database_url.strip()
    if not database_url:
        db_file = Path(args.db_file).expanduser()
        if not db_file.is_absolute():
            db_file = backend_dir / db_file
        db_file.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{db_file}"

    env = dict(os.environ)
    env["DATABASE_URL"] = database_url

    print(f"[run_local_backend] DATABASE_URL={database_url}")

    run([sys.executable, "-m", "alembic", "upgrade", "head"], env, backend_dir)

    seed_password = args.seed_admin_password.strip() or os.getenv("SEED_ADMIN_PASSWORD", "").strip()
    if seed_password:
        run(
            [
                sys.executable,
                "scripts/seed_auth_data.py",
                "--username",
                args.seed_admin_username,
                "--email",
                args.seed_admin_email,
                "--password",
                seed_password,
            ],
            env,
            backend_dir,
        )
    else:
        print("[run_local_backend] Skipping auth seed (no seed password provided).")

    run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        env,
        backend_dir,
    )


if __name__ == "__main__":
    main()
