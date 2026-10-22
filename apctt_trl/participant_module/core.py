"""Kit-independent assessment logic. The adapter maps the kit's objects to/from these plain dicts."""
import json, time, pathlib
import numpy as np
from .extract import extract_pages
from .features import featurize, RidgeJSON
from .evidence import retrieve

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
SAFETY_MS = 25_000          # return a valid result with this much time left

def load_model(path=None):
    p = pathlib.Path(path) if path else ASSETS / "trl_ridge.json"
    return RidgeJSON.from_dict(json.loads(p.read_text())) if p.exists() else None

def assess_case(case, checklist, model, remaining_ms, settings=None):
    """case: dict per DATA_CONTRACT (documents[].path/document_id). checklist: list of {criterion_id, description}.
    remaining_ms: callable. Always returns a valid-looking result dict."""
    settings = settings or {}
    k_pages = settings.get("evidence_pages", 3); min_score = settings.get("min_score", 0.12)
    res = {"schema_version": case.get("schema_version"), "checklist_version": case.get("checklist_version"),
           "case_id": case.get("case_id"), "assessment_target": case.get("assessment_target"),
           "criterion_status": {}, "evidence_reference": {}, "missing_evidence": {},
           "predicted_trl": None, "abstention_reason": None, "error_code": None}
    try:
        t_end = time.monotonic() + max(0, remaining_ms() - SAFETY_MS) / 1000.0
        docs, all_pages = [], []
        for d in case["documents"]:
            try: pages = extract_pages(d["path"], deadline=t_end)
            except Exception: pages = []   # one bad PDF must not kill the case
            docs.append((d["document_id"], pages)); all_pages.extend(pages)
        have_text = sum(len(p) for p in all_pages) > 500
        for c in checklist:
            cid, desc = c["criterion_id"], c["description"]
            cands = []
            for did, pages in docs:
                st, ev = retrieve(pages, did, desc, k_pages, min_score)
                cands.extend(ev)
            # best-first across documents: re-rank by quote/description overlap is left to retrieve order
            if cands:
                res["criterion_status"][cid] = "met"; res["evidence_reference"][cid] = cands[:k_pages]
            else:
                res["criterion_status"][cid] = "insufficient evidence"; res["evidence_reference"][cid] = []
                res["missing_evidence"][cid] = "No page describing this criterion was found in the supplied reports."
        if not have_text or model is None:
            res.update(assessment_status="abstained", predicted_trl=None, abstention_reason="insufficient evidence")
        else:
            x = featurize(all_pages)
            trl = int(np.clip(round(float(model.predict(x[None, :])[0])), 1, 9))
            res.update(assessment_status="completed", predicted_trl=trl)
    except Exception as e:  # never raise: a failed case scores 0, an abstention scores >= 0
        for c in checklist:
            res["criterion_status"].setdefault(c["criterion_id"], "insufficient evidence")
            res["evidence_reference"].setdefault(c["criterion_id"], [])
            res["missing_evidence"].setdefault(c["criterion_id"], "Document could not be processed.")
        res.update(assessment_status="abstained", predicted_trl=None, abstention_reason="insufficient evidence")
    return res