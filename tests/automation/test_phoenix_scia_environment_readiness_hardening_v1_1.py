from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.integrations.scia.environment_readiness_hardening_v1_1 import (
    EXIT_CODES, RUNTIME_NOT_FOUND, RUNTIME_HELP_NOT_PROBED, RUNTIME_HELP_OK,
    LICENSE_TARGET_REQUIRED, LOCAL_SERVICE_STOPPED, LICENSE_UNREACHABLE,
    ENDPOINT_REACHABLE, LIVE_AUTH_REQUIRED, APP_ENV_BLOCKED,
    PROJECT_OPEN_BLOCKED, CALCULATION_BLOCKED, LIVE_READY,
    parse_license_target, is_local_host, inspect_builtin_help,
    inspect_environment, classify_existing_probe, run_live_probe, SAFETY
)

class SciaEnvironmentReadinessHardeningTests(unittest.TestCase):
    def test_01_exit_code_6_exact(self):
        self.assertEqual("Unable to initialize application environment", EXIT_CODES[6])

    def test_02_target_parser(self):
        self.assertEqual(("DESKTOP-X", 7182), parse_license_target("7182@DESKTOP-X"))

    def test_03_target_parser_rejects_bad(self):
        with self.assertRaises(ValueError):
            parse_license_target("DESKTOP-X")

    def test_04_localhost_detection(self):
        self.assertTrue(is_local_host("localhost"))
        self.assertTrue(is_local_host("127.0.0.1"))

    def test_05_missing_runtime(self):
        r = inspect_builtin_help(Path("missing.exe"), False)
        self.assertEqual(RUNTIME_NOT_FOUND, r["status"])

    def test_06_runtime_help_not_automatic(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ESA_XML.exe"
            p.write_bytes(b"x")
            r = inspect_builtin_help(p, False)
            self.assertEqual(RUNTIME_HELP_NOT_PROBED, r["status"])
            self.assertFalse(r["runtime_execution_started"])

    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.subprocess.run")
    def test_07_runtime_help_contract(self, run_mock):
        class CP:
            returncode = 2
            stdout = "Missing parameters.\nExit codes:\n6 = Unable to initialize application environment\n10 = Error during update ProjectFile by XLSX Update\n"
            stderr = ""
        run_mock.return_value = CP()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ESA_XML.exe"
            p.write_bytes(b"x")
            r = inspect_builtin_help(p, True)
            self.assertEqual(RUNTIME_HELP_OK, r["status"])
            self.assertFalse(r["solver_calculation_started"])

    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.inspect_builtin_help")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.windows_service_state")
    def test_08_license_target_required(self, svc, help_mock):
        help_mock.return_value = {"status": RUNTIME_HELP_OK, "present": True}
        svc.return_value = {"status": "RUNNING"}
        r = inspect_environment(Path("dummy"), allow_runtime_help=True)
        self.assertEqual(LICENSE_TARGET_REQUIRED, r["status"])

    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.inspect_builtin_help")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.windows_service_state")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.is_local_host")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.tcp_probe")
    def test_09_local_stopped_service_block(self, tcp, local, svc, help_mock):
        help_mock.return_value = {"status": RUNTIME_HELP_OK, "present": True}
        local.return_value = True
        tcp.return_value = {"reachable": False, "host": "X", "port": 7182, "error": "closed"}
        svc.side_effect = lambda name: {"status": "1  STOPPED" if name=="lmadmin" else "UNKNOWN"}
        r = inspect_environment(Path("dummy"), license_target="7182@X", allow_runtime_help=True)
        self.assertEqual(LOCAL_SERVICE_STOPPED, r["status"])

    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.inspect_builtin_help")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.windows_service_state")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.is_local_host")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.tcp_probe")
    def test_10_remote_unreachable_block(self, tcp, local, svc, help_mock):
        help_mock.return_value = {"status": RUNTIME_HELP_OK, "present": True}
        local.return_value = False
        tcp.return_value = {"reachable": False, "host": "REMOTE", "port": 7182, "error": "closed"}
        svc.return_value = {"status": "STOPPED"}
        r = inspect_environment(Path("dummy"), license_target="7182@REMOTE", allow_runtime_help=True)
        self.assertEqual(LICENSE_UNREACHABLE, r["status"])

    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.inspect_builtin_help")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.windows_service_state")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.is_local_host")
    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.tcp_probe")
    def test_11_reachable_is_not_solver_ready(self, tcp, local, svc, help_mock):
        help_mock.return_value = {"status": RUNTIME_HELP_OK, "present": True}
        local.return_value = True
        tcp.return_value = {"reachable": True, "host": "X", "port": 7182, "error": None}
        svc.return_value = {"status": "RUNNING"}
        r = inspect_environment(Path("dummy"), license_target="7182@X", allow_runtime_help=True)
        self.assertEqual(ENDPOINT_REACHABLE, r["status"])
        self.assertNotEqual(LIVE_READY, r["status"])

    def test_12_classify_existing_exit_6(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "probe.json"
            p.write_text(json.dumps({"return_code": 6}), encoding="utf-8")
            r = classify_existing_probe(p)
            self.assertEqual(APP_ENV_BLOCKED, r["status"])
            self.assertEqual("Unable to initialize application environment", r["return_code_meaning"])
            self.assertFalse(r["live_probe_started_by_this_action"])

    def test_13_classify_exit_4(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "probe.json"
            p.write_text(json.dumps({"return_code": 4}), encoding="utf-8")
            self.assertEqual(PROJECT_OPEN_BLOCKED, classify_existing_probe(p)["status"])

    def test_14_classify_exit_5(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "probe.json"
            p.write_text(json.dumps({"return_code": 5}), encoding="utf-8")
            self.assertEqual(CALCULATION_BLOCKED, classify_existing_probe(p)["status"])

    def test_15_classify_exit_0_is_live_ready(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "probe.json"
            p.write_text(json.dumps({"return_code": 0}), encoding="utf-8")
            self.assertEqual(LIVE_READY, classify_existing_probe(p)["status"])

    def test_16_live_probe_requires_explicit_switch(self):
        with tempfile.TemporaryDirectory() as td:
            r = run_live_probe(Path("no.exe"), Path("no.esa"), Path(td), False)
            self.assertEqual(LIVE_AUTH_REQUIRED, r["status"])
            self.assertFalse(r["live_probe_started"])

    @patch("phoenix.integrations.scia.environment_readiness_hardening_v1_1.subprocess.run")
    def test_17_live_probe_maps_exit_6(self, run_mock):
        class CP:
            returncode = 6
            stdout = ""
            stderr = ""
        run_mock.return_value = CP()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exe = root / "ESA_XML.exe"; exe.write_bytes(b"x")
            esa = root / "Beam.esa"; esa.write_bytes(b"SEN-test")
            r = run_live_probe(exe, esa, root / "out", True)
            self.assertEqual(APP_ENV_BLOCKED, r["status"])
            self.assertTrue(r["source_project_unchanged"])

    def test_18_safety_contract(self):
        self.assertFalse(SAFETY["service_start_stop_reconfigure"])
        self.assertFalse(SAFETY["license_configuration_change"])
        self.assertFalse(SAFETY["automatic_runtime_help_probe"])
        self.assertFalse(SAFETY["automatic_live_probe"])
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])
        self.assertEqual("LOCKED", SAFETY["production_release"])
        self.assertEqual("LOCKED", SAFETY["for_construction_release"])

if __name__ == "__main__":
    unittest.main()
