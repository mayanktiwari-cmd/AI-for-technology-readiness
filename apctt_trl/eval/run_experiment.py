"""Extract all PDFs (cached), then compare baselines and the cue-feature ridge with leave-one-SDG-out CV.
Usage: python eval/run_experiment.py [--train-final]"""
import sys, csv, json, pathlib, time
from multiprocessing import Pool
import numpy as np
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from participant_module.extract import extract_pages
from participant_module.features import featurize, RidgeJSON, NAMES

def score_A(pred, gold):
    """pred None = abstain. Gold TRL is determinable here."""
    if pred is None: return 0.25
    d = abs(pred - gold); return 1.0 if d == 0 else 0.5 if d == 1 else 0.0

def get_pages(no):
    cache = root / "data" / "text" / f"{no:03d}.json"
    if cache.exists(): return json.loads(cache.read_text())
    pdf = root / "data" / "pdfs" / f"{no:03d}.pdf"
    pages = extract_pages(pdf); cache.parent.mkdir(exist_ok=True, parents=True)
    cache.write_text(json.dumps(pages)); return pages

def feat(no): 
    t = time.time(); f = featurize(get_pages(no)); return no, f, time.time() - t

if __name__ == "__main__":
    rows = [r for r in csv.DictReader(open(root / "data" / "labels.csv")) if r["have_pdf"] == "1"]
    nos = [int(r["no"]) for r in rows]; y = np.array([int(r["trl"]) for r in rows]); grp = np.array([r["sdg"] for r in rows])
    with Pool() as p: out = p.map(feat, nos)
    X = np.array([o[1] for o in out]); print(f"{len(rows)} docs; slowest extract+featurize {max(o[2] for o in out):.1f}s")
    def report(name, pred):
        s = np.mean([score_A(p, g) for p, g in zip(pred, y)])
        v = [p for p in pred if p is not None]
        ex = np.mean([p == g for p, g in zip(pred, y) if p is not None]) if v else 0
        w1 = np.mean([abs(p - g) <= 1 for p, g in zip(pred, y) if p is not None]) if v else 0
        print(f"{name:28s} A={s:.3f}  exact={ex:.2f}  within1={w1:.2f}")
    report("always abstain", [None] * len(y))
    report("always 6 (majority)", [6] * len(y))
    for alpha in (1, 10, 30, 100):
        pred = np.zeros(len(y))
        for g in np.unique(grp):
            te = grp == g; m = RidgeJSON.fit(X[~te], y[~te], alpha); pred[te] = m.predict(X[te])
        report(f"ridge a={alpha} (leave-SDG-out)", [int(np.clip(round(p), 1, 9)) for p in pred])
    if "--train-final" in sys.argv:
        m = RidgeJSON.fit(X, y, 30.0); (root / "assets").mkdir(exist_ok=True)
        (root / "assets" / "trl_ridge.json").write_text(json.dumps(m.to_dict()))
        print("wrote assets/trl_ridge.json; top weights:", sorted(zip(NAMES, np.round(m.coef, 2)), key=lambda t: -abs(t[1]))[:5])
