from __future__ import annotations

from pathlib import Path
import json
import unittest

from phoenix.autonomy import MultidisciplinaryEngineSuiteService
from phoenix.autonomy.executor_adapter_registry import UniversalCapabilityExecutorRegistry
from phoenix.autonomy.multidisciplinary_engine_suite import EXPECTED_KEYS, object_sha256


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name: str) -> dict:
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


class Phase17MultidisciplinaryEngineSuiteTests(unittest.TestCase):
    def setUp(self):
        self.service = MultidisciplinaryEngineSuiteService.from_repo(ROOT)
        self.catalog = load("multidisciplinary_engine_suite_v1.json")

    def verified_project(self):
        return {
            "project_id": "PHASE17-TEST",
            "verified_inputs": {
                descriptor.key: {name: f"verified:{name}" for name in descriptor.required_inputs}
                for descriptor in self.service.descriptors
            },
        }

    def test_01_schema(self):
        self.assertEqual(self.catalog["schema"], "PHOENIX_MULTIDISCIPLINARY_ENGINE_SUITE_V1")

    def test_02_exact_engine_count(self):
        self.assertEqual(len(self.service.descriptors), 14)

    def test_03_exact_engine_order(self):
        self.assertEqual(tuple(x.key for x in sorted(self.service.descriptors, key=lambda x: x.order)), EXPECTED_KEYS)

    def test_04_unique_engine_keys(self):
        self.assertEqual(len({x.key for x in self.service.descriptors}), 14)

    def test_05_unique_engine_ids(self):
        self.assertEqual(len({x.engine_id for x in self.service.descriptors}), 14)

    def test_06_unique_adapter_ids(self):
        self.assertEqual(len({x.adapter_id for x in self.service.descriptors}), 14)

    def test_07_fail_closed(self):
        self.assertTrue(self.catalog["fail_closed"])

    def test_08_no_automatic_activation(self):
        self.assertFalse(self.catalog["automatic_engine_activation"])

    def test_09_no_repository_mutation(self):
        self.assertFalse(self.catalog["automatic_repository_mutation"])

    def test_10_professional_release_required(self):
        self.assertTrue(self.catalog["final_professional_release_required"])

    def test_11_dependencies_precede_consumers(self):
        order = {x.key: x.order for x in self.service.descriptors}
        self.assertTrue(all(order[d] < x.order for x in self.service.descriptors for d in x.dependencies))

    def test_12_all_engines_have_inputs(self):
        self.assertTrue(all(x.required_inputs for x in self.service.descriptors))

    def test_13_all_engines_have_outputs(self):
        self.assertTrue(all(x.outputs for x in self.service.descriptors))

    def test_14_all_engines_have_release_boundary(self):
        self.assertTrue(all(x.release_boundary for x in self.service.descriptors))

    def test_15_missing_project_id_denied(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_ID_REQUIRED"):
            self.service.plan({"verified_inputs": {}})

    def test_16_missing_inputs_hold(self):
        result = self.service.plan({"project_id": "X", "verified_inputs": {}})
        self.assertEqual(result["status"], "HOLD_MISSING_VERIFIED_INPUTS")

    def test_17_verified_inputs_ready(self):
        result = self.service.plan(self.verified_project())
        self.assertEqual(result["status"], "READY_FOR_GOVERNED_EXECUTION")

    def test_18_result_has_exact_fourteen_rows(self):
        self.assertEqual(len(self.service.plan(self.verified_project())["engines"]), 14)

    def test_19_result_digest_is_bound(self):
        result = self.service.plan(self.verified_project())
        expected = object_sha256({k: v for k, v in result.items() if k != "result_sha256"})
        self.assertEqual(result["result_sha256"], expected)

    def test_20_no_calculation_claimed(self):
        result = self.service.plan(self.verified_project())
        self.assertTrue(all(x["calculation_claimed"] is False for x in result["engines"]))

    def test_21_no_professional_release_claimed(self):
        result = self.service.plan(self.verified_project())
        self.assertTrue(all(x["professional_release"] is False for x in result["engines"]))

    def test_22_climate_control_has_energyplus(self):
        climate = next(x for x in self.service.descriptors if x.key == "climate_control")
        self.assertIn("energyplus", climate.external_backends)

    def test_23_climate_control_has_openstudio(self):
        climate = next(x for x in self.service.descriptors if x.key == "climate_control")
        self.assertIn("openstudio", climate.external_backends)

    def test_24_climate_control_has_contam(self):
        climate = next(x for x in self.service.descriptors if x.key == "climate_control")
        self.assertIn("contam", climate.external_backends)

    def test_25_climate_control_has_openmodelica(self):
        climate = next(x for x in self.service.descriptors if x.key == "climate_control")
        self.assertIn("openmodelica", climate.external_backends)

    def test_26_backend_probe_never_installs(self):
        probe = self.service.backend_probe()
        self.assertTrue(all(x["automatic_installation"] is False for x in probe.values()))

    def test_27_backend_probe_never_activates(self):
        probe = self.service.backend_probe()
        self.assertTrue(all(x["automatic_activation"] is False for x in probe.values()))

    def test_28_engine_registry_contains_fourteen_disciplines(self):
        registered = {x["engine_id"] for x in load("engine_registry_v1.json")["engines"]}
        self.assertTrue({x.engine_id for x in self.service.descriptors} <= registered)

    def test_29_executor_registry_complete(self):
        registry = UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        self.assertTrue(registry.coverage_report()["complete"])

    def test_30_each_discipline_resolves_to_adapter(self):
        registry = UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        for descriptor in self.service.descriptors:
            resolved = registry.resolve(descriptor.engine_id, descriptor.action)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved[0].adapter_id, descriptor.adapter_id)

    def test_31_synthetic_proof(self):
        proof = self.service.synthetic_proof()
        self.assertEqual(proof["status"], "PASS")

    def test_32_result_schema_present(self):
        schema = load("multidisciplinary_engine_result_v1.schema.json")
        self.assertEqual(schema["properties"]["schema"]["const"], "PHOENIX_MULTIDISCIPLINARY_ENGINE_RESULT_V1")

    def test_33_third_party_registry_has_climate_stack(self):
        engines = load("third_party_engine_registry_v5_1_0.json")["engines"]
        self.assertTrue({"energyplus", "openstudio", "contam", "openmodelica"} <= set(engines))

    def test_34_autonomous_delivery_includes_climate(self):
        self.assertIn("climate_control", load("autonomous_project_delivery_v1_0.json")["engines"])

    def test_35_orchestrator_uses_climate_control_name(self):
        order = load("orchestrator_policy_v1_0.json")["required_engine_order"]
        self.assertIn("climate_control", order)

    def test_36_policy_manifest_binds_suite(self):
        manifest = load("policy_bundle_manifest_v1.json")
        self.assertIn("multidisciplinary_engine_suite_v1.json", manifest["files"])


if __name__ == "__main__":
    unittest.main()
