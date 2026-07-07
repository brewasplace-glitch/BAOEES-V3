from pathlib import Path
from datetime import datetime
import json

from project_phoenix.pdk.generators.suite_generator import PhoenixSuiteGenerator
from project_phoenix.pdk.generators.module_generator import PhoenixModuleGenerator
from project_phoenix.pdk.generators.test_generator import PhoenixTestGenerator
from project_phoenix.pdk.validators.specification_validator import PhoenixSpecificationValidator
from project_phoenix.pdk.release.release_builder import PhoenixReleaseBuilder


class PhoenixDevelopmentKit:
    def bootstrap_architectural_suite(self):
        suite = PhoenixSuiteGenerator().generate_suite("architectural", "Architectural Suite")

        modules = [
            ("project_intake", "Project Intake Engine"),
            ("program_of_requirements", "Programma van Eisen Engine"),
            ("space_schedule", "Ruimtestaat Engine"),
            ("floorplan_generator", "Plattegrondgenerator"),
        ]

        generated_modules = []
        for module_id, title in modules:
            generated_modules.append(PhoenixModuleGenerator().generate_module("architectural", module_id, title))
            PhoenixTestGenerator().generate_test("architectural", module_id)

        validation = PhoenixSpecificationValidator().validate_suite("architectural")
        release = PhoenixReleaseBuilder().create_release_manifest("architectural_suite_pdk_bootstrap", "0.1.0")

        result = {
            "pdk": "Phoenix Development Kit",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "suite": suite,
            "modules": generated_modules,
            "validation": validation,
            "release": release
        }

        out = Path("outputs/pdk")
        out.mkdir(parents=True, exist_ok=True)
        (out / "pdk_v1_bootstrap_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return result


if __name__ == "__main__":
    result = PhoenixDevelopmentKit().bootstrap_architectural_suite()
    print("Phoenix Development Kit v1.0 geÃ¯nstalleerd.")
    print("Architectural Suite bootstrap:", result["validation"]["overall_ok"])
