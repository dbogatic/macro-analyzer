from __future__ import annotations

from pathlib import Path
import markdown as md

try:
    from xhtml2pdf import pisa as _pisa
    _XHTML2PDF_AVAILABLE = True
except Exception:
    _XHTML2PDF_AVAILABLE = False

try:
    from weasyprint import HTML as _WeasyHTML
    _WEASYPRINT_AVAILABLE = True
except Exception:
    _WEASYPRINT_AVAILABLE = False


def export_pdf(report_text: str, path: str | Path) -> Path:
    out_path = Path(path)
    html = md.markdown(report_text)

    if _XHTML2PDF_AVAILABLE:
        with open(out_path, "wb") as f:
            _pisa.CreatePDF(html, dest=f)
        return out_path

    if _WEASYPRINT_AVAILABLE:
        _WeasyHTML(string=html).write_pdf(str(out_path))
        return out_path

    raise RuntimeError(
        "No PDF library available. Run: pip install xhtml2pdf"
    )
