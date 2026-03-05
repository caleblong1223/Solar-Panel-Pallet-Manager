from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.services.export_generator import _find_pallet_workbook
from app.services.export_workbook import inspect_core_export_templates


router = APIRouter()


@router.get("/template-info")
def get_template_info() -> dict:
    """Debug endpoint to verify Excel templates and export directories.

    Returns the resolved template workbook (if any), panel-count-specific
    template presence, and the base PALLETS export directory.
    """
    excel_dir = Path("data") / "EXCEL"
    pallets_dir = Path("data") / "PALLETS"

    template_any = _find_pallet_workbook(excel_dir, None)
    template_26 = (excel_dir / "26.xlsx").resolve()
    template_30 = (excel_dir / "30.xlsx").resolve()
    template_35 = (excel_dir / "35.xlsx").resolve()

    return {
        "excel_dir": str(excel_dir.resolve()),
        "pallets_dir": str(pallets_dir.resolve()),
        "template_any": str(template_any.resolve()) if template_any else None,
        "templates": {
            "26_panels": str(template_26) if template_26.exists() else None,
            "30_panels": str(template_30) if template_30.exists() else None,
            "35_panels": str(template_35) if template_35.exists() else None,
        },
        "pallets_dir_exists": pallets_dir.exists(),
        "core_templates": inspect_core_export_templates(),
    }

