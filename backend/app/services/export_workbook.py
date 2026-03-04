from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from app.models.pallet import Pallet


class ExportWorkbookError(RuntimeError):
    pass


def _repo_root() -> Path:
    # backend/app/services -> repo root
    return Path(__file__).resolve().parents[3]


def _template_path_for_capacity(max_panels: int) -> Path:
    if max_panels in (25, 26):
        template_name = "26.xlsx"
    elif max_panels == 30:
        template_name = "30.xlsx"
    elif max_panels == 35:
        template_name = "35.xlsx"
    else:
        raise ExportWorkbookError(
            f"Unsupported panel capacity {max_panels}. Allowed capacities: 25, 26, 30, 35."
        )

    root = _repo_root()
    candidates = [
        root / "data" / "EXCEL" / template_name,
        root / "EXCEL" / template_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ExportWorkbookError(
        f"Template workbook {template_name} not found. Checked: "
        + ", ".join(str(path) for path in candidates)
    )


def _build_b3_value(panel_type: str, pallet_number: int, export_dt: datetime) -> str:
    # Match 1.1 format: {PanelType}{MDYYYY}-{PalletNumber}
    # Example: 200WT162025-1 for Jan 6, 2025 pallet 1
    date_mdyyyy = f"{export_dt.month}{export_dt.day}{export_dt.year}"
    return f"{panel_type}{date_mdyyyy}-{pallet_number}"


def generate_export_workbook_bytes(pallet: Pallet, panel_type: str, export_dt: datetime | None = None) -> bytes:
    when = export_dt or datetime.now()
    template_path = _template_path_for_capacity(pallet.max_panels)
    workbook = load_workbook(template_path)
    try:
        if "PALLET SHEET" not in workbook.sheetnames:
            raise ExportWorkbookError(f"Template {template_path.name} missing 'PALLET SHEET' worksheet.")
        sheet = workbook["PALLET SHEET"]

        # 1.1 compatibility cells.
        sheet["B1"] = panel_type
        sheet["G3"] = when
        sheet["B3"] = _build_b3_value(panel_type, pallet.pallet_number, when)

        # Clear serial slots then write current pallet serials into B5..B30
        for row in range(5, 31):
            sheet.cell(row=row, column=2).value = None
        for idx, item in enumerate(sorted(pallet.items, key=lambda value: value.slot_index), start=5):
            if idx > 30:
                break
            sheet.cell(row=idx, column=2).value = item.serial

        out = BytesIO()
        workbook.save(out)
        return out.getvalue()
    finally:
        workbook.close()
