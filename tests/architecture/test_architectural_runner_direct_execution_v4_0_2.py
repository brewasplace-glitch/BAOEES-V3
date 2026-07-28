from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "runners/PROJECT_PHOENIX_architectural_suite_v4_0_0.py"
MODEL = ROOT / "configs/projects/moskee_bunschoten_architectural_model_v4_0_0.json"

with tempfile.TemporaryDirectory() as td:
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--model", str(MODEL), "--output", td],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "PROJECT PHOENIX ARCHITECTURAL SUITE v4.0.0 COMPLETED" in result.stdout
    assert (Path(td) / "05_artifact_manifest.json").is_file()

print("ARCHITECTURAL RUNNER DIRECT EXECUTION TEST PASSED")
