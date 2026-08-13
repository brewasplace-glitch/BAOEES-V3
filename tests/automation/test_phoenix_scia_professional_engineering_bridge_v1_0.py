from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from phoenix.integrations.scia.professional_engineering_bridge_v1_0 import (
    DEFAULT_ESA_XML,
    STATUS_CALCULATED,
    STATUS_INVALID,
    STATUS_READY,
    build_esa_xml_command,
    execute_plan,
    validate_plan,
)


def plan_template():
    return {
        "schema_version": "phoenix.scia-calculation-plan/1.0",
        "project_id": "TEST-PROJECT",
        "analysis_type": "LIN",
        "seed_esa": "projects/runtime/TEST-PROJECT/inputs/structural/scia/base.esa",
        "input_xml": None,
        "evidence_root": "projects/runtime/TEST-PROJECT/results/scia/run_001",
        "document_export": {
            "type": "PDF",
            "output_file": "projects/runtime/TEST-PROJECT/results/scia/run_001/scia_document.pdf",
            "document_name": None,
        },
        "output_xml": None,
        "output_xml_format": None,
        "expected_project_generated_exports": [],
    }


class BridgeTests(unittest.TestCase):
    def repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        seed = root / "projects/runtime/TEST-PROJECT/inputs/structural/scia/base.esa"
        seed.parent.mkdir(parents=True)
        seed.write_bytes(b"ESA-SEED")
        exe = root / "fake_esa_xml.exe"
        exe.write_bytes(b"fake")
        return tmp, root, exe

    def test_01_default_target_is_detected_scia_18_1_path(self):
        self.assertIn("Engineer18.1", DEFAULT_ESA_XML)
        self.assertTrue(DEFAULT_ESA_XML.lower().endswith("esa_xml.exe"))

    def test_02_valid_plan(self):
        tmp, root, exe = self.repo()
        try:
            self.assertEqual([], validate_plan(plan_template(), root))
        finally:
            tmp.cleanup()

    def test_03_rejects_unknown_analysis_type(self):
        tmp, root, exe = self.repo()
        try:
            plan = plan_template()
            plan["analysis_type"] = "MADE_UP"
            self.assertTrue(any("analysis_type" in e for e in validate_plan(plan, root)))
        finally:
            tmp.cleanup()

    def test_04_rejects_path_escape(self):
        tmp, root, exe = self.repo()
        try:
            plan = plan_template()
            plan["evidence_root"] = "../outside"
            self.assertTrue(any(e.startswith("path:") for e in validate_plan(plan, root)))
        finally:
            tmp.cleanup()

    def test_05_dry_run_never_starts_scia(self):
        tmp, root, exe = self.repo()
        try:
            result = execute_plan(plan_template(), root, esa_xml_executable=exe, dry_run=True)
            self.assertEqual(STATUS_READY, result["status"])
            self.assertFalse(result["scia_calculation_started"])
            self.assertTrue(result["professional_review_required"])
        finally:
            tmp.cleanup()

    def test_06_command_is_argument_list_and_contains_lin(self):
        tmp, root, exe = self.repo()
        try:
            plan = plan_template()
            evidence = root / "evidence"
            evidence.mkdir()
            seed = root / plan["seed_esa"]
            cmd = build_esa_xml_command(plan, root, exe, seed, evidence / "run.log")
            self.assertIsInstance(cmd, list)
            self.assertEqual("LIN", cmd[1])
            self.assertIn("/tPDF", cmd)
        finally:
            tmp.cleanup()

    @patch("phoenix.integrations.scia.professional_engineering_bridge_v1_0.subprocess.run")
    def test_07_zero_exit_plus_expected_output_is_only_calculated_unverified(self, run_mock):
        tmp, root, exe = self.repo()
        try:
            plan = plan_template()
            output = root / plan["document_export"]["output_file"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"PDF")
            run_mock.return_value = Mock(returncode=0, stdout="ok", stderr="")
            result = execute_plan(plan, root, esa_xml_executable=exe, dry_run=False)
            self.assertEqual(STATUS_CALCULATED, result["status"])
            self.assertEqual("NOT_YET_INDEPENDENTLY_VERIFIED", result["verification_status"])
            self.assertTrue(result["professional_review_required"])
        finally:
            tmp.cleanup()

    @patch("phoenix.integrations.scia.professional_engineering_bridge_v1_0.subprocess.run")
    def test_08_missing_expected_output_fails_closed(self, run_mock):
        tmp, root, exe = self.repo()
        try:
            run_mock.return_value = Mock(returncode=0, stdout="ok", stderr="")
            result = execute_plan(plan_template(), root, esa_xml_executable=exe, dry_run=False)
            self.assertNotEqual(STATUS_CALCULATED, result["status"])
            self.assertTrue(result["missing_expected_outputs"])
        finally:
            tmp.cleanup()

    def test_09_missing_esa_xml_is_invalid(self):
        tmp, root, exe = self.repo()
        try:
            result = execute_plan(plan_template(), root, esa_xml_executable=root/"missing.exe", dry_run=True)
            self.assertEqual(STATUS_INVALID, result["status"])
        finally:
            tmp.cleanup()

    def test_10_release_and_professional_locks_are_hard(self):
        tmp, root, exe = self.repo()
        try:
            result = execute_plan(plan_template(), root, esa_xml_executable=exe, dry_run=True)
            safety = result["safety"]
            self.assertFalse(safety["automatic_professional_approval"])
            self.assertFalse(safety["automatic_code_compliance_claim"])
            self.assertEqual("LOCKED", safety["production_release"])
            self.assertEqual("LOCKED", safety["for_construction_release"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
