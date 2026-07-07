from pathlib import Path
from datetime import datetime
import json


class PhoenixSpecificationValidator:
    def validate_suite(self, suite_id: str):
        suite_path = Path("suites") / suite_id
        checks = {
            "suite_exists": suite_path.exists(),
            "manifest_exists": (suite_path / "suite_manifest.json").exists(),
            "core_exists": (suite_path / "core").exists(),
            "engines_exists": (suite_path / "engines").exists(),
            "schemas_exists": (suite_path / "schemas").exists(),
            "tests_exists": (suite_path / "tests").exists(),
            "docs_exists": (suite_path / "docs").exists()
        }
        result = {
            "suite_id": suite_id,
            "validated_at": datetime.now().isoformat(timespec="seconds"),
            "checks": checks,
            "overall_ok": all(checks.values())
        }
        out = Path("outputs/pdk")
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{suite_id}_validation.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return result
