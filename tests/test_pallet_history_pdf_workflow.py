from pathlib import Path

import os

import pytest
from openpyxl import Workbook

from app.pallet_history_window import PalletHistoryWindow


class _FakeMaster:
    def update(self):
        return None


class _FakeLabel:
    def __init__(self):
        self.master = _FakeMaster()
        self.text = ""

    def config(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]


def _make_window():
    window = PalletHistoryWindow.__new__(PalletHistoryWindow)
    window.window = None
    return window


def test_open_pdf_uses_windows_default_app(monkeypatch, tmp_path):
    window = _make_window()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    calls = {"startfile": [], "popen": []}

    monkeypatch.setattr("app.pallet_history_window.platform.system", lambda: "Windows")
    monkeypatch.setattr(
        os,
        "startfile",
        lambda path: calls["startfile"].append(path),
        raising=False,
    )
    monkeypatch.setattr(
        "app.pallet_history_window.subprocess.Popen",
        lambda *args, **kwargs: calls["popen"].append((args, kwargs)),
    )

    window._open_pdf(pdf_path)

    assert calls["startfile"] == [str(pdf_path.absolute())]
    assert calls["popen"] == []


def test_reportlab_pdf_generation_from_xlsx(tmp_path):
    pytest.importorskip("reportlab")

    workbook_path = tmp_path / "pallet.xlsx"
    pdf_path = tmp_path / "pallet.pdf"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "PALLET SHEET"
    worksheet["B1"] = "Panel Type 30"
    worksheet["B3"] = "Pallet-001"
    worksheet["G3"] = "2026-03-11"
    worksheet["B5"] = "SERIAL-001"
    worksheet["B6"] = "SERIAL-002"
    workbook.save(workbook_path)

    window = _make_window()
    progress_label = _FakeLabel()

    created_pdfs = window._excel_to_pdf_reportlab([workbook_path], pdf_path, progress_label)

    assert created_pdfs == [pdf_path]
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_excel_to_pdf_prefers_libreoffice(monkeypatch, tmp_path):
    window = _make_window()
    progress_label = _FakeLabel()
    excel_file = tmp_path / "pallet.xlsx"
    excel_file.write_bytes(b"placeholder")
    expected_pdf = tmp_path / "pallet.pdf"

    calls = []

    def fake_libreoffice(files, pdf_path, label):
        calls.append(("libreoffice", files, pdf_path))
        return [expected_pdf]

    monkeypatch.setattr(window, "_excel_to_pdf_libreoffice", fake_libreoffice)
    monkeypatch.setattr(
        window,
        "_excel_to_pdf_com",
        lambda *args, **kwargs: pytest.fail("Excel COM fallback should not run when LibreOffice succeeds"),
    )
    monkeypatch.setattr(
        window,
        "_excel_to_pdf_reportlab",
        lambda *args, **kwargs: pytest.fail("ReportLab fallback should not run when LibreOffice succeeds"),
    )

    result = window._excel_to_pdf([excel_file], expected_pdf, progress_label)

    assert result == [expected_pdf]
    assert calls == [("libreoffice", [excel_file], expected_pdf)]
