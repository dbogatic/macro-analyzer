from __future__ import annotations

from pathlib import Path
import markdown as md
from weasyprint import HTML


def export_pdf(report_text: str, path: str | Path) -> Path:
    out_path = Path(path)
    html = md.markdown(report_text)
    HTML(string=html).write_pdf(str(out_path))
    return out_path
