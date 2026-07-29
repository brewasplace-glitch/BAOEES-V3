import unittest
from unittest.mock import Mock, patch
from phoenix.adapters.open_source.engines import IfcOpenShellAdapter

class Tests(unittest.TestCase):
    def test_python_module_detection(self):
        cp = Mock(returncode=0, stdout="0.8.5\n", stderr="")
        with patch("subprocess.run", return_value=cp):
            result = IfcOpenShellAdapter().detect()
        self.assertTrue(result.available)
        self.assertEqual(result.source, "python_module")
        self.assertEqual(result.version_text, "0.8.5")

if __name__ == "__main__":
    unittest.main()
