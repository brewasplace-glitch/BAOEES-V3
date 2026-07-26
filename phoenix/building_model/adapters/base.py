from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

@dataclass(frozen=True, slots=True)
class AdapterStatus:
    application: str
    available: bool
    executable: str | None
    mode: str
    message: str
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class ExternalApplicationAdapter:
    application_name = "External application"
    def candidate_executables(self) -> Iterable[Path]:
        return ()
    def detect(self) -> AdapterStatus:
        for candidate in self.candidate_executables():
            if candidate.is_file():
                return AdapterStatus(self.application_name, True, str(candidate),
                                     "manifest-handoff",
                                     "Application detected; controlled handoff is available.")
        return AdapterStatus(self.application_name, False, None, "manifest-only",
                             "Application not detected in standard installation paths.")
    def write_manifest(self, *, output_path: str | Path, project_id: str,
                       model_path: str | Path, actions: list[dict[str, Any]]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "phoenix.external-app-handoff/1.0",
            "project_id": project_id,
            "application": self.application_name,
            "adapter_status": self.detect().to_dict(),
            "model_path": str(Path(model_path)),
            "actions": actions,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
