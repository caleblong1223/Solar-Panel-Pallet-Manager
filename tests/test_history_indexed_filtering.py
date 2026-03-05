#!/usr/bin/env python3
"""
Regression and performance sanity checks for indexed history filtering.
"""

from __future__ import annotations

import random
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.pallet_manager import PalletManager


def _customer_display_name(pallet: dict) -> str | None:
    customer_info = pallet.get("customer", {})
    if not customer_info:
        return None
    display_name = customer_info.get("display_name")
    if display_name:
        return display_name
    name = customer_info.get("name", "")
    business = customer_info.get("business", "")
    return f"{name} | {business}" if name and business else None


def _naive_filter(pm: PalletManager, filter_value: str, customer_filter: str, search_term: str):
    all_pallets = pm.data.get("pallets", [])
    valid_pallets = [p for p in all_pallets if pm.is_pallet_record_file_available(p)]
    pallets = pm._filter_pallets_by_date(valid_pallets, filter_value) if hasattr(pm, "_filter_pallets_by_date") else valid_pallets

    # Mirror pallet_history_window date logic directly (PalletManager has no public helper).
    if filter_value != "All":
        now = datetime.now()
        filtered = []
        for pallet in valid_pallets:
            completed_at = pallet.get("completed_at", "")
            if not completed_at:
                continue
            try:
                pallet_date = datetime.strptime(completed_at.split()[0], "%Y-%m-%d")
            except (ValueError, IndexError):
                continue
            days_diff = (now.date() - pallet_date.date()).days
            if filter_value == "Today" and days_diff == 0:
                filtered.append(pallet)
            elif filter_value == "This Week" and 0 <= days_diff <= 6:
                filtered.append(pallet)
            elif filter_value == "This Month" and pallet_date.year == now.year and pallet_date.month == now.month:
                filtered.append(pallet)
            elif filter_value == "This Year" and pallet_date.year == now.year:
                filtered.append(pallet)
        pallets = filtered
    else:
        pallets = valid_pallets

    if customer_filter != "ALL":
        pallets = [p for p in pallets if _customer_display_name(p) == customer_filter]

    if search_term:
        search_key = search_term.strip().upper()
        pallets = [
            p for p in pallets
            if any(search_key == str(serial).strip().upper() for serial in p.get("serial_numbers", []))
        ]

    pallets.sort(key=lambda x: x.get("pallet_number", 0), reverse=True)
    return pallets


def _build_sample_history(pm: PalletManager, count: int = 12000):
    now = datetime.now()
    pallets = []
    for i in range(1, count + 1):
        completed = (now - timedelta(days=i % 45)).strftime("%Y-%m-%d %H:%M:%S")
        customer = "Acme | Solar" if i % 3 == 0 else "Beta | Power"
        pallets.append(
            {
                "pallet_number": i,
                "serial_numbers": [f"SN{i:06d}", f"ALT{i:06d}"],
                "completed_at": completed,
                "exported_file": None,
                "customer": {"display_name": customer},
            }
        )
    # Add a few reset/missing-file records to preserve edge behavior.
    pallets.append(
        {
            "pallet_number": count + 1,
            "serial_numbers": ["RESET123"],
            "completed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "exported_file": None,
            "reset": True,
            "customer": {"display_name": "Acme | Solar"},
        }
    )
    pallets.append(
        {
            "pallet_number": count + 2,
            "serial_numbers": ["MISS123"],
            "completed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "exported_file": "missing.xlsx",
            "customer": {"display_name": "Acme | Solar"},
        }
    )
    pm.data = {"pallets": pallets, "next_pallet_number": count + 3}
    pm.save_history()


def test_indexed_filtering_correctness_and_speed():
    with tempfile.TemporaryDirectory() as temp_dir:
        history_file = Path(temp_dir) / "pallet_history.json"
        pm = PalletManager(history_file, defer_load=False)
        _build_sample_history(pm, count=12000)

        scenarios = [
            ("All", "ALL", ""),
            ("This Week", "ALL", ""),
            ("This Month", "Acme | Solar", ""),
            ("This Year", "Beta | Power", "SN000321"),
            ("Today", "ALL", "ALT000005"),
        ]

        for filter_value, customer_filter, search_term in scenarios:
            expected = _naive_filter(pm, filter_value, customer_filter, search_term)
            actual = pm.filter_history_for_ui(filter_value, customer_filter, search_term)
            assert [p.get("pallet_number") for p in actual] == [p.get("pallet_number") for p in expected]

        filter_value, customer_filter, search_term = random.choice(scenarios)
        t0 = time.perf_counter()
        _naive_filter(pm, filter_value, customer_filter, search_term)
        naive_s = time.perf_counter() - t0

        t1 = time.perf_counter()
        pm.filter_history_for_ui(filter_value, customer_filter, search_term)
        indexed_s = time.perf_counter() - t1

        # Performance sanity: indexed path should not be materially slower.
        assert indexed_s <= naive_s * 1.2
