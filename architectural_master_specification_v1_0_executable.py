from dataclasses import dataclass
from typing import List, Dict, Any
import json
from pathlib import Path

@dataclass
class ModuleContract:
    id: str
    name: str
    purpose: str
    inputs: List[str]
    outputs: List[str]
    knowledge_sources: List[str]
    tests: List[str]

class ArchitecturalSpecificationValidator:
    REQUIRED_FIELDS = ["id", "name", "purpose", "inputs", "outputs", "knowledge_sources", "tests"]

    def validate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        modules = spec.get("modules", [])
        for index, module in enumerate(modules):
            for field in self.REQUIRED_FIELDS:
                if field not in module or module[field] in (None, "", []):
                    issues.append({"module_index": index, "module_id": module.get("id"), "issue": f"missing_or_empty_{field}"})
        return {
            "specification": spec.get("specification"),
            "version": spec.get("version"),
            "module_count": len(modules),
            "issue_count": len(issues),
            "issues": issues,
            "valid": len(issues) == 0,
        }


def load_spec(path="architectural_master_specification_v1_0.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    spec = load_spec(here / "architectural_master_specification_v1_0.json")
    result = ArchitecturalSpecificationValidator().validate(spec)
    out = here / "architectural_master_specification_v1_0_validation.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
