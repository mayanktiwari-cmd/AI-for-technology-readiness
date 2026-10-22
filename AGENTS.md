PROJECT: APCTT TRL hackathon, Stage 1 package. Deadline 15 Nov 2026 23:59 IST.
Goal: a Python module that, per case (1-20 PDFs), returns criterion_status, evidence_reference
(with verbatim supporting_span), and a TRL 1-9 or an abstention, in the kit's exact schema.

HARD RULES (never violate):
- Runs in the kit's frozen base env (CPython 3.12). Use only packages from the kit's requirements-base.lock. Never pip install into the package.
- No network at runtime. No public models except the 23 in the kit's model catalogue.
- 3 minutes per case INCLUDING interpreter start and model load. A failed/invalid case scores 0, so never raise: return a valid abstained result on any error.
- supporting_span must be copied verbatim from the extracted text of the cited page. Never generate quotes. Never use a sentence that only states a TRL number as evidence.
- Take criterion IDs from the checklist passed to load(). Never hard-code IDs.
- Only the participant_module/ and assets/ folders are submitted.
- Do not invent kit APIs. Read the kit docs in ../apctt-participant-kit-0.5.0-cpu/ first. If unsure, say so.
- After every change, run the stated checks and paste the REAL output. Never claim a test passed without running it.
Data: data/labels.csv (columns incl. no, sdg, trl, unit, rationale, have_pdf), data/pdfs/NNN.pdf.
Labels are rough estimates, not official expert labels.