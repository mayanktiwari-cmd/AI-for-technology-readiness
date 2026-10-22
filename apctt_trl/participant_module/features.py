"""Maturity-cue features. Pure Python + numpy, no model weights."""
import re, math
import numpy as np

CUES = {
 "concept":  r"\b(conceptual|proof[- ]of[- ]concept|theoretical|hypothes\w+|feasib\w+)\b",
 "lab":      r"\b(laborator\w+|bench|flume|experiment\w*|simulat\w+)\b",
 "model":    r"\b(model\w*|regression|equation\w*|algorithm\w*|software|code)\b",
 "calib":    r"\b(calibrat\w+|validat\w+|verif\w+|uncertaint\w+|nash|sutcliffe|r-squared|root[- ]mean)\b",
 "field":    r"\b(field|deploy\w+|gage\w*|gauge\w*|streamgag\w+|survey\w*|sampled|sampling|monitor\w+)\b",
 "applied":  r"\b(applied|application\w*|decision\w*|management|planning|regulat\w+|floodway\w*|insurance)\b",
 "release":  r"\b(release\w*|version|install\w+|user'?s? (?:guide|manual)|download\w*|open[- ]source|doi)\b",
 "operational": r"\b(operational\w*|real[- ]time|routine\w*|continuous\w*|network\w*|forecast\w*|warning\w*|publicly available|web ?site)\b",
 "tested":   r"\b(test\w*|evaluat\w+|compar\w+|performance|accuracy)\b",
}
_RX = {k: re.compile(v, re.I) for k, v in CUES.items()}
NAMES = list(CUES) + ["log_pages"]

def featurize(pages):
    text = " ".join(pages)
    words = max(1, len(text.split()))
    f = [math.log1p(1000.0 * len(_RX[k].findall(text)) / words) for k in CUES]
    f.append(math.log1p(len(pages)))
    return np.array(f, dtype=float)

class RidgeJSON:
    """Tiny ridge regressor stored as plain JSON (no pickle)."""
    def __init__(self, mu=None, sd=None, coef=None, b=6.0):
        self.mu, self.sd, self.coef, self.b = mu, sd, coef, b
    @staticmethod
    def fit(X, y, alpha=10.0):
        X = np.asarray(X, float); y = np.asarray(y, float)
        mu, sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - mu) / sd; b = y.mean()
        coef = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - b))
        return RidgeJSON(mu.tolist(), sd.tolist(), coef.tolist(), float(b))
    def predict(self, X):
        Z = (np.asarray(X, float) - np.array(self.mu)) / np.array(self.sd)
        return Z @ np.array(self.coef) + self.b
    def to_dict(self): return dict(mu=self.mu, sd=self.sd, coef=self.coef, b=self.b, names=NAMES)
    @staticmethod
    def from_dict(d): return RidgeJSON(d["mu"], d["sd"], d["coef"], d["b"])
