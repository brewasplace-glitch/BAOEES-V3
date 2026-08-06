from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy import material_certification_engineering_mode as m


class MaterialEngineeringContinuationTests(unittest.TestCase):
    def test_default_is_certified(self):
        self.assertEqual(m.resolve_mode({"brief": "test"}), m.MODE_CERTIFIED)

    def test_marker_disables_certification_gate(self):
        self.assertEqual(m.resolve_mode({"brief":"[PHOENIX_MATERIAL_CERTIFICATION_MODE=UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED]"}), m.MODE_UNCERTIFIED)

    def _workspace(self, root: Path, *, unknown=False, design_class="C20/25", alternative=None, relaxed=True) -> Path:
        ws=root/"projects"/"runtime"/"P1"; a=ws/"results"/"session_adapters"/"architecture"; a.mkdir(parents=True)
        row={
            "requirement_id":"REQ-CONCRETE","material_family":"structural_concrete","element_role":"column",
            "selection_status":"AVAILABILITY_UNKNOWN" if unknown else "LOCAL_AVAILABILITY_CONFIRMED",
            "commercial_availability_confirmed":not unknown,
            "engineering_qualification_status":"TECHNICAL_PRODUCT_EVIDENCE_REQUIRED",
            "selected_product":None if unknown else {"product_id":"LOCAL-CONCRETE","supplier_name":"Local","description":f"Ready mix {design_class}","unit_price":100,"currency":"SRD","unit":"m3","certifications":[]},
            "alternatives": [alternative] if alternative else [],
        }
        (a/"structural_material_selection_register.json").write_text(json.dumps({"selections":[row]}),encoding="utf-8")
        (a/"local_material_requirements.json").write_text(json.dumps({"requirement_id":"REQ-CONCRETE","material_family":"structural_concrete","required_class":design_class}) if design_class else json.dumps({"requirement_id":"REQ-CONCRETE","material_family":"structural_concrete"}),encoding="utf-8")
        mode=m.MODE_UNCERTIFIED if relaxed else m.MODE_CERTIFIED
        (a/"architectural_session_intake.json").write_text(json.dumps({"material_certification_mode":mode}),encoding="utf-8")
        return ws

    def test_explicit_temp_workspace_wins_over_inferred_repository_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            ws=root/"projects"/"runtime"/"P1"
            ws.mkdir(parents=True)
            context={
                "evidence":"projects/runtime/OTHER/results/x.json",
                "ctx":{"workspace":ws,"project_id":"P1"},
            }
            resolved=m.resolve_workspace(context)
            self.assertEqual(resolved,ws.resolve())

    def test_unknown_availability_does_not_block_relaxed_engineering(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertFalse(m.structural_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_UNCERTIFIED}))

    def test_unknown_availability_does_not_block_certified_engineering_if_design_class_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True,relaxed=False)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertFalse(m.structural_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_CERTIFIED}))

    def test_no_alternative_creates_unavailable_register_and_placeholder(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True)
            with patch.object(m,"PROJECT_ROOT",root):
                reg=m.resolve_material_availability(ws,m.MODE_UNCERTIFIED)
                self.assertEqual(reg["unavailable_material_count"],1)
                self.assertTrue((ws/"results/session_adapters/architecture/unavailable_materials_register.json").is_file())
                data=json.loads((ws/"results/session_adapters/architecture/structural_material_selection_register.json").read_text())
                row=data["selections"][0]
                self.assertEqual(row["procurement_route"],"UNRESOLVED_AVAILABILITY_DESIGN_PLACEHOLDER")
                self.assertFalse(row["availability_blocks_engineering"])

    def test_available_same_family_alternative_is_selected_in_relaxed_mode(self):
        alt={"product_id":"ALT-C20-25","supplier_name":"Alt Supplier","description":"Alternative C20/25","material_family":"structural_concrete","availability_status":"AVAILABLE_TO_ORDER","unit_price":90,"currency":"SRD","unit":"m3","certifications":[]}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True,alternative=alt)
            with patch.object(m,"PROJECT_ROOT",root):
                reg=m.resolve_material_availability(ws,m.MODE_UNCERTIFIED)
                self.assertEqual(reg["available_alternative_count"],1)
                data=json.loads((ws/"results/session_adapters/architecture/structural_material_selection_register.json").read_text())
                self.assertEqual(data["selections"][0]["selected_product"]["product_id"],"ALT-C20-25")

    def test_strict_mode_does_not_auto_select_uncertified_alternative(self):
        alt={"product_id":"ALT","material_family":"structural_concrete","availability_status":"AVAILABLE_TO_ORDER","certifications":[]}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True,alternative=alt,relaxed=False)
            with patch.object(m,"PROJECT_ROOT",root):
                reg=m.resolve_material_availability(ws,m.MODE_CERTIFIED)
                self.assertEqual(reg["available_alternative_count"],0)
                self.assertEqual(reg["unavailable_material_count"],1)

    def test_missing_design_class_does_not_trigger_certification_or_availability_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True,design_class="")
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertFalse(m.structural_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_UNCERTIFIED}))
                gaps=m.build_design_material_basis_gap_register(ws)
                self.assertEqual(gaps["design_basis_gap_count"],1)
                self.assertEqual(gaps["gaps"][0]["status"],"STRUCTURAL_DESIGN_MATERIAL_BASIS_REQUIRED")

    def test_unknown_availability_does_not_block_cost_generation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True)
            with patch.object(m,"PROJECT_ROOT",root):
                self.assertFalse(m.cost_certification_block_should_apply({"workspace":str(ws),"material_certification_mode":m.MODE_UNCERTIFIED}))

    def test_available_uncertified_material_keeps_price_in_relaxed_register(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=False)
            with patch.object(m,"PROJECT_ROOT",root):
                reg=m.build_uncertified_material_register(ws)
                self.assertEqual(reg["materials"][0]["unit_price"],100)
                self.assertEqual(reg["materials"][0]["certification_status"],"UNCERTIFIED")

    def test_uncertified_register_reference_uses_normalizing_repo_ref_helper(self):
        source=Path(m.__file__).read_text(encoding="utf-8")
        start=source.index("def build_uncertified_material_register")
        end=source.index("def ", start + 4) if "def " in source[start + 4:] else len(source)
        body=source[start:end]
        self.assertIn("_repo_ref_for_workspace(", body)
        self.assertNotIn(".relative_to(_repository_root_for_workspace(workspace))", body)

    def test_structural_postprocess_keeps_release_locked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ws=self._workspace(root,unknown=True)
            with patch.object(m,"PROJECT_ROOT",root):
                result=m.postprocess_structural_result({"outputs":[]},args=({"workspace":str(ws),"material_certification_mode":m.MODE_UNCERTIFIED},))
                self.assertEqual(result["production_release"],"LOCKED")
                self.assertTrue((ws/"results/session_adapters/structural_engineering/material_availability_design_status_report.json").is_file())

if __name__=="__main__": unittest.main()
