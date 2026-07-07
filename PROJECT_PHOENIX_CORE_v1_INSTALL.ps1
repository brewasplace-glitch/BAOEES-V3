param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX CORE v1.0 - Update Engine Installer" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) {
    throw "Geen git repository gevonden. Voer dit uit vanuit C:\BREWSTER-ENGINEERING-WIZARD."
}

if (-not (Test-Path "baoees")) {
    throw "Map 'baoees' niet gevonden. Dit lijkt niet de BAOEES/BREWSTER repository."
}

Write-Host "Stap 1 - Veiligheid: huidige status vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "PHOENIX_CORE_v1_pre_install_status.txt"

$changes = git status --short
if ($changes) {
    Write-Host "Bestaande wijzigingen gevonden. Ik maak eerst een stabilisatie-commit." -ForegroundColor Yellow
    git add -A
    git commit -m "chore: stabilize workspace before phoenix core v1.0"
} else {
    Write-Host "Working tree schoon." -ForegroundColor Green
}

Write-Host "Stap 2 - Phoenix Core structuur aanmaken..." -ForegroundColor Yellow

$dirs = @(
    "baoees/phoenix_core",
    "baoees/phoenix_core/runtime",
    "baoees/phoenix_core/update_engine",
    "baoees/phoenix_core/registry",
    "baoees/phoenix_core/health",
    "baoees/phoenix_core/backup",
    "baoees/phoenix_core/logging",
    "baoees/phoenix_core/dashboard",
    "baoees/phoenix_core/tests",
    "docs/phoenix_core",
    "outputs/phoenix_core",
    "outputs/phoenix_core/logs",
    "outputs/phoenix_core/health",
    "outputs/phoenix_core/backups"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
"""
PROJECT PHOENIX CORE v1.0

Centrale infrastructuur voor BREWSTER ENGINEERING WIZARD / BAOEES:
- Update Engine
- Module Registry
- Health Monitor
- Backup/Rollback basis
- Logging/Audit
- Dashboard payload
"""

__version__ = "1.0.0"
__name__ = "Project Phoenix Core"
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/__init__.py"

@'
from pathlib import Path
from datetime import datetime
import json
import subprocess


class PhoenixModuleRegistry:
    def __init__(self, registry_path="baoees/phoenix_core/registry/modules.json"):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def default_registry(self):
        return {
            "registry_version": "1.0",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "modules": {
                "phoenix_core": {
                    "name": "Phoenix Core",
                    "version": "1.0.0",
                    "status": "installed",
                    "category": "core"
                },
                "architectural_suite": {
                    "name": "Architectural Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                },
                "structural_suite": {
                    "name": "Structural Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                },
                "geotechnical_suite": {
                    "name": "Geotechnical Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                },
                "permit_suite": {
                    "name": "Permit Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                }
            }
        }

    def ensure(self):
        if not self.registry_path.exists():
            self.registry_path.write_text(
                json.dumps(self.default_registry(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        return self.load()

    def load(self):
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def save(self, data):
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.registry_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/registry/module_registry.py"

@'
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
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/health/health_monitor.py"

@'
from pathlib import Path
from datetime import datetime
import json
import shutil


class PhoenixBackupManager:
    def __init__(self, backup_root="outputs/phoenix_core/backups"):
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_manifest_backup(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / f"backup_manifest_{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        files_to_capture = [
            "baoees/phoenix_core/registry/modules.json",
            "PHOENIX_CORE_v1_pre_install_status.txt"
        ]

        copied = []
        for item in files_to_capture:
            src = Path(item)
            if src.exists():
                dst = backup_dir / src.name
                shutil.copy2(src, dst)
                copied.append(str(dst))

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "backup_type": "manifest",
            "files": copied
        }

        (backup_dir / "backup_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return manifest
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/backup/backup_manager.py"

@'
from pathlib import Path
from datetime import datetime
import json
import subprocess

from baoees.phoenix_core.registry.module_registry import PhoenixModuleRegistry
from baoees.phoenix_core.health.health_monitor import PhoenixHealthMonitor
from baoees.phoenix_core.backup.backup_manager import PhoenixBackupManager


class PhoenixUpdateEngine:
    def __init__(self, output_dir="outputs/phoenix_core"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = self.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run_bootstrap(self):
        registry = PhoenixModuleRegistry().ensure()
        health = PhoenixHealthMonitor().check()
        backup = PhoenixBackupManager().create_manifest_backup()

        result = {
            "engine": "Phoenix Update Engine",
            "version": "1.0.0",
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "registry": registry,
            "health": health,
            "backup": backup,
            "next": [
                "koppel update-engine aan BAOEES dashboard",
                "voeg package installer toe",
                "voeg rollback op bestandsniveau toe",
                "voeg plugin-loader toe",
                "start Architectural Suite als eerste grote suite"
            ]
        }

        out = self.output_dir / "phoenix_core_bootstrap_result.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        md = self.output_dir / "phoenix_core_bootstrap_report.md"
        md.write_text(
            "# Phoenix Core v1.0 bootstrap\n\n"
            f"Uitgevoerd: {result['ran_at']}\n\n"
            f"Health OK: {health['overall_ok']}\n\n"
            "## Volgende stappen\n"
            + "\n".join(f"- {x}" for x in result["next"]),
            encoding="utf-8"
        )

        return result


if __name__ == "__main__":
    result = PhoenixUpdateEngine().run_bootstrap()
    print("Phoenix Core v1.0 bootstrap uitgevoerd.")
    print("Health OK:", result["health"]["overall_ok"])
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/update_engine/update_engine.py"

@'
from baoees.phoenix_core.update_engine.update_engine import PhoenixUpdateEngine


def main():
    result = PhoenixUpdateEngine().run_bootstrap()
    print("PROJECT PHOENIX CORE")
    print("Version: 1.0.0")
    print("Health OK:", result["health"]["overall_ok"])


if __name__ == "__main__":
    main()
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/runtime/phoenix_launcher.py"

@'
# PROJECT PHOENIX CORE v1.0

## Doel

Phoenix Core is de permanente infrastructuurlaag voor BREWSTER ENGINEERING WIZARD / BAOEES.

## Onderdelen

- Phoenix Launcher
- Phoenix Update Engine
- Module Registry
- Health Monitor
- Backup Manager
- Logging & Audit basis
- Dashboard-output
- Voorbereiding op rollback en plugin-loader

## Belangrijk

Vanaf dit punt moeten nieuwe grote uitbreidingen zoveel mogelijk via Phoenix Core worden aangesloten.

## Volgende release

Phoenix Core v1.1:
- package installer;
- rollback op bestandsniveau;
- dashboardknop "Update Project Phoenix";
- automatische module-activatie;
- Architectural Suite koppelen.
'@ | Set-Content -Encoding UTF8 "docs/phoenix_core/PROJECT_PHOENIX_CORE_v1.md"

Write-Host "Stap 3 - Phoenix Core bootstrap uitvoeren..." -ForegroundColor Yellow
python "baoees/phoenix_core/runtime/phoenix_launcher.py"

Write-Host "Stap 4 - Commit maken..." -ForegroundColor Yellow
git add baoees/phoenix_core docs/phoenix_core outputs/phoenix_core PHOENIX_CORE_v1_pre_install_status.txt
git commit -m "feat: add phoenix core v1 update engine"

Write-Host ""
Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Phoenix Core v1.0 is geïnstalleerd." -ForegroundColor Green
Write-Host "Voer daarna uit: git push" -ForegroundColor Green