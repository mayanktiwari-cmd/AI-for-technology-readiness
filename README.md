# APCTT TRL Assessment — Participant Module

This repository contains a participant module for the **APCTT TRL Hackathon** (Stage 1). The module assesses Technology Readiness Levels (TRL 1–9) from PDF reports using a lightweight ridge regression model on maturity-cue features.

## Project Structure

```
.
├── participant_module/     # Kit entry point (submitted folder)
│   ├── __init__.py
│   ├── adapter.py          # AssessmentModule: load → assess → reset_case → close
│   ├── core.py             # Kit-independent assessment logic
│   ├── extract.py          # Per-page PDF text extraction (pypdfium2 + pypdf fallback)
│   ├── features.py         # Maturity-cue TF features + RidgeJSON regressor
│   └── evidence.py         # Verbatim quote retrieval per criterion
├── assets/                 # Model weights (trl_ridge.json) — generated, not committed
├── data/                   # Local data (PDFs, labels.csv) — not committed
├── tools/
│   └── download_pdfs.py    # Download PDFs from USGS dataset XLSX
├── eval/
│   └── run_experiment.py   # Leave-one-SDG-out baseline evaluation
└── docs/
    └── CONTRACT_NOTES.md   # Kit contract reference (from participant kit)
```

## Quick Start

### 1. Install the kit's base environment
```bash
# From the participant kit root (apctt-participant-kit-0.5.0-cpu/)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.lock
uv pip install --python .venv/bin/python --no-deps -e .
```

### 2. Prepare data (optional, for local testing)
```bash
# Download USGS PDFs from the corrected XLSX
python tools/download_pdfs.py /path/to/USGS_SDG_open_data_set_corrected.xlsx
# Outputs: data/pdfs/, data/labels.csv
```

### 3. Train the ridge model (generates `assets/trl_ridge.json`)
```bash
python eval/run_experiment.py --train-final
```

### 4. Run the kit server locally
```bash
# From the participant kit root
.venv/bin/python -m apctt_server --profile dev --config config/dev.json
```

### 5. Submit a test case
```bash
.venv/bin/python submit.py docs/EXAMPLE_REQUEST.json
```

## Module Interface (Kit Contract)

The `AssessmentModule` in `participant_module/adapter.py` implements the required lifecycle:

| Method | Purpose |
|--------|---------|
| `load(checklist, settings, asset_root)` | Load checklist criteria, settings, and model from `asset_root/trl_ridge.json` |
| `assess(case, context)` | Process one case: extract PDF text, retrieve evidence per criterion, predict TRL |
| `reset_case()` | Clear per-case state (cold-per-case policy) |
| `close()` | Release resources (no-op here) |

### Output Schema (per DATA_CONTRACT.md)

- `assessment_status`: `completed` | `abstained` | `failed`
- `predicted_trl`: integer 1–9 (only when `completed`)
- `criterion_status`: `{criterion_id: "met" | "not met" | "insufficient evidence"}`
- `evidence_reference`: `{criterion_id: [{document_id, page, supporting_span}]}`
- `supporting_span` is **always verbatim** from the extracted page text
- Never raises: returns a valid `abstained` result on any error

## Constraints (Hard Rules)

- **No network** at runtime; `HF_HUB_OFFLINE=1` enforced
- **3 minutes per case** including interpreter start + model load
- **Frozen base env**: only packages from `requirements-base.lock`
- **Only `participant_module/` and `assets/`** are submitted
- **Never hard-code criterion IDs** — take from `load(checklist)`

## License

Internal hackathon submission. Not for public distribution.