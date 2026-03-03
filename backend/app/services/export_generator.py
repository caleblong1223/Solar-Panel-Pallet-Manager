from __future__ import annotations

from datetime import datetime, timezone

from app.models.pallet import Pallet


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_export_pdf_bytes(pallet: Pallet, template_type: str) -> bytes:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "Pallet Manager Export",
        f"Pallet ID: {pallet.id}",
        f"Pallet Number: {pallet.pallet_number}",
        f"Template: {template_type}",
        f"Status: {pallet.status}",
        f"Created: {now}",
    ]
    if pallet.items:
        lines.append("Serials:")
        lines.extend([f" - {item.serial}" for item in pallet.items])

    y = 760
    text_ops = ["BT", "/F1 11 Tf", "72 0 0 72 0 0 Tm"]
    for line in lines:
        safe = _pdf_escape(line)
        text_ops.append(f"1 0 0 1 40 {y} Tm ({safe}) Tj")
        y -= 16
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="ignore")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii")
        + stream
        + b"\nendstream endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)
