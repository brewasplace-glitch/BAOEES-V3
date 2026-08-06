from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy import material_certification_engineering_mode as m


class StructuralMaterialDesignBasisGateFixTests(unittest.TestCase):
    def _write_selection(self, root: Path, row: dict, design_requirement: dict | None = None, mode: str = m.MODE_UNCERTIFIED):
        ws = root / "projects" / "runtime" / "P1"
        a = ws / "results" / "session_adapters" / "architecture"
        a.mkdir(parents=True)
        (a / "structural_material_selection_register.json").write_text(json.dumps({"selections": [row]}), encoding="utf-8")
        if design_requirement is not None:
            (a / "local_material_requirements.json").write_text(json.dumps(design_requirement), encoding="utf-8")
        (a / "architectural_session_intake.json").write_text(json.dumps({"material_certification_mode": mode}), encoding="utf-8")
        return ws

    def test_supplier_concrete_range_must_not_become_required_design_class(self):
        row = {
            "requirement_id": "REQ-CONCRETE",
            "material_family": "structural_concrete",
            "selection_status": "LOCAL_AVAILABILITY_CONFIRMED",
            "commercial_availability_confirmed": True,
            "engineering_qualification_status": "TECHNICAL_PRODUCT_EVIDENCE_REQUIRED",
            "selected_product": {"description": "Supplier capability C8/10 through C53/65", "certifications": []},
            "alternatives": [{"description": "Ready mix C8/10 through C53/65", "material_family": "structural_concrete"}],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._write_selection(root,row)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertIsNone(m.resolve_required_design_class(ws,row))
                gaps=m.build_design_material_basis_gap_register(ws)
                self.assertEqual(gaps["design_basis_gap_count"],1)

    def test_explicit_design_requirement_wins_over_supplier_range(self):
        row = {
            "requirement_id": "REQ-CONCRETE",
            "material_family": "structural_concrete",
            "selection_status": "LOCAL_AVAILABILITY_CONFIRMED",
            "commercial_availability_confirmed": True,
            "engineering_qualification_status": "TECHNICAL_PRODUCT_EVIDENCE_REQUIRED",
            "selected_product": {"description": "Supplier capability C8/10 through C53/65", "certifications": []},
        }
        requirement={"requirement_id":"REQ-CONCRETE","material_family":"structural_concrete","required_design_class":"C25/30"}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._write_selection(root,row,requirement)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertEqual(m.resolve_required_design_class(ws,row),"C25/30")

    def test_relaxed_mode_missing_design_class_bypasses_certification_gate_but_records_gap(self):
        row = {
            "requirement_id": "REQ-REBAR",
            "material_family": "reinforcement_steel",
            "selection_status": "AVAILABILITY_UNKNOWN",
            "commercial_availability_confirmed": False,
            "engineering_qualification_status": "NOT_QUALIFIED",
            "selected_product": None,
            "candidates": [],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._write_selection(root,row)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertFalse(m.structural_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_UNCERTIFIED}))
                gaps=m.build_design_material_basis_gap_register(ws)
                self.assertEqual(gaps["gaps"][0]["requirement_id"],"REQ-REBAR")

    def test_strict_mode_unknown_availability_is_not_certification_blocker(self):
        row = {
            "requirement_id": "REQ-TIMBER",
            "material_family": "structural_timber",
            "selection_status": "AVAILABILITY_UNKNOWN",
            "commercial_availability_confirmed": False,
            "engineering_qualification_status": "NOT_QUALIFIED",
            "selected_product": None,
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._write_selection(root,row,mode=m.MODE_CERTIFIED)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertFalse(m.structural_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_CERTIFIED}))

    def test_strict_mode_available_uncertified_product_still_blocks(self):
        row = {
            "requirement_id": "REQ-CONCRETE",
            "material_family": "structural_concrete",
            "selection_status": "LOCAL_AVAILABILITY_CONFIRMED",
            "commercial_availability_confirmed": True,
            "engineering_qualification_status": "TECHNICAL_PRODUCT_EVIDENCE_REQUIRED",
            "selected_product": {"description":"Concrete","certifications":[]},
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._write_selection(root,row,mode=m.MODE_CERTIFIED)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertTrue(m.structural_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_CERTIFIED}))


if __name__ == "__main__":
    unittest.main()
