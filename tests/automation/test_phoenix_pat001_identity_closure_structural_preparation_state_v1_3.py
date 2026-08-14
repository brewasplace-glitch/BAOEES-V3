from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.pat001_identity_closure_structural_preparation_state_v1_3 import (
    PROJECT_ID,
    IDENTITY_CLOSED,
    PREPARED_SCIA_PENDING,
    SAFETY,
    close_identity,
)


PROJECT_NAME = "Anijsstraat"
STRUCTURAL_SCOPE = "Constructief ontwerp en analyse van de volledige draagconstructie, inclusief fundering, kolommen, balken, vloeren/daken, stabiliteit en belastingafdracht."


def canonical():
    return {
        "schema_version": "phoenix.canonical-structural-model/1.1",
        "project_id": PROJECT_ID,
        "model_id": "MODEL",
        "units": {"length": "m", "force": "kN"},
        "nodes": [
            {"id": "N1", "x": 0, "y": 0, "z": 0},
            {"id": "N2", "x": 1, "y": 0, "z": 0},
            {"id": "N3", "x": 1, "y": 1, "z": 0},
        ],
        "materials": [{"id": "MAT1", "properties": {}}],
        "sections": [{"id": "SEC1", "properties": {}}],
        "members": [{
            "id": "M1", "start_node": "N1", "end_node": "N2",
            "material": "MAT1", "section": "SEC1",
        }],
        "shells": [],
        "supports": [{"id": "S1", "node": "N1", "dofs": ["UX", "UY", "UZ"]}],
        "load_cases": [{"id": "LC1"}],
        "load_actions": [],
        "load_combinations": [{
            "id": "C1",
            "terms": [{"load_case": "LC1", "factor": 1.0}],
        }],
        "metadata": {"design_values_invented": False},
    }


def contract():
    source = [{"reference": "TRACE"}]
    provenance = {
        key: {"status": "TRACEABLE", "sources": source}
        for key in (
            "geometry", "materials", "sections", "supports_and_boundaries",
            "load_basis", "load_cases", "load_combinations",
        )
    }
    return {
        "schema_version": "phoenix.pat001-structural-input-contract/1.2",
        "project_id": PROJECT_ID,
        "project_identity": {
            "name": "REQUIRED",
            "location": "Paramaribo, Suriname.",
            "structural_scope": "REQUIRED",
        },
        "provenance": provenance,
        "analysis_scope": {"status": "CONFIRMED", "calculation_type": "LIN"},
        "calculix": {"project_adapter": "PAT001-LEGACY-V8_3-CALCULIX-PROJECT-ADAPTER-v1"},
        "scia": {"seed_esa": None},
    }


def declaration():
    return {
        "schema_version": "phoenix.project-identity-declaration/1.0",
        "project_id": PROJECT_ID,
        "project_name": PROJECT_NAME,
        "structural_scope": STRUCTURAL_SCOPE,
        "decision_source": "USER_STRATEGIC_DECISION",
        "decision_date": "2026-08-14",
        "authority": "PROJECT_OWNER",
    }


class IdentityClosureTests(unittest.TestCase):
    def setup_files(self, root: Path):
        c = root / "contract.json"
        d = root / "decl.json"
        m = root / "canonical.json"
        c.write_text(json.dumps(contract()), encoding="utf-8")
        d.write_text(json.dumps(declaration()), encoding="utf-8")
        m.write_text(json.dumps(canonical()), encoding="utf-8")
        return c, d, m

    def test_01_identity_closes_with_explicit_owner_declaration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            r = close_identity(root, c, d, m, root / "out")
            self.assertEqual(IDENTITY_CLOSED, r["identity_status"])
            self.assertEqual(PROJECT_NAME, r["project_name"])

    def test_02_structural_scope_exactly_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            r = close_identity(root, c, d, m, root / "out")
            self.assertEqual(STRUCTURAL_SCOPE, r["structural_scope"])

    def test_03_location_preserved_from_existing_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            r = close_identity(root, c, d, m, root / "out")
            self.assertEqual("Paramaribo, Suriname.", r["location"])

    def test_04_missing_location_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = contract()
            data["project_identity"]["location"] = "REQUIRED"
            c = root / "contract.json"; c.write_text(json.dumps(data), encoding="utf-8")
            d = root / "decl.json"; d.write_text(json.dumps(declaration()), encoding="utf-8")
            m = root / "canonical.json"; m.write_text(json.dumps(canonical()), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_05_wrong_project_id_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            data = declaration(); data["project_id"] = "OTHER"
            d.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_06_non_owner_authority_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            data = declaration(); data["authority"] = "AUTOMATION"
            d.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_07_non_user_decision_source_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            data = declaration(); data["decision_source"] = "INFERRED"
            d.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_08_canonical_invalid_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            data = canonical()
            data["members"][0]["material"] = "MISSING"
            m.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_09_analysis_scope_must_remain_confirmed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = contract()
            data["analysis_scope"] = {"status": "REQUIRED", "calculation_type": None}
            c = root / "contract.json"; c.write_text(json.dumps(data), encoding="utf-8")
            d = root / "decl.json"; d.write_text(json.dumps(declaration()), encoding="utf-8")
            m = root / "canonical.json"; m.write_text(json.dumps(canonical()), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_10_calculix_adapter_must_remain_qualified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = contract()
            data["calculix"]["project_adapter"] = None
            c = root / "contract.json"; c.write_text(json.dumps(data), encoding="utf-8")
            d = root / "decl.json"; d.write_text(json.dumps(declaration()), encoding="utf-8")
            m = root / "canonical.json"; m.write_text(json.dumps(canonical()), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_11_provenance_must_remain_complete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = contract()
            data["provenance"]["geometry"] = {"status": "REQUIRED", "sources": []}
            c = root / "contract.json"; c.write_text(json.dumps(data), encoding="utf-8")
            d = root / "decl.json"; d.write_text(json.dumps(declaration()), encoding="utf-8")
            m = root / "canonical.json"; m.write_text(json.dumps(canonical()), encoding="utf-8")
            with self.assertRaises(ValueError):
                close_identity(root, c, d, m, root / "out")

    def test_12_only_scia_gap_remains(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            r = close_identity(root, c, d, m, root / "out")
            self.assertEqual(["PAT001-GAP-SCIA-MODEL"], r["remaining_gaps"])
            self.assertEqual(PREPARED_SCIA_PENDING, r["status"])

    def test_13_source_contract_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            before = c.read_bytes()
            close_identity(root, c, d, m, root / "out")
            self.assertEqual(before, c.read_bytes())

    def test_14_output_contract_is_v13(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            close_identity(root, c, d, m, root / "out")
            out = json.loads((root / "out/pat001_structural_input_contract_v1_3.json").read_text())
            self.assertEqual("phoenix.pat001-structural-input-contract/1.3", out["schema_version"])

    def test_15_identity_evidence_records_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c, d, m = self.setup_files(root)
            close_identity(root, c, d, m, root / "out")
            out = json.loads((root / "out/pat001_structural_input_contract_v1_3.json").read_text())
            self.assertEqual("PROJECT_OWNER", out["project_identity_evidence"]["declaration"]["authority"])

    def test_16_no_identity_auto_inference(self):
        self.assertFalse(SAFETY["identity_auto_inferred"])

    def test_17_no_live_solvers(self):
        self.assertFalse(SAFETY["automatic_live_scia"])
        self.assertFalse(SAFETY["automatic_live_calculix"])

    def test_18_no_auto_approval_or_compliance(self):
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])

    def test_19_release_locks(self):
        self.assertEqual("LOCKED", SAFETY["production_release"])
        self.assertEqual("LOCKED", SAFETY["for_construction_release"])


if __name__ == "__main__":
    unittest.main()
