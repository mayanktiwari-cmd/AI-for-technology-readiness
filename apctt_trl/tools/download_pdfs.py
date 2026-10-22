"""Download the USGS PDFs listed in the xlsx and write data/labels.csv.
Usage: python tools/download_pdfs.py path/to/USGS_SDG_open_data_set_corrected.xlsx
Resumable. Skips rows marked 'excluded' in the sample-status column."""
import sys, csv, time, pathlib, urllib.request, ssl, certifi, openpyxl

xlsx = sys.argv[1]
root = pathlib.Path(__file__).resolve().parent.parent
pdfdir = root / "data" / "pdfs"; pdfdir.mkdir(parents=True, exist_ok=True)
ws = openpyxl.load_workbook(xlsx).active
rows = [[c.value for c in r] for r in ws.iter_rows()]
h = rows[0]; ix = {k: i for i, k in enumerate(h)}
out = []
for r in rows[1:]:
    no = int(r[ix["No."]])
    status = str(r[ix["APCTT public sample status"]])
    path = pdfdir / f"{no:03d}.pdf"
    ok = path.exists() and path.read_bytes()[:5] == b"%PDF-"
    if not ok and not status.startswith("excluded"):
        url = r[ix["Direct PDF URL"]]
        ctx = ssl.create_default_context(cafile=certifi.where())
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=120, context=ctx).read()
                if data[:5] != b"%PDF-": raise ValueError("not a PDF")
                path.write_bytes(data); ok = True; break
            except Exception as e:
                print(f"[{no}] attempt {attempt+1} failed: {e}"); time.sleep(2)
        print(f"[{no}] {'ok' if ok else 'FAILED'}")
    out.append(dict(no=no, sdg=r[ix["SDG"]], target=r[ix["SDG target"]], category=r[ix["Category"]],
                    title=r[ix["Title (original English)"]], year=r[ix["Publication year"]],
                    pages=r[ix["Page count"]], trl=r[ix["Estimated TRL"]],
                    unit=r[ix["TRL assessment unit"]], rationale=r[ix["TRL rationale"]],
                    status=status[:40], have_pdf=int(ok)))
with open(root / "data" / "labels.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print("PDFs available:", sum(o["have_pdf"] for o in out), "of", len(out))
