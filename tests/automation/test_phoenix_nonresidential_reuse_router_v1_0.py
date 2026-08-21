from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"


class NonResidentialReuseRouterTests(unittest.TestCase):
    def test_binding_route(self):
        data = json.loads(BINDING.read_text(encoding="utf-8"))
        route = data["metadata"]["phoenix_architectural_engine_route"]["route"]
        self.assertEqual(route, "NONRESIDENTIAL_REUSE_V1")

    def test_cli_routes_moskee_nonresidential(self):
        from phoenix.design.tropical_residential.project_orchestration_cli import resolve_architectural_route
        data = json.loads(BINDING.read_text(encoding="utf-8"))
        self.assertEqual(resolve_architectural_route(data), "NONRESIDENTIAL_REUSE_V1")

    def test_cli_preserves_legacy_residential_route(self):
        from phoenix.design.tropical_residential.project_orchestration_cli import resolve_architectural_route
        self.assertEqual(resolve_architectural_route({"project_id": "X"}), "TROPICAL_RESIDENTIAL_LEGACY")

    def test_exact_A_E_variant_contract(self):
        from phoenix.architecture.nonresidential_real_project_orchestration_v1_0 import VARIANT_SPECS
        self.assertEqual([item["id"] for item in VARIANT_SPECS], list("ABCDE"))

    def test_no_residential_room_semantics_in_new_router(self):
        source = (ROOT / "phoenix/architecture/nonresidential_real_project_orchestration_v1_0.py").read_text(encoding="utf-8").lower()
        self.assertNotIn('"bedrooms"', source)
        self.assertNotIn('"bathrooms"', source)
        self.assertIn("residential_program_fabricated", source)

    def test_reuse_modules_are_invoked(self):
        source = (ROOT / "phoenix/architecture/nonresidential_real_project_orchestration_v1_0.py").read_text(encoding="utf-8")
        self.assertIn("run_integrated_suite", source)
        self.assertIn("generate_authoritative_ifc", source)
        self.assertIn("render_project_exterior", source)

    def test_source_models_are_real_moskee_sources(self):
        from phoenix.architecture.nonresidential_real_project_orchestration_v1_0 import _source_models
        arch, geom, prod = _source_models(ROOT)
        self.assertGreaterEqual(len(arch.get("spaces", [])), 2)
        self.assertEqual(float(geom["extension"]["gross_area_m2"]), 140.0)
        self.assertGreaterEqual(int(prod["occupancy"]["special_peak_persons"]), 200)

    def test_integrated_suite_smoke_on_scaled_variant(self):
        from phoenix.architecture.nonresidential_real_project_orchestration_v1_0 import _source_models, _base_dimensions, _scale_model, VARIANT_SPECS, _write
        from phoenix.architecture.integrated_suite_v4_0_0 import run
        arch, geom, prod = _source_models(ROOT)
        x, y, gross, storeys = _base_dimensions(geom, prod)
        model = _scale_model(arch, "TEST-MOSKEE", "Moskee Test", VARIANT_SPECS[0], x, y, gross, storeys)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "model.json"
            _write(model_path, model)
            manifest = run(model_path, root / "suite")
            self.assertEqual(manifest["release_status"], "CONCEPT_REVIEW_REQUIRED")
            self.assertTrue((root / "suite" / "drawings").is_dir())

    def test_release_locks(self):
        source = (ROOT / "phoenix/architecture/nonresidential_real_project_orchestration_v1_0.py").read_text(encoding="utf-8")
        self.assertIn("CONCEPT_ONLY_NOT_FOR_CONSTRUCTION", source)
        self.assertIn('"production_locked": True', source)
        self.assertIn('"for_construction_locked": True', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
