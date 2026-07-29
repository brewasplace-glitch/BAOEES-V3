import unittest
from unittest.mock import Mock, patch

from phoenix.adapters.open_source.engines import IfcOpenShellAdapter

class IfcOpenShellDualDetectionTests(unittest.TestCase):
    def test_python_module_takes_precedence(self):
        module = Mock(
            available=True,
            executable="python.exe",
            source="python_module",
            version_text="0.8.5",
            notes=[],
        )
        adapter = IfcOpenShellAdapter()
        with patch.object(adapter, "detect_python_module", return_value=module):
            with patch("shutil.which", return_value="IfcConvert.exe"):
                result = adapter.detect()
        self.assertEqual(result.source, "python_module")
        self.assertEqual(result.version_text, "0.8.5")

    def test_executable_fallback_when_module_absent(self):
        adapter = IfcOpenShellAdapter()
        completed = Mock(returncode=0, stdout="IfcConvert 0.8.5\n", stderr="")
        with patch.object(adapter, "detect_python_module", return_value=None):
            with patch("shutil.which", return_value="C:/Tools/IfcConvert.exe"):
                with patch("subprocess.run", return_value=completed):
                    result = adapter.detect()
        self.assertTrue(result.available)
        self.assertEqual(result.source, "PATH")
        self.assertEqual(result.executable, "C:/Tools/IfcConvert.exe")

if __name__ == "__main__":
    unittest.main()
