import json
import tempfile
import unittest
from pathlib import Path

from phoenix.adapters.multi_material_design_adapter import (
    run_multi_material_design,
)
from phoenix.multi_material import (
    DesignContext,
    MaterialCandidate,
    MultiMaterialDesignEngine,
    MultiMaterialError,
    SystemCandidate,
)


def materials():
    return (
        MaterialCandidate("C30", "concrete", 2400, 0.12, 0.18, 30, 0.8, 0.7),
        MaterialCandidate("S355", "steel", 7850, 1.8, 1.35, 355, 0.9, 0.9),
        MaterialCandidate("GL24", "timber", 480, 0.10, 1.10, 24, 0.7, 0.8),
    )


def systems():
    return (
        SystemCandidate("SYS_ANY", "any", 0.20, 250, 5.0, 2),
        SystemCandidate("SYS_STEEL", "steel", 0.03, 300, 5.0, 2),
    )


class Wave152Tests(unittest.TestCase):
    def test_generates_multiple_material_families(self):
        result = MultiMaterialDesignEngine().generate(
            context=DesignContext("PHX", 150),
            materials=materials(),
            systems=systems(),
        )
        self.assertEqual(result["feasible_variant_count"], 4)
        self.assertEqual(
            set(result["family_summary"]),
            {"concrete", "steel", "timber"},
        )

    def test_incompatible_combinations_are_rejected(self):
        result = MultiMaterialDesignEngine().generate(
            context=DesignContext("PHX", 150),
            materials=materials(),
            systems=systems(),
        )
        reasons = {
            item["variant_id"]: item["rejection_reasons"]
            for item in result["rejected_variants"]
        }
        self.assertIn("family_incompatible", reasons["SYS_STEEL__C30"])
        self.assertIn("family_incompatible", reasons["SYS_STEEL__GL24"])

    def test_utilization_constraint_rejects_system(self):
        with self.assertRaisesRegex(MultiMaterialError, "No feasible"):
            MultiMaterialDesignEngine().generate(
                context=DesignContext("PHX", 400),
                materials=(materials()[1],),
                systems=(SystemCandidate("LOW", "steel", 0.1, 300, 4),),
            )

    def test_metrics_are_calculated(self):
        result = MultiMaterialDesignEngine().generate(
            context=DesignContext("PHX", 100),
            materials=(materials()[0],),
            systems=(SystemCandidate("C", "concrete", 0.5, 200, 4, 1),),
        )
        item = result["variants"][0]
        self.assertEqual(item["mass_kg"], 1200.0)
        self.assertEqual(item["utilization"], 0.5)
        self.assertGreater(item["cost"], 0)
        self.assertGreater(item["carbon_kgco2e"], 0)

    def test_evidence_is_sha256(self):
        result = MultiMaterialDesignEngine().generate(
            context=DesignContext("PHX", 100),
            materials=(materials()[0],),
            systems=(SystemCandidate("C", "concrete", 0.5, 200, 4),),
        )
        self.assertEqual(len(result["evidence"]["payload_sha256"]), 64)

    def test_duplicate_material_rejected(self):
        duplicate = (materials()[0], materials()[0])
        with self.assertRaisesRegex(MultiMaterialError, "Duplicate material_id"):
            MultiMaterialDesignEngine().generate(
                context=DesignContext("PHX", 100),
                materials=duplicate,
                systems=(systems()[0],),
            )

    def test_adapter_writes_output(self):
        request = {
            "context": {"project_id": "PHX", "design_action_kn": 100},
            "materials": [
                {
                    "material_id": "S",
                    "family": "steel",
                    "density_kg_m3": 7850,
                    "embodied_carbon_kgco2e_kg": 1.8,
                    "cost_per_kg": 1.2,
                    "strength_mpa": 355,
                }
            ],
            "systems": [
                {
                    "system_id": "SYS",
                    "required_family": "steel",
                    "volume_m3": 0.02,
                    "design_resistance_kn": 200,
                    "span_m": 5,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            result = run_multi_material_design(request, path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(result["feasible_variant_count"], 1)
        self.assertEqual(stored["adapter"]["version"], "1.0.0")

    def test_write_result_is_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            MultiMaterialDesignEngine().write_result(
                context=DesignContext("PHX", 100),
                materials=(materials()[2],),
                systems=(SystemCandidate("T", "timber", 0.5, 200, 4),),
                destination=path,
            )
            self.assertTrue(path.is_file())
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
