#!/usr/bin/env python3
"""
CI performance smoke tests for startup and barcode-scan duplicate checks.

These are intentionally lightweight and use conservative thresholds so they
catch major regressions without being flaky across CI runners.
"""

from __future__ import annotations

import os
import random
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.pallet_manager import PalletManager


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _build_history(pm: PalletManager, count: int = 15000) -> None:
    now = datetime.now()
    pallets = []
    for i in range(1, count + 1):
        pallets.append(
            {
                "pallet_number": i,
                "serial_numbers": [f"SN{i:06d}", f"ALT{i:06d}"],
                "completed_at": (now - timedelta(days=i % 40)).strftime("%Y-%m-%d %H:%M:%S"),
                "exported_file": None,
                "customer": {"display_name": "Acme | Solar" if i % 2 == 0 else "Beta | Power"},
            }
        )
    pm.data = {"pallets": pallets, "next_pallet_number": count + 1}
    assert pm.save_history()


def _naive_find(pallets: list[dict], serial_key: str) -> dict | None:
    for pallet in pallets:
        if pallet.get("reset", False):
            continue
        if serial_key in {str(s).strip().upper() for s in pallet.get("serial_numbers", [])}:
            return {
                "pallet_number": pallet.get("pallet_number"),
                "completed_at": pallet.get("completed_at"),
                "is_current": False,
            }
    return None


def test_ci_startup_and_scan_perf_smoke():
    startup_limit_s = _env_float("PM_CI_STARTUP_LIMIT_S", 4.0)
    scan_limit_s = _env_float("PM_CI_SCAN_BATCH_LIMIT_S", 2.5)
    relative_factor = _env_float("PM_CI_SCAN_RELATIVE_FACTOR", 0.7)

    with tempfile.TemporaryDirectory() as temp_dir:
        history_file = Path(temp_dir) / "pallet_history.json"

        # Seed realistic history first.
        seeder = PalletManager(history_file, defer_load=False)
        _build_history(seeder, count=15000)

        # Startup/load smoke check.
        t0 = time.perf_counter()
        pm = PalletManager(history_file, defer_load=False)
        startup_s = time.perf_counter() - t0
        assert startup_s <= startup_limit_s, f"Startup/load regression: {startup_s:.3f}s > {startup_limit_s:.3f}s"

        # Build mixed query set for duplicate scan checks.
        existing = [f"SN{i:06d}" for i in range(1000, 2500)]
        missing = [f"MISS{i:06d}" for i in range(1000)]
        queries = existing + missing
        random.shuffle(queries)

        # Indexed path timing.
        t1 = time.perf_counter()
        indexed_results = [pm.is_serial_on_any_pallet(q) for q in queries]
        indexed_s = time.perf_counter() - t1
        assert indexed_s <= scan_limit_s, f"Scan regression: {indexed_s:.3f}s > {scan_limit_s:.3f}s"

        # Naive baseline timing and parity on same queries.
        pallets = pm.data["pallets"]
        t2 = time.perf_counter()
        naive_results = [_naive_find(pallets, q.strip().upper()) for q in queries]
        naive_s = time.perf_counter() - t2

        assert indexed_results == naive_results
        assert indexed_s <= naive_s * relative_factor, (
            f"Indexed scan too slow vs naive: indexed={indexed_s:.3f}s naive={naive_s:.3f}s "
            f"required_factor={relative_factor:.2f}"
        )
