"""Kit entry point. TODO: align the method names/signatures with the kit's MODULE_GUIDE.md and DATA_CONTRACT.md.
core.assess_case holds all logic and is independent of the kit."""
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from .core import assess_case, load_model

class AssessmentModule:
    def load(self, checklist=None, settings=None, asset_root=None, **kw):
        self.checklist = [{"criterion_id": c["criterion_id"], "description": c["description"]} for c in (checklist or [])]
        self.settings = settings or {}
        self.model = load_model(os.path.join(asset_root, "trl_ridge.json") if asset_root else None)

    def assess(self, case, context=None):
        rem = context.remaining_ms if context is not None else (lambda: 170_000)
        return assess_case(case, self.checklist, self.model, rem, self.settings)

    def reset_case(self): pass
    def close(self): pass
