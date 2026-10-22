"""Per-page text extraction with a time budget. Returns list[str], one per page (index 0 = page 1)."""
import re, time

_WS = re.compile(r"\s+")

def norm(t: str) -> str:
    return _WS.sub(" ", t or "").strip()

def extract_pages(path, deadline=None):
    """deadline: time.monotonic() value after which remaining pages are left empty."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(path))
        n = len(pdf); pages = []
        for i in range(n):
            if deadline is not None and time.monotonic() > deadline:
                pages.extend([""] * (n - i)); break
            page = pdf[i]
            try:
                tp = page.get_textpage()
                pages.append(norm(tp.get_text_range()))
                tp.close()
            finally:
                page.close()
        pdf.close()
        return pages
    except Exception:
        pass
    from pypdf import PdfReader  # fallback
    rd = PdfReader(str(path)); pages = []
    n = len(rd.pages)
    for i, p in enumerate(rd.pages):
        if deadline is not None and time.monotonic() > deadline:
            pages.extend([""] * (n - i)); break
        try: pages.append(norm(p.extract_text()))
        except Exception: pages.append("")
    return pages
