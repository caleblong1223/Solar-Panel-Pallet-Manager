#!/usr/bin/env python3
"""
Seed a single default customer for the 2.0 app.

This is intentionally opinionated: it clears the customers table and inserts
exactly one active customer matching the legacy default:

  "Josh Atwood | Future Solutions"

The database connection is taken from Settings / SessionLocal, so it will target
whichever DATABASE_URL the backend is configured to use (for Docker, the
postgres://pallet_user:... URL).
"""

from __future__ import annotations

from app.db.session import SessionLocal
from app.models.pallet import Customer


def main() -> None:
    db = SessionLocal()
    try:
        # Remove any existing legacy-imported customers.
        deleted = db.query(Customer).delete()

        customer = Customer(
            display_name="Josh Atwood | Future Solutions",
            contact_name="Josh Atwood",
            business_name="Future Solutions",
            email=None,
            phone=None,
            is_active=True,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        print("Seeded default customer.")
        print(f"- previous_rows_deleted: {deleted}")
        print(f"- id: {customer.id}")
        print(f"- display_name: {customer.display_name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

