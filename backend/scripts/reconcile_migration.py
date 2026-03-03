#!/usr/bin/env python3
"""Basic post-migration reconciliation report."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_HISTORY = ROOT / "data" / "PALLETS" / "pallet_history.json"


def load_legacy_counts() -> tuple[int, int]:
    if not LEGACY_HISTORY.exists():
        return 0, 0
    with LEGACY_HISTORY.open("r", encoding="utf-8") as f:
        data = json.load(f)
    pallets = data.get("pallets", [])
    serial_count = sum(len(p.get("serial_numbers") or []) for p in pallets)
    return len(pallets), serial_count


def load_db_counts(conn: object) -> tuple[int, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pallets")
        pallets = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM pallet_items")
        items = cur.fetchone()[0]
    return pallets, items


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL environment variable is required")

    legacy_pallets, legacy_items = load_legacy_counts()

    try:
        import psycopg
    except Exception:
        print("Migration reconciliation report")
        print(f"- Legacy pallets: {legacy_pallets}")
        print(f"- Legacy pallet items: {legacy_items}")
        print("- DB status: unavailable (install psycopg and ensure database is running)")
        return

    with psycopg.connect(db_url) as conn:
        db_pallets, db_items = load_db_counts(conn)

    print("Migration reconciliation report")
    print(f"- Legacy pallets: {legacy_pallets}")
    print(f"- DB pallets: {db_pallets}")
    print(f"- Legacy pallet items: {legacy_items}")
    print(f"- DB pallet items: {db_items}")

    if legacy_pallets != db_pallets or legacy_items != db_items:
        print("- Status: MISMATCH (investigate before cutover)")
    else:
        print("- Status: MATCH")


if __name__ == "__main__":
    main()
