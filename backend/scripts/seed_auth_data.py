#!/usr/bin/env python3
"""Seed baseline roles and a default admin user."""

from __future__ import annotations

import argparse
import os

import bcrypt
import psycopg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed roles and a default admin user")
    parser.add_argument("--username", default=os.getenv("SEED_ADMIN_USERNAME", "admin"))
    parser.add_argument("--email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@local.test"))
    parser.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD"))
    parser.add_argument("--inactive", action="store_true", help="Create user as inactive")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL environment variable is required")
    if not args.password:
        raise SystemExit("Admin password is required (set --password or SEED_ADMIN_PASSWORD)")

    role_names = ["admin", "packout_operator", "purchasing_manager"]
    password_hash = bcrypt.hashpw(args.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            role_ids: dict[str, int] = {}
            for role_name in role_names:
                cur.execute(
                    """
                    INSERT INTO roles (name, description)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                    RETURNING id
                    """,
                    (role_name, f"Seeded role: {role_name}"),
                )
                role_ids[role_name] = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                  email = EXCLUDED.email,
                  password_hash = EXCLUDED.password_hash,
                  is_active = EXCLUDED.is_active
                RETURNING id
                """,
                (args.username, args.email, password_hash, not args.inactive),
            )
            user_id = cur.fetchone()[0]

            for role_name in role_names:
                cur.execute(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                    """,
                    (user_id, role_ids[role_name]),
                )
        conn.commit()

    print("Seed complete")
    print(f"- user_id: {user_id}")
    print(f"- username: {args.username}")
    print(f"- roles: {', '.join(role_names)}")


if __name__ == "__main__":
    main()
