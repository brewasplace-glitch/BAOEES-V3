from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.structural_model_interchange_v1_1 import (
    VALID as CANONICAL_VALID,
    INVALID as CANONICAL_INVALID,
    canonical_sha256,
    validate_model,
)
from phoenix.autonomy.pat001_structural_canonicalization_adapter_hardening_v1_2 import (
    ADAPTER_ID,
    PROJECT_ID,
    SAFETY,
    assess_v1_2,
    build_canonical_v1_1,
    qualify_existing_calculix_adapter,
    resolve_analysis_scope,
    resolve_project_identity,
)


def fixture_v83():
    return {
        "project_id": PROJECT_ID,
        "analytical_model": {
            "model_state": "ANALYTICAL_CANDIDATE",
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0, "source_ids": ["S1"]},
                {"id": "N2", "x": 5, "y": 0, "z": 0, "source_ids": ["S2"]},
                {"id": "N3", "x": 5, "y": 4, "z": 0, "source_ids": ["S3"]},
                {"id": "N4", "x": 0, "y": 4, "z": 0, "source_ids": ["S4"]},
            ],
            "members": [
                {
                    "id": "M1", "type": "beam", "node_i": "N1", "node_j": "N2",
                    "material_id": "MAT1", "section_id": "SEC1",
                    "approval_state": "CANDIDATE_ONLY",
                }
            ],
            "shells": [
                {
                    "id": "S1", "type": "slab", "node_ids": ["N1", "N2", "N3", "N4"],
                    "material_id": "MAT1", "section_id": "SH1",
                    "approval_state": "CANDIDATE_ONLY",
                }
            ],
            "supports": [
                {"id": "SUP1", "node_id": "N1", "dofs": ["UX", "UY", "UZ"], "approval_state": "CANDIDATE_ONLY"}
            ],
        },
        "solver_basis": {
            "basis": "EXPLICIT_PROJECT_INPUT",
            "analysis_type": "LINEAR_STATIC",
            "materials": {
                "MAT1": {"elastic_modulus_kN_m2": 30000000.0, "analysis_only": True}
            },
            "sections": {
                "SEC1": {"type": "rectangular_beam", "width_m": 0.3, "height_m": 0.6},
                "SH1": {"type": "shell", "thickness_m": 0.16},
            },
        },
        "action_load_model": {
            "model_state": "ACTION_LOAD_MODEL_CANDIDATE",
            "unit_system": {"force": "kN", "length": "m", "mass": "kg", "moment": "kNm", "stress": "kPa"},
            "load_cases": [
                {"id": "LC-G", "category": "permanent", "analysis_type": "STATIC", "approval_state": "CANDIDATE_ONLY"}
            ],
            "action_assignments": [
                {
                    "id": "A1", "case_id": "LC-G", "kind": "self_weight", "direction": "GRAVITY",
                    "factor": 1.0, "target_element_ids": ["M1", "S1"], "approval_state": "CANDIDATE_ONLY",
                }
            ],
            "load_combinations": [
                {"id": "C1", "limit_state": "ULS", "terms": [{"case_id": "LC-G", "coefficient": 1.2}]}
            ],
        },
        "solver_adapters": ["opensees", "calculix"],
        "execution_policy": {"allow_execution": False},
    }


def base_contract():
    src = [{"reference": "TRACEABLE"}]
    prov = {
        key: {"status": "TRACEABLE", "sources": src}
        for key in (
            "geometry", "materials", "sections", "supports_and_boundaries",
            "load_basis", "load_cases", "load_combinations",
        )
    }
    return {
        "schema_version": "phoenix.pat001-structural-input-contract/1.1",
        "project_id": PROJECT_ID,
        "project_identity": {"name": "REQUIRED", "location": "Paramaribo, Suriname.", "structural_scope": "REQUIRED"},
        "canonical_structural_model": {"path": "REQUIRED"},
        "provenance": prov,
        "analysis_scope": {"status": "REQUIRED", "calculation_type": None},
        "scia": {"seed_esa": None},
        "calculix": {"project_adapter": None},
    }


class Pat001CanonicalAdapterTests(unittest.TestCase):
    def test_01_v11_validator_accepts_shell_model(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            self.assertEqual(CANONICAL_VALID, validate_model(model)["status"])
            self.assertEqual(1, len(model["shells"]))

    def test_02_shells_are_not_dropped(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, audit = build_canonical_v1_1(p, root)
            self.assertEqual(audit["source_counts"]["shells"], audit["output_counts"]["shells"])
            self.assertFalse(audit["shells_dropped"])

    def test_03_deterministic_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            a, _ = build_canonical_v1_1(p, root)
            b, _ = build_canonical_v1_1(p, root)
            self.assertEqual(canonical_sha256(a), canonical_sha256(b))

    def test_04_wrong_project_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            v = fixture_v83()
            v["project_id"] = "OTHER"
            p = root / "v83.json"
            p.write_text(json.dumps(v), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_canonical_v1_1(p, root)

    def test_05_missing_shell_list_refuses_lossy_conversion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            v = fixture_v83()
            del v["analytical_model"]["shells"]
            p = root / "v83.json"
            p.write_text(json.dumps(v), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_canonical_v1_1(p, root)

    def test_06_unknown_member_material_fails_validator(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            model["members"][0]["material"] = "MISSING"
            self.assertEqual(CANONICAL_INVALID, validate_model(model)["status"])

    def test_07_analysis_scope_uses_solver_basis(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            r = resolve_analysis_scope(p, root, base_contract())
            self.assertEqual("LIN", r["mapped_value"])
            self.assertFalse(r["required_template_used_as_authority"])
            self.assertFalse(r["load_case_analysis_type_used_as_global_scope"])

    def test_08_unknown_analysis_scope_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            v = fixture_v83()
            v["solver_basis"]["analysis_type"] = "MYSTERY"
            p = root / "v83.json"
            p.write_text(json.dumps(v), encoding="utf-8")
            r = resolve_analysis_scope(p, root, base_contract())
            self.assertIsNone(r["mapped_value"])
            self.assertEqual("REQUIRED", r["analysis_scope"]["status"])

    def test_09_identity_does_not_use_generic_name(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "projects/runtime" / PROJECT_ID
            d.mkdir(parents=True)
            (d / "project_manifest.json").write_text(json.dumps({
                "project_id": PROJECT_ID,
                "name": "WRONG_GENERIC_NAME",
                "location": "Paramaribo",
            }), encoding="utf-8")
            r = resolve_project_identity(root, base_contract())
            self.assertEqual("REQUIRED", r["project_identity"]["name"])
            self.assertFalse(r["generic_name_field_used"])

    def test_10_identity_accepts_explicit_project_name(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "projects/runtime" / PROJECT_ID
            d.mkdir(parents=True)
            (d / "project_manifest.json").write_text(json.dumps({
                "project_id": PROJECT_ID,
                "project_name": "PAT 001 Residence",
                "structural_scope": "Building structural system",
            }), encoding="utf-8")
            r = resolve_project_identity(root, base_contract())
            self.assertEqual("PAT 001 Residence", r["project_identity"]["name"])
            self.assertEqual("Building structural system", r["project_identity"]["structural_scope"])

    def test_11_adapter_requires_all_project_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            r = qualify_existing_calculix_adapter(root, p)
            self.assertFalse(r["qualified"])

    def test_12_adapter_qualifies_existing_legacy_chain(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            structural = root / "projects/runtime" / PROJECT_ID / "results/session_adapters/structural_engineering/validated_v8_1_to_v8_12"
            v83 = structural / "v8_3/input.json"
            v83.parent.mkdir(parents=True)
            v83.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            runner = root / "runners/PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py"
            runner.parent.mkdir(parents=True)
            runner.write_text("# legacy adapter\n", encoding="utf-8")
            manifest = structural / "v8_3/solver_package/PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}", encoding="utf-8")
            deck = structural / "v8_4/solver_evidence/calculix/LC-G/phoenix_v8_4_case.inp"
            deck.parent.mkdir(parents=True)
            deck.write_text("*HEADING\n", encoding="ascii")
            r = qualify_existing_calculix_adapter(root, v83)
            self.assertTrue(r["qualified"])
            self.assertEqual(ADAPTER_ID, r["adapter_id"])
            self.assertFalse(r["live_solver_started"])

    def test_13_adapter_rejects_missing_calculix_declaration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            structural = root / "projects/runtime" / PROJECT_ID / "results/session_adapters/structural_engineering/validated_v8_1_to_v8_12"
            v = fixture_v83()
            v["solver_adapters"] = ["opensees"]
            p = structural / "v8_3/input.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(v), encoding="utf-8")
            r = qualify_existing_calculix_adapter(root, p)
            self.assertFalse(r["checks"]["calculix_declared"])

    def test_14_assessment_keeps_scia_gap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            validation = validate_model(model)
            contract = base_contract()
            contract["project_identity"] = {"name": "PAT", "location": "Paramaribo", "structural_scope": "Structure"}
            contract["analysis_scope"] = {"status": "CONFIRMED", "calculation_type": "LIN"}
            r = assess_v1_2(contract, validation, {"qualified": True})
            self.assertIn("PAT001-GAP-SCIA-MODEL", r["gaps"])

    def test_15_assessment_identity_gap_is_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            contract = base_contract()
            contract["analysis_scope"] = {"status": "CONFIRMED", "calculation_type": "LIN"}
            r = assess_v1_2(contract, validate_model(model), {"qualified": True})
            self.assertIn("PAT001-GAP-IDENTITY", r["gaps"])

    def test_16_material_analysis_only_flag_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            self.assertTrue(model["materials"][0]["properties"]["analysis_only"])

    def test_17_candidate_flags_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            self.assertEqual("CANDIDATE_ONLY", model["members"][0]["approval_state"])

    def test_18_units_are_preserved_not_converted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            model, _ = build_canonical_v1_1(p, root)
            self.assertEqual("kN", model["units"]["force"])
            self.assertEqual("m", model["units"]["length"])

    def test_19_no_golden_reference_registration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "v83.json"
            p.write_text(json.dumps(fixture_v83()), encoding="utf-8")
            r = qualify_existing_calculix_adapter(root, p)
            self.assertFalse(r["golden_reference_used_as_project_evidence"])

    def test_20_no_live_solver_or_release(self):
        self.assertFalse(SAFETY["automatic_live_scia"])
        self.assertFalse(SAFETY["automatic_live_calculix"])
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])
        self.assertEqual("LOCKED", SAFETY["production_release"])
        self.assertEqual("LOCKED", SAFETY["for_construction_release"])

    def test_21_no_lossy_or_invented_behavior(self):
        self.assertFalse(SAFETY["shells_dropped_during_canonicalization"])
        self.assertFalse(SAFETY["design_values_invented"])
        self.assertFalse(SAFETY["generic_name_used_as_project_name"])
        self.assertFalse(SAFETY["required_template_used_as_analysis_authority"])


if __name__ == "__main__":
    unittest.main()
