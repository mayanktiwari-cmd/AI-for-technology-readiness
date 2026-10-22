# Contract Notes — APCTT Participant Kit 0.5.0 (CPU variant)

All facts are quoted with the exact source file and section.

## 1. Entry-point class and method names/signatures; context object

- **Entry point**: `participant_module.adapter:AssessmentModule` — the default the organizer expects (README.md §1, §5; MODULE_GUIDE.md §1; CONFIGURATION.md §5). The class is created with no arguments, then called once per process in order: `load` → `assess` → `reset_case` → `close` (MODULE_GUIDE.md §1, §3).
- **`load(config, asset_root)`** — receives `config` (plain dict, JSON types) and `asset_root` (`pathlib.Path`, read-only, part of package hash). Must set `self.checklist` and `self.settings` from `config` (MODULE_GUIDE.md §2, the minimal example at §1). Never download anything (README.md §5).
- **`assess(case, context)`** — receives `case` (plain JSON Mapping holding the request case) and `context` (SimpleNamespace with exactly four attributes + one helper; MODULE_GUIDE.md §3, §3.1):
  - `context.run_id` (`str`): server-generated ID of this run, 32 hex characters (MODULE_GUIDE.md §3, "What assess receives and returns").
  - `context.seed` (`int`): same as `config["compute"]["seed"]` (MODULE_GUIDE.md §3).
  - `context.time_budget_ms` (`int`): time left for the whole case when the worker received it (MODULE_GUIDE.md §5).
  - `context.scratch_dir` (`pathlib.Path`): private, empty directory for this case; deleted afterwards (MODULE_GUIDE.md §3).
  - `context.remaining_ms()` (`float`): budget left now, measured by the worker's own clock (MODULE_GUIDE.md §3, §5).
- **`reset_case()`** — drops per-case state; nothing survives between cases (cold_per_case loading policy; MODULE_GUIDE.md §1, §3).
- **`close()`** — releases files, memory, GPU; must never raise or the case fails with `CLEANUP_ERROR` (MODULE_GUIDE.md §4, §9).

## 2. Input case fields; output result schema; validator rules

### 2.1 Request / case (DATA_CONTRACT.md §1)

**Top-level request body** (`POST /v1/assessments`):
- `request_id` — ASCII `[A-Za-z0-9_-]`, 1–128 characters (idempotency key).
- `case` — object with the following required fields:
  - `schema_version` — must equal server's schema version (`apctt-pdf-example-v1` in dev).
  - `input_profile` — must be `pdf_report` (the only supported profile).
  - `checklist_version` — must equal the server's checklist version (`APCTT-2026-CHECKLIST-v1` for official; CONFIGURATION.md §4).
  - `case_id` — identifier, ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`.
  - `assessment_as_of` — `"YYYY-MM-DD"` or `null`.
  - `assessment_target` — object: `target_id` (identifier), `type` (`component`/`subsystem`/`system`/`technology`), `description` (non-blank string).
  - `intended_application` — non-blank string.
  - `intended_environment` — non-blank string.
  - `title` — non-blank string.
  - `documents` — array of 1 to `max_documents` (3, official limit D77) documents.
  - `description` — optional, non-blank string.
  - `benefits` — optional, non-blank string.
  - `sdg_targets` — optional, array of distinct integers from 6, 11, 13, 14.
  - `sdg_rationale` — optional, non-blank string.

### 1.3 Document (DATA_CONTRACT.md §1.3)

Each document sent as base64 in the request:
- `document_id` — identifier, unique within the case.
- `title` — non-blank string.
- `document_date` — non-blank string or `null`.
- `language` — must be `en`.
- `format` — must be `pdf`.
- `content_base64` — standard base64 (RFC 4648), decoded must start with `%PDF-`, be ≤ `max_document_bytes` (50 MiB), and be a readable PDF.
- `sha256` — SHA-256 of decoded PDF bytes, 64 lowercase hex chars; must match.

### 1.4 What the module receives (DATA_CONTRACT.md §1.4)

In `case["documents"]`, instead of `content_base64`, the module sees per document:
- `page_count` — number of pages the server counted (≥ 1).
- `path` — absolute path of the PDF inside the case's private scratch directory, e.g. `<scratch>/documents/001.pdf`.
- All other document fields (`document_id`, `title`, `document_date`, `language`, `format`, `sha256`) are passed as sent.

Reading the PDF is the module's job; the server does not extract text, select, shorten or reorder anything. Pages are numbered from 1 in file order.

### 1.5 General rules (DATA_CONTRACT.md §1.5)

- Unknown fields are rejected at every level.
- Optional fields are omitted, not `null`.
- Types are strict: no conversion between strings, numbers, booleans.
- Identifier = `[A-Za-z0-9][A-Za-z0-9_.:-]{0,128}`.
- Non-blank string = contains at least one non-whitespace character.
- Encoding: `Content-Type: application/json` (optionally `; charset=utf-8`), UTF-8, no BOM, no `Content-Encoding` other than `identity`.
- Size: body may not exceed `max_request_bytes` (80 MiB, official; base64 makes a PDF about 4/3 of file size, so all PDFs of a case together ≤ about 59 MiB).
- Order of checks: size and JSON → schema → input profile → versions → document checks (uniqueness, base64, size, `%PDF-` header, SHA-256, count) → page count → total pages. Only the first failing stage is reported, with all its field errors (up to 20 shown; `diagnostics.field_errors_total` gives full count).

### 2.2 Result (DATA_CONTRACT.md §2)

**Result object** returned by the module — exactly these fields:

| Field | Required | Type and rule |
|---|---|---|
| `schema_version` | yes | Copy of `case.schema_version`. |
| `checklist_version` | yes | Copy of checklist `version` (= `case.checklist_version`). |
| `case_id` | yes | Copy of `case.case_id`. |
| `assessment_target` | yes | Exact copy of `case.assessment_target`. |
| `assessment_status` | yes | `completed`, `abstained` or `failed`. |
| `predicted_trl` | yes | Integer 1–9 when completed, otherwise `null`. |
| `criterion_status` | yes | Object: criterion ID → `met`/`not met`/`insufficient evidence`. |
| `evidence_reference` | yes | Object: criterion ID → array of evidence items (§2.3). |
| `missing_evidence` | yes | Object: criterion ID → non-blank explanation. May be `{}`. |
| `abstention_reason` | yes | When abstained: `insufficient evidence`/`conflicting evidence`/`ambiguous scope`/`out of scope`; otherwise `null`. |
| `error_code` | yes | When failed: non-blank string of choice; otherwise `null`. |
| `confidence` | no | Number 0–1 (integers 0 and 1 allowed; booleans not). Not with `failed`. |
| `uncertainty` | no | `{"kind": "trl_interval", "lower": L, "upper": U}`, integers 1–9, `L ≤ U`; when completed, `L ≤ predicted_trl ≤ U`. Not with `failed`. |
| `trl_rationale` | no | Non-blank string explaining `predicted_trl`. Only with `completed`. |
| `criterion_rationale` | no | Object: criterion ID → non-blank explanation. Any subset of criteria. Not with `failed`. |

**Status combinations** (DATA_CONTRACT.md §2.2):

| assessment_status | predicted_trl | abstention_reason | error_code | criteria maps |
|---|---|---|---|---|
| `completed` | integer 1–9 | `null` | `null` | every checklist criterion present |
| `abstained` | `null` | one of the four reasons | `null` | every checklist criterion present |
| `failed` | `null` | `null` | non-blank string | may be empty; entries present must be valid |

`abstained` is a scientific answer, not an error.

**Evidence items** (DATA_CONTRACT.md §2.3):

Each evidence item is an object with:
- `document_id` — yes — A document in this case.
- `page` — yes — Integer from 1 to that document's `page_count`.
- `supporting_span` — no — Non-blank string: the words on that page that support the judgment.

**Structural consistency rules** (DATA_CONTRACT.md §2.3):
1. `criterion_status` and `evidence_reference` each have exactly one key per checklist criterion.
2. A `met` criterion has at least one evidence item.
3. An `insufficient evidence` criterion has a non-blank explanation in `missing_evidence`.
4. A `not met` criterion needs no evidence, but may cite pages that show it is not met.
5. `missing_evidence` and `criterion_rationale` may only use checklist criterion IDs.

### 2.3 Result rules (DATA_CONTRACT.md §4.2)

| Rule | Meaning |
|---|---|
| `result_object` | The result is not a JSON object. |
| `result_required_field` | A required field is missing (checking stops here). |
| `result_unknown_field` | A field outside §2.1, at top level or inside an evidence item. |
| `result_matches_case` | `schema_version`, `case_id` or `assessment_target` differs from the case. |
| `result_matches_checklist` | `checklist_version` differs from the checklist or the case. |
| `assessment_status_value` | `assessment_status` is not `completed`, `abstained` or `failed`. |
| `strict_trl` | `completed` needs an integer TRL 1–9. |
| `status_combination` | A field contradicts the status (§2.2), e.g. a TRL with `abstained`. |
| `abstention_reason_value` | `abstained` needs one of the four reasons. |
| `error_code_required` | `failed` needs a non-blank `error_code`. |
| `failed_omits_optional` | `confidence`, `uncertainty`, `trl_rationale` and `criterion_rationale` are not allowed with `failed`. |
| `map_object` | `criterion_status`, `evidence_reference`, `missing_evidence` or `criterion_rationale` is not an object. |
| `criterion_known_id` | A key in `criterion_status` or `missing_evidence` is not a checklist criterion. |
| `criterion_status_complete` | A checklist criterion has no status. |
| `criterion_status_value` | A status other than `met`, `not met`, `insufficient evidence`. |
| `evidence_keys_match_checklist` | `evidence_reference` keys differ from the checklist criteria (missing or extra). |
| `evidence_list` | An evidence value is not an array. |
| `evidence_item_object` | An evidence item is not an object. |
| `evidence_item_required` | An evidence item lacks a string `document_id` or a `page`. |
| `evidence_locator_exists` | `document_id` is not a document of this case. |
| `evidence_page_in_document` | `page` is not an integer from 1 to the document's `page_count`. |
| `supporting_span_nonblank` | `supporting_span` is empty or only whitespace. |
| `evidence_required_for_met` | A `met` criterion has no evidence. |
| `missing_evidence_text` | A `missing_evidence` value is not a non-blank string. |
| `missing_evidence_required_for_insufficient` | An `insufficient evidence` criterion has no explanation. |
| `confidence_range` | `confidence` is not a finite number 0–1. |
| `uncertainty_interval` | `uncertainty` has the wrong shape, range or does not contain `predicted_trl`. |
| `trl_rationale_requires_completed` | `trl_rationale` with a status other than `completed`. |
| `rationale_known_criterion` | A `criterion_rationale` key is not a checklist criterion. |
| `rationale_nonblank_text` | A rationale value is not a non-blank string. |

## 3. How to run the kit server locally and submit a case

### 3.1 Install the server environment (README.md §3–4)

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.lock
uv pip install --python .venv/bin/python --no-deps -e .
```

### 3.2 Start the server (README.md §4, §6)

```bash
# Default dev profile with official checklist
.venv/bin/python -m apctt_server --profile dev --config config/dev.json

# Custom configuration (e.g. your own module)
.venv/bin/python -m apctt_server --profile dev --config config/my.local.json
```

### 3.3 Health check (README.md §4)

```bash
curl -s http://127.0.0.1:8000/health/ready
```
Returns `"reason_code":"READY"` when the server can accept cases.

### 3.4 Send an example request (README.md §4)

```bash
curl -s -i -H 'Content-Type: application/json' --data @docs/EXAMPLE_REQUEST.json \
     http://127.0.0.1:8000/v1/assessments
```
Answers with 202 + `Location` header.

### 3.5 Poll for the result (README.md §4)

```bash
# Get assessment ID from the Location line, then:
curl -s http://127.0.0.1:8000/v1/assessments/<assessment_id from the Location line>
```
When finished: shows `"job_status":"finished"`, `"result_origin":"module"`, with one entry per criterion of the official checklist (`APCTT-C01` to `APCTT-C12`).

### 3.6 Submit a case using the kit script (README.md §7)

```bash
# Using the included submit.py helper
.venv/bin/python submit.py                     # sends docs/EXAMPLE_REQUEST.json
.venv/bin/python submit.py my_cases/case-001.json  # sends your own request file

# make_request.py turns PDFs into request files
.venv/bin/python tools/make_request.py docs/EXAMPLE_REPORT.pdf -o my_cases/example.json --case-id EXAMPLE-001
.venv/bin/python tools/make_request.py ../reports/report-a.pdf -o my_cases/case-001.json --case-id MY-001
```

### 3.7 Restart server after code changes (README.md §8, §9)

Stop the server (`Ctrl+C`) and start it again with `config/my.local.json`. Each case loads your code fresh, but the server computes the package hash at start-up; restarting keeps the recorded hash equal to the files that actually ran.

### 3.8 Pack and check submission (README.md §10; SUBMISSION.md §1.2)

```bash
.venv/bin/python tools/make_submission.py ../my_submission
.venv/bin/python tools/make_submission.py --check ../MY-TEAM_submission.zip
```
Exit codes: 0 `VALID`, 1 `REFUSED` (each `ERROR` line names a problem; the zip is deleted), 2 `VALID_WITH_REVIEW` (licence items the organizer decides after submission).

## 4. The demo checklist and demo case format

### 4.1 DEMO checklist (CONFIGURATION.md §4; MODULE_GUIDE.md §8; README.md §9)

The kit has two checklist files:
- `contracts/checklist.official.json` — official checklist, `APCTT-2026-CHECKLIST-v1`, `"official": true`, criteria `APCTT-C01` to `APCTT-C12` (decision D74). The organizer runs every package with it; it is the default of `config/dev.json` and of the configuration of README step 6.
- `contracts/checklist.demo.json` — DEMO checklist with two criteria, for the protocol tests and for one run with a changed checklist (shown in CONFIGURATION.md §4).

**DEMO checklist content** (CONFIGURATION.md §4):
```json
{
  "version": "DEMO-CHECKLIST-NOT-OFFICIAL",
  "official": false,
  "criteria": [
    {"criterion_id": "DEMO-C01", "description": "DEMO ONLY: the report states that a prototype or model was tested."},
    {"criterion_id": "DEMO-C02", "description": "DEMO ONLY: the report states that measured results met stated acceptance criteria."}
  ]
}
```

### 4.2 Using the DEMO checklist (MODULE_GUIDE.md §8; CONFIGURATION.md §4)

To test that your module does not depend on hard-coded criterion IDs:
1. Copy `contracts/checklist.demo.json`.
2. Change the criterion IDs, descriptions and `version`.
3. Set `checklist_path` in a copy of your configuration to the new checklist path.
4. Make requests with `tools/make_request.py --checklist <your copy>`.

This is the only use of the DEMO checklist: the organizer runs the official one.

### 4.3 Demo case format (README.md §7; DATA_CONTRACT.md §1)

Public sample cases are 99 real USGS reports listed in `contracts/public-cases.json` (README.md §7, §5.2). To turn PDFs into request files:

```bash
# List every case: SDG, TRL, pages, MiB
.venv/bin/python tools/get_public_cases.py --list

# Download (smoke test: 3 diagnostic cases)
.venv/bin/python tools/get_public_cases.py --download --smoke --dir ../public_cases/pdf

# Make request files from downloaded PDFs
.venv/bin/python tools/get_public_cases.py --make-requests --smoke --dir ../public_cases/pdf --out ../public_cases/requests

# Submit a diagnostic case
.venv/bin/python submit.py ../public_cases/requests/USGS-SDG-012.json
```

`--download --all` fetches all 99 (about 1.1 GB, one file at a time; run again to resume). `--labels` prints the organizer's estimated TRL and reason for each case (rough reference, not expert labels, never sent to your module).

## 5. Differences from AGENTS.md

No `AGENTS.md` file exists in the project directory. A search of `/Users/mayanktiwari/drive-download-20261020T195409Z-1-001` returned no matches for `AGENTS.md`. Therefore, there are no differences to list — the kit has no AGENTS.md to compare against.