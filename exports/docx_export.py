from __future__ import annotations

from pathlib import Path
from docx import Document


def export_docx(report_text: str, path: str | Path) -> Path:
    out_path = Path(path)
    doc = Document()
    for line in report_text.splitlines():
        doc.add_paragraph(line)
    doc.save(out_path)
    return out_path
