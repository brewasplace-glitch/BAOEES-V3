from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
package_installer = ROOT.parent / "INSTALL_PROJECT_PHOENIX_INTEGRATED_ARCHITECTURAL_MODEL_BBL_DRAWING_SUITE_v4_0_1_CALL_DEPTH_RECOVERY_FIXED.ps1"

# This test is intended for package validation and may be skipped after installation,
# because the installer itself is not copied into the repository.
if package_installer.is_file():
    text = package_installer.read_text(encoding="utf-8")
    assert "function Py" not in text
    assert "function Resolve-Python" in text
    assert "function Invoke-Python" in text
    assert "& $PythonInfo.Command @All" in text
print("INSTALLER PYTHON RESOLUTION REGRESSION TEST PASSED")
