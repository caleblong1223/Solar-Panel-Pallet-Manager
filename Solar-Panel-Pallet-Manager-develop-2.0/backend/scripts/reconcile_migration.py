#!/usr/bin/env python3
"""Basic post-migration reconciliation report."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from migrate_legacy_data import DEFAULT_CUSTOMERS_XLSX, parse_customer_rows

ROOT = Path(__file__).resolve().parents[2]
LEGACY_HISTORY = ROOT / "data" / "PALLETS" / "pallet_history.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile legacy data counts with database counts")
    parser.add_argument("--history", type=Path, default=LEGACY_HISTORY)
    parser.add_argument("--customers", type=Path, default=DEFAULT_CUSTOMERS_XLSX)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on mismatch")
    return parser.parse_args()


def load_legacy_counts(history_path: Path, customers_path: Path) -> dict[str, int]:
    if not history_path.exists():
        pallets: list[dict] = []
    else:
        with history_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        pallets = data.get("pallets", [])

    customers = parse_customer_rows(customers_path)
    exports = [p for p in pallets if p.get("exported_file")]

    return {
        "customers": len(customers),
        "pallets": len(pallets),
        "items": sum(len(p.get("serial_numbers") or []) for p in pallets),
        "exports": len(exports),
    }


def load_db_counts(conn: object) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM pallets")
        pallets = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM pallet_items")
        items = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM exports")
        exports = cur.fetchone()[0]
    return {
        "customers": customers,
        "pallets": pallets,
        "items": items,
        "exports": exports,
    }


def detect_mismatches(legacy: dict[str, int], db: dict[str, int]) -> list[str]:
    keys = ["customers", "pallets", "items", "exports"]
    return [key for key in keys if legacy.get(key, 0) != db.get(key, 0)]


def main() -> None:
    args = parse_args()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL environment variable is required")

    legacy = load_legacy_counts(args.history, args.customers)

    try:
        import psycopg
    except Exception:
        print("Migration reconciliation report")
        print(f"- Legacy customers: {legacy['customers']}")
        print(f"- Legacy pallets: {legacy['pallets']}")
        print(f"- Legacy pallet items: {legacy['items']}")
        print(f"- Legacy exports: {legacy['exports']}")
        print("- DB status: unavailable (install psycopg and ensure database is running)")
        return

    with psycopg.connect(db_url) as conn:
        db = load_db_counts(conn)

    mismatches = detect_mismatches(legacy, db)
    print("Migration reconciliation report")
    print(f"- Legacy customers: {legacy['customers']}")
    print(f"- DB customers: {db['customers']}")
    print(f"- Legacy pallets: {legacy['pallets']}")
    print(f"- DB pallets: {db['pallets']}")
    print(f"- Legacy pallet items: {legacy['items']}")
    print(f"- DB pallet items: {db['items']}")
    print(f"- Legacy exports: {legacy['exports']}")
    print(f"- DB exports: {db['exports']}")

    if mismatches:
        print(f"- Status: MISMATCH ({', '.join(mismatches)})")
        if args.strict:
            raise SystemExit(1)
    else:
        print("- Status: MATCH")


if __name__ == "__main__":
    main()
