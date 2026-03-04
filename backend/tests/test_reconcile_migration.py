from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from openpyxl import Workbook

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

MODULE_PATH = SCRIPTS_DIR / "reconcile_migration.py"
SPEC = importlib.util.spec_from_file_location("reconcile_migration", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

detect_mismatches = MODULE.detect_mismatches
load_legacy_counts = MODULE.load_legacy_counts


def test_load_legacy_counts_includes_customers_pallets_items_exports(tmp_path: Path) -> None:
    history = tmp_path / "pallet_history.json"
    history.write_text(
        json.dumps(
            {
                "pallets": [
                    {"serial_numbers": ["A", "B"], "exported_file": "/tmp/a.xlsx"},
                    {"serial_numbers": ["C"], "exported_file": None},
                ]
            }
        ),
        encoding="utf-8",
    )

    customers = tmp_path / "customers.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Name", "Business"])
    ws.append(["A", "BizA"])
    ws.append(["B", "BizB"])
    wb.save(customers)

    counts = load_legacy_counts(history, customers)
    assert counts == {"customers": 2, "pallets": 2, "items": 3, "exports": 1}


def test_detect_mismatches_reports_changed_keys() -> None:
    legacy = {"customers": 2, "pallets": 3, "items": 4, "exports": 1}
    db = {"customers": 2, "pallets": 1, "items": 4, "exports": 0}
    mismatches = detect_mismatches(legacy, db)
    assert mismatches == ["pallets", "exports"]
