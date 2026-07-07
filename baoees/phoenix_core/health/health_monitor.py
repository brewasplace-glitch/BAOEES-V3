from pathlib import Path
from datetime import datetime
import json
import subprocess


class PhoenixHealthMonitor:
    def __init__(self, output_dir="outputs/phoenix_core/health"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def check(self):
        required_paths = [
            "baoees",
            "baoees/phoenix_core",
            "baoees/phoenix_core/update_engine",
            "baoees/phoenix_core/registry",
            "docs",
            "outputs"
        ]

        path_results = {
            path: Path(path).exists()
            for path in required_paths
        }

        git_ok = Path(".git").exists()

        python_ok = True
        try:
            subprocess.run(["python", "--version"], capture_output=True, text=True, check=False)
        except Exception:
            python_ok = False

        result = {
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "phoenix_core_version": "1.0.0",
            "git_repository_detected": git_ok,
            "python_available": python_ok,
            "paths": path_results,
            "overall_ok": git_ok and python_ok and all(path_results.values())
        }

        out = self.output_dir / "phoenix_health_check.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return result
