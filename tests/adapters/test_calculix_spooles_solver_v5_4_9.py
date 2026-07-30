from pathlib import Path
import json
import tempfile
import unittest

from phoenix.adapters.open_source.calculix_acceptance_v5_4_9 import (
    MODEL,
    parse_version,
)

ROOT = Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_config(self):
        cfg = json.loads(
            (
                ROOT / "configs/phoenix/calculix_msys2_repository_variable_v5_4_4.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["official_version"], "2.23")
        self.assertEqual(cfg["windows_binary_provider"], "MSYS2")
        self.assertEqual(cfg["msys2_install_strategy"]["primary"], "winget package MSYS2.MSYS2")
        self.assertTrue(cfg["repository_rollback_policy"]["rollback_after_payload_copy_only"])
        self.assertEqual(cfg["mirror_policy"]["mingw"], "https://repo.msys2.org/mingw/$repo/")
        self.assertEqual(cfg["mirror_policy"]["msys"], "https://repo.msys2.org/msys/$arch/")
        self.assertEqual(cfg["retry_policy"]["package_install_attempts"], 5)
        self.assertTrue(cfg["retry_policy"]["pacman_cache_preserved"])
        self.assertEqual(cfg["expected_executable"], r"C:\msys64\mingw64\bin\ccx.exe")
        self.assertEqual(cfg["environment_variable"], "CALCULIX_CCX_EXE")
        self.assertFalse(cfg["acceptance"]["simulated_results_allowed"])

    def test_model_contract(self):
        self.assertIn("*ELEMENT, TYPE=C3D8", MODEL)
        self.assertIn("*STATIC", MODEL)
        self.assertIn("*NODE FILE", MODEL)
        self.assertIn("*EL FILE", MODEL)

    def test_version_parser(self):
        self.assertEqual(parse_version("CalculiX Version 2.23"), "2.23")

if __name__ == "__main__":
    unittest.main()

# v5.4.4 verifies mirrorlist.mingw uses $repo and mirrorlist.msys uses $arch.

# v5.4.5 executes the package verifier from the installer payload.


class RuntimePathTests(unittest.TestCase):
    def test_runtime_path_launcher(self):
        p = ROOT / "phoenix/adapters/open_source/calculix_windows.py"
        text = p.read_text(encoding="utf-8")
        self.assertIn("build_calculix_environment", text)
        self.assertIn('env["PATH"] = str(runtime_bin)', text)
        self.assertIn("probe_ccx", text)


class InputArgumentTests(unittest.TestCase):
    def test_ccx_input_argument(self):
        p = ROOT / "phoenix/adapters/open_source/calculix_windows.py"
        text = p.read_text(encoding="utf-8")
        self.assertIn(
            '[str(executable.resolve()), "-i", model_stem]',
            text,
        )

    def test_solver_failure_logs_are_printed(self):
        p = ROOT / "phoenix/adapters/open_source/calculix_acceptance_v5_4_9.py"
        text = p.read_text(encoding="utf-8")
        self.assertIn("===== CALCULIX STDOUT =====", text)
        self.assertIn("===== CALCULIX STDERR =====", text)


class LoadStepOrderTests(unittest.TestCase):
    def test_cload_inside_step(self):
        from phoenix.adapters.open_source.calculix_acceptance_v5_4_9 import MODEL
        self.assertLess(MODEL.index("*STEP"), MODEL.index("*CLOAD"))
        self.assertLess(MODEL.index("*CLOAD"), MODEL.index("*END STEP"))
        self.assertNotIn("*CLOAD", MODEL.split("*STEP", 1)[0])


class SpoolesSolverTests(unittest.TestCase):
    def test_static_step_selects_spooles(self):
        from phoenix.adapters.open_source.calculix_acceptance_v5_4_9 import MODEL
        self.assertIn("*STATIC, SOLVER=SPOOLES", MODEL)
        self.assertNotIn("*STATIC\n*CLOAD", MODEL)

    def test_acceptance_rejects_pastix(self):
        path = ROOT / "phoenix/adapters/open_source/calculix_acceptance_v5_4_9.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn(
            "unexpectedly selected PaStiX instead of SPOOLES",
            text,
        )
        self.assertIn(
            "does not confirm the required SPOOLES solver",
            text,
        )
