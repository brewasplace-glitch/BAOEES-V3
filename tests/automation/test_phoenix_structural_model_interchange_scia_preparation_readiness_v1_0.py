from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy.structural_model_interchange_scia_preparation_v1_0 import (
    VALID, INVALID, SCIA_MODEL_BUILD_REQUIRED,
    SCIA_ANALYSIS_SCOPE_REQUIRED, SCIA_SEED_XML_PREPARATION_READY,
    canonical_model_sha256, prepare_scia, validate_model, SAFETY as MODEL_SAFETY,
)
from phoenix.integrations.scia.environment_readiness_v1_0 import (
    SCIA_EXIT_CODES, RUNTIME_NOT_FOUND, LICENSE_SERVER_UNREACHABLE,
    READY_FOR_PROBE, LIVE_AUTH_REQUIRED, APPLICATION_ENV_BLOCKED,
    parse_license_target, inspect_environment, probe_application_environment,
    SAFETY as ENV_SAFETY,
)


def valid_model():
    return {
        "schema_version": "phoenix.canonical-structural-model/1.0",
        "model_id": "TEST-MODEL-001",
        "units": {"length": "m", "force": "N", "mass": "kg", "temperature": "C"},
        "nodes": [
            {"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": "N2", "x": 5.0, "y": 0.0, "z": 0.0},
        ],
        "materials": [{"id": "MAT1", "properties": {}}],
        "sections": [{"id": "SEC1", "properties": {}}],
        "members": [{"id": "B1", "start_node": "N1", "end_node": "N2", "material": "MAT1", "section": "SEC1"}],
        "supports": [{"id": "S1", "node": "N1"}, {"id": "S2", "node": "N2"}],
        "load_cases": [{"id": "LC1"}],
        "nodal_loads": [],
        "line_loads": [{"id": "LF1", "member": "B1", "load_case": "LC1", "fz": -1000.0}],
        "load_combinations": [{"id": "COMB1", "terms": [{"load_case": "LC1", "factor": 1.0}]}],
        "metadata": {"normative_scope": "NOT_ASSUMED"},
    }


class CombinedPackTests(unittest.TestCase):
    def test_01_valid_model_passes(self):
        self.assertEqual(VALID, validate_model(valid_model())["status"])

    def test_02_unknown_member_node_fails(self):
        m = valid_model()
        m["members"][0]["end_node"] = "MISSING"
        result = validate_model(m)
        self.assertEqual(INVALID, result["status"])
        self.assertTrue(any("unknown_reference:MISSING" in e for e in result["errors"]))

    def test_03_duplicate_ids_fail(self):
        m = valid_model()
        m["nodes"].append(dict(m["nodes"][0]))
        self.assertEqual(INVALID, validate_model(m)["status"])

    def test_04_load_case_cross_reference_is_enforced(self):
        m = valid_model()
        m["line_loads"][0]["load_case"] = "NOPE"
        self.assertEqual(INVALID, validate_model(m)["status"])

    def test_05_canonical_hash_is_deterministic(self):
        a = valid_model()
        b = json.loads(json.dumps(a))
        self.assertEqual(canonical_model_sha256(a), canonical_model_sha256(b))

    def test_06_prepare_without_seed_stays_model_build_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = root / "model.json"
            model.write_text(json.dumps(valid_model()), encoding="utf-8")
            result = prepare_scia(model, root / "out")
            self.assertEqual(SCIA_MODEL_BUILD_REQUIRED, result["status"])
            self.assertEqual("NOT_PERFORMED", result["manifest"]["binary_esa_synthesis"])

    def test_07_seed_xml_without_analysis_requires_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = root / "model.json"
            model.write_text(json.dumps(valid_model()), encoding="utf-8")
            seed = root / "seed.esa"; seed.write_bytes(b"SEN\x00TEST")
            xml = root / "u.xml"; xml.write_text("<project/>", encoding="utf-8")
            deff = root / "u.xml.def"; deff.write_text("<def_project/>", encoding="utf-8")
            result = prepare_scia(model, root / "out", seed, xml, deff)
            self.assertEqual(SCIA_ANALYSIS_SCOPE_REQUIRED, result["status"])

    def test_08_seed_xml_with_scope_is_preparation_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = root / "model.json"
            model.write_text(json.dumps(valid_model()), encoding="utf-8")
            seed = root / "seed.esa"; seed.write_bytes(b"SEN\x00TEST")
            xml = root / "u.xml"; xml.write_text("<project/>", encoding="utf-8")
            deff = root / "u.xml.def"; deff.write_text("<def_project/>", encoding="utf-8")
            result = prepare_scia(model, root / "out", seed, xml, deff, "LIN")
            self.assertEqual(SCIA_SEED_XML_PREPARATION_READY, result["status"])
            plan = json.loads((root / "out/scia_command_plan.json").read_text(encoding="utf-8"))
            self.assertEqual("NOT_EXECUTED_PREPARATION_ONLY", plan["execution"])
            self.assertEqual("LIN", plan["analysis_scope"])

    def test_09_preparation_never_claims_binary_esa_synthesis(self):
        self.assertFalse(MODEL_SAFETY["automatic_binary_esa_synthesis"])

    def test_10_exit_code_6_contract_is_exact(self):
        self.assertEqual("Unable to initialize application environment", SCIA_EXIT_CODES[6])

    def test_11_license_target_parser(self):
        self.assertEqual(("DESKTOP-TEST", 7182), parse_license_target("7182@DESKTOP-TEST"))

    def test_12_missing_runtime_is_reported(self):
        result = inspect_environment(Path("Z:/definitely/missing/ESA_XML.exe"))
        self.assertEqual(RUNTIME_NOT_FOUND, result["status"])

    @patch("phoenix.integrations.scia.environment_readiness_v1_0.esa_xml_help")
    @patch("phoenix.integrations.scia.environment_readiness_v1_0.tcp_probe")
    def test_13_unreachable_license_server_is_blocked(self, tcp_mock, help_mock):
        help_mock.return_value = {"present": True, "status": "SCIA_RUNTIME_HELP_VALIDATED"}
        tcp_mock.return_value = {"reachable": False, "host": "X", "port": 7182, "error": "closed"}
        result = inspect_environment(Path("dummy.exe"), license_target="7182@X")
        self.assertEqual(LICENSE_SERVER_UNREACHABLE, result["status"])

    def test_14_live_probe_requires_explicit_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = probe_application_environment(
                Path("missing.exe"), root / "missing.esa", root / "out", False
            )
            self.assertEqual(LIVE_AUTH_REQUIRED, result["status"])
            self.assertFalse(result["live_execution_started"])

    @patch("phoenix.integrations.scia.environment_readiness_v1_0.subprocess.run")
    def test_15_exit_code_6_maps_to_application_environment_block(self, run_mock):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            esa_xml = root / "ESA_XML.exe"; esa_xml.write_bytes(b"x")
            project = root / "beam.esa"; project.write_bytes(b"SEN\x00test")
            class CP:
                returncode = 6
                stdout = ""
                stderr = ""
            run_mock.return_value = CP()
            result = probe_application_environment(esa_xml, project, root / "out", True)
            self.assertEqual(APPLICATION_ENV_BLOCKED, result["status"])
            self.assertEqual("Unable to initialize application environment", result["return_code_meaning"])

    def test_16_environment_layer_never_controls_services_or_license(self):
        self.assertFalse(ENV_SAFETY["service_start_stop_reconfigure"])
        self.assertFalse(ENV_SAFETY["license_configuration_change"])
        self.assertFalse(ENV_SAFETY["automatic_live_probe"])

    def test_17_release_locks_remain_hard(self):
        self.assertEqual("LOCKED", MODEL_SAFETY["production_release"])
        self.assertEqual("LOCKED", MODEL_SAFETY["for_construction_release"])
        self.assertEqual("LOCKED", ENV_SAFETY["production_release"])
        self.assertEqual("LOCKED", ENV_SAFETY["for_construction_release"])


if __name__ == "__main__":
    unittest.main()
