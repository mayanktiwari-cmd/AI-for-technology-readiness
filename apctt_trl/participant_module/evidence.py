"""Per-criterion page retrieval and VERBATIM quote selection (quotes are always cut from extracted page text)."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

_TRL_ASSERT = re.compile(r"\bTRL\b|technology readiness", re.I)
_SENT = re.compile(r"(?<=[.!?])\s+")

def _best_sentence(page_text, query_terms):
    best, best_s = None, 0
    for s in _SENT.split(page_text):
        s = s.strip()
        if not (40 <= len(s) <= 300) or _TRL_ASSERT.search(s):
            continue
        low = s.lower()
        sc = sum(1 for t in query_terms if t in low)
        if sc > best_s: best, best_s = s, sc
    return best

def retrieve(pages, doc_id, description, k=3, min_score=0.12):
    """Return (status_hint, evidence list). Evidence quotes are substrings of pages[page-1]."""
    if not any(pages):
        return "insufficient evidence", []
    vec = TfidfVectorizer(stop_words="english", sublinear_tf=True, ngram_range=(1, 2))
    try:
        M = vec.fit_transform(pages + [description])
    except ValueError:
        return "insufficient evidence", []
    sims = (M[:-1] @ M[-1].T).toarray().ravel()
    order = np.argsort(-sims)[:k]
    terms = [t for t in re.findall(r"[a-z]{4,}", description.lower())]
    ev = []
    for i in order:
        if sims[i] < min_score: continue
        q = _best_sentence(pages[i], terms)
        if q:
            ev.append({"document_id": doc_id, "page": int(i) + 1, "supporting_span": q})
    return ("met" if ev else "insufficient evidence"), ev
