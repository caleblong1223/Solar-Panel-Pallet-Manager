from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from openpyxl import Workbook

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migrate_legacy_data.py"
SPEC = importlib.util.spec_from_file_location("migrate_legacy_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
parse_customer_rows = MODULE.parse_customer_rows


def _write_workbook(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_parse_customer_rows_supports_current_legacy_columns(tmp_path: Path) -> None:
    workbook = tmp_path / "customers.xlsx"
    _write_workbook(
        workbook,
        headers=["Name", "Business", "Address", "City", "State", "Zip Code"],
        rows=[
            ["Josh Atwood", "Future Solutions Inc", "2616 Glenview Dr", "Elkhart", "IN", "46514"],
            ["Only Name", "", "", "", "", ""],
            ["", "Only Biz", "", "", "", ""],
        ],
    )
    parsed = parse_customer_rows(workbook)
    assert len(parsed) == 3
    assert parsed[0]["display_name"] == "Josh Atwood | Future Solutions Inc"
    assert parsed[0]["contact_name"] == "Josh Atwood"
    assert parsed[0]["business_name"] == "Future Solutions Inc"
    assert parsed[0]["email"] is None
    assert parsed[0]["phone"] is None
    assert parsed[1]["display_name"] == "Only Name"
    assert parsed[2]["display_name"] == "Only Biz"


def test_parse_customer_rows_supports_email_and_phone_aliases(tmp_path: Path) -> None:
    workbook = tmp_path / "customers_with_contact.xlsx"
    _write_workbook(
        workbook,
        headers=["Contact", "Company", "Email Address", "Phone Number"],
        rows=[["A Person", "A Co", "a@example.com", "555-1111"]],
    )
    parsed = parse_customer_rows(workbook)
    assert len(parsed) == 1
    assert parsed[0]["display_name"] == "A Person | A Co"
    assert parsed[0]["email"] == "a@example.com"
    assert parsed[0]["phone"] == "555-1111"
