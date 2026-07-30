from pathlib import Path
import json, unittest
ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_config(self):
        c=json.loads((ROOT/"configs/phoenix/opensees_engine_setup_v5_5_0.json").read_text(encoding="utf-8"))
        self.assertEqual(c["official_version"],"3.8.0.0")
        self.assertEqual(c["package"],"openseespy==3.8.0.0")
        self.assertFalse(c["acceptance"]["simulated_results_allowed"])
    def test_acceptance_contract(self):
        t=(ROOT/"phoenix/adapters/open_source/opensees_acceptance_v5_5_0.py").read_text(encoding="utf-8")
        self.assertIn('ops.element("truss"',t)
        self.assertIn('ops.analysis("Static")',t)
        self.assertIn("vertical_reaction_sum",t)
    def test_registry_tool(self):
        t=(ROOT/"tools/opensees/activate_opensees_adapter_v5_5_0.py").read_text(encoding="utf-8")
        self.assertIn("OpenSeesPyAdapter",t)

if __name__=="__main__":
    unittest.main()


class PowerShellLauncherRecoveryTests(unittest.TestCase):
    def test_launcher_recovery_documented(self):
        doc = ROOT / "docs/architecture/PHOENIX_OPENSEES_POWERSHELL_PYTHON_LAUNCHER_RECOVERY_v5_5_1.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("separate launcher variable", text)
        self.assertIn("resolved Python executable", text)


class CommandPathPropertyRecoveryTests(unittest.TestCase):
    def test_command_path_property_recovery_documented(self):
        doc = (
            ROOT
            / "docs/architecture/"
              "PHOENIX_OPENSEES_COMMAND_PATH_PROPERTY_RECOVERY_v5_5_2.md"
        )
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("Path", text)
        self.assertIn("Source", text)
        self.assertIn("Definition", text)
        self.assertIn("Test-Path", text)

# v5.5.3 uses PSObject.Properties for StrictMode-safe command resolution.


class PyCommandShadowingRecoveryTests(unittest.TestCase):
    def test_shadowing_recovery_documented(self):
        doc = (
            ROOT
            / "docs/architecture/"
              "PHOENIX_OPENSEES_PY_COMMAND_SHADOWING_RECOVERY_v5_5_4.md"
        )
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("Invoke-PhoenixPython", text)
        self.assertIn("CommandType Application", text)
        self.assertIn("py.exe", text)


class DedicatedPythonRuntimeTests(unittest.TestCase):
    def test_dedicated_runtime_config(self):
        cfg = json.loads(
            (ROOT / "configs/phoenix/opensees_engine_setup_v5_5_0.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["runtime"]["python_major_minor"], "3.12")
        self.assertEqual(
            cfg["runtime"]["winget_package"],
            "Python.Python.3.12",
        )
        self.assertIn(
            r"C:\PHOENIX-ENGINES\OpenSeesPy\3.8.0.0\venv",
            cfg["runtime"]["venv_root"],
        )
        self.assertIn("openseespywin==3.8.0.0", cfg["packages"])
