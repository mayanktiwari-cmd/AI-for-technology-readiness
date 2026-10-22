"""Kit entry point: participant_module.adapter:AssessmentModule
Signatures taken from participant_example/adapter.py of kit 0.5.0:
  load(config, asset_root) ; assess(case, context) -> dict ; reset_case() ; close()
All logic lives in core.assess_case."""
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from .core import assess_case, load_model


class AssessmentModule:
    def __init__(self) -> None:
        self._checklist = []
        self._settings = {}
        self._model = None

    def load(self, config: Mapping[str, Any], asset_root: Path) -> None:
        # Criterion IDs/descriptions come from the checklist the server passes in; never hard-coded.
        self._checklist = [{"criterion_id": c["criterion_id"], "description": c["description"]}
                           for c in config["checklist"]["criteria"]]
        self._settings = dict(config.get("module", {}).get("settings", {}) or {})
        try:
            self._model = load_model(Path(asset_root) / "trl_ridge.json")
        except Exception:
            self._model = None  # no model -> cases abstain instead of failing

    def assess(self, case: Mapping[str, Any], context: Any) -> dict[str, Any]:
        return assess_case(dict(case), self._checklist, self._model, context.remaining_ms, self._settings)

    def reset_case(self) -> None:
        pass

    def close(self) -> None:
        pass