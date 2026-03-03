from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migrate_legacy_data.py"
SPEC = importlib.util.spec_from_file_location("migrate_legacy_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

insert_export = MODULE.insert_export
insert_pallet = MODULE.insert_pallet
insert_pallet_items = MODULE.insert_pallet_items


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self._fetchone_result = None
        self.rowcount = 0

    def execute(self, query: str, params: tuple) -> None:
        self.calls.append((query, params))
        query_lower = " ".join(query.lower().split())
        if "select id from pallets" in query_lower:
            self._fetchone_result = None
        elif "insert into pallets" in query_lower:
            self._fetchone_result = (123,)
        elif "select id from exports" in query_lower:
            self._fetchone_result = None
        elif "insert into exports" in query_lower:
            self._fetchone_result = None
        elif "insert into pallet_items" in query_lower:
            self.rowcount = 1

    def fetchone(self):  # noqa: ANN001
        return self._fetchone_result


def test_insert_pallet_items_uses_one_based_slot_index() -> None:
    cur = FakeCursor()
    count = insert_pallet_items(cur, pallet_id=10, serials=["A", "B"], user_id=1, apply=True)
    assert count == 2
    insert_calls = [c for c in cur.calls if "insert into pallet_items" in c[0].lower()]
    assert len(insert_calls) == 2
    assert insert_calls[0][1][2] == 1
    assert insert_calls[1][1][2] == 2


def test_insert_pallet_returns_inserted_flag() -> None:
    cur = FakeCursor()
    pallet = {"pallet_number": 7, "completed_at": "2026-01-06 12:00:00", "panel_type": "450WT"}
    pallet_id, inserted = insert_pallet(cur, pallet, user_id=1, apply=True)
    assert pallet_id == 123
    assert inserted is True


def test_insert_export_skips_existing() -> None:
    class ExistingExportCursor(FakeCursor):
        def execute(self, query: str, params: tuple) -> None:
            self.calls.append((query, params))
            query_lower = " ".join(query.lower().split())
            if "select id from exports" in query_lower:
                self._fetchone_result = (999,)
            else:
                super().execute(query, params)

    cur = ExistingExportCursor()
    inserted = insert_export(
        cur,
        pallet_id=5,
        pallet={"exported_file": "/tmp/path/export.xlsx", "panel_type": "legacy"},
        user_id=1,
        apply=True,
    )
    assert inserted == 0
