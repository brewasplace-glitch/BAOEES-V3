param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX CORE v1.1 - Manager Upgrade" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) { throw "Geen git repository gevonden." }
if (-not (Test-Path "baoees/phoenix_core")) { throw "Phoenix Core v1.0 niet gevonden." }

Write-Host "Stap 1 - DOCS/phoenix_core netjes opnemen indien aanwezig..." -ForegroundColor Yellow
if (Test-Path "DOCS/phoenix_core") {
    git add DOCS/phoenix_core
    git commit -m "docs: add phoenix core documentation" 2>$null
}

Write-Host "Stap 2 - Phoenix Core v1.1 mappen aanmaken..." -ForegroundColor Yellow

$dirs = @(
    "baoees/phoenix_core/package_manager",
    "baoees/phoenix_core/versioning",
    "baoees/phoenix_core/plugin_loader",
    "baoees/phoenix_core/dashboard",
    "outputs/phoenix_core/dashboard",
    "outputs/phoenix_core/packages"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
from pathlib import Path
from datetime import datetime
import json


class PhoenixDashboardBuilder:
    def __init__(self, output_dir="outputs/phoenix_core/dashboard"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, registry_path="baoees/phoenix_core/registry/modules.json"):
        registry_file = Path(registry_path)
        registry = {}
        if registry_file.exists():
            registry = json.loads(registry_file.read_text(encoding="utf-8"))

        payload = {
            "dashboard": "Project Phoenix Core Dashboard",
            "version": "1.1.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "registry": registry,
            "cards": [
                {"title": "Phoenix Core", "status": "installed", "type": "core"},
                {"title": "Architectural Suite", "status": "next", "type": "suite"},
                {"title": "Structural Suite", "status": "planned", "type": "suite"},
                {"title": "Geotechnical Suite", "status": "planned", "type": "suite"},
                {"title": "Permit Suite", "status": "planned", "type": "suite"}
            ]
        }

        (self.output_dir / "phoenix_dashboard_payload.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        markdown = "# Project Phoenix Dashboard\n\n"
        markdown += f"Versie: {payload['version']}\n\n"
        markdown += "## Modules\n\n"
        for card in payload["cards"]:
            markdown += f"- {card['title']} — {card['status']}\n"

        (self.output_dir / "phoenix_dashboard.md").write_text(markdown, encoding="utf-8")
        return payload
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/dashboard/dashboard_builder.py"

@'
from pathlib import Path
from datetime import datetime
import json


class PhoenixPackageManager:
    def __init__(self, package_dir="outputs/phoenix_core/packages"):
        self.package_dir = Path(package_dir)
        self.package_dir.mkdir(parents=True, exist_ok=True)

    def create_package_manifest(self, package_name, version, files=None):
        manifest = {
            "package_name": package_name,
            "version": version,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "files": files or [],
            "status": "manifest_created"
        }

        out = self.package_dir / f"{package_name}_{version}_manifest.json"
        out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/package_manager/package_manager.py"

@'
from pathlib import Path
from datetime import datetime
import json


class PhoenixVersionManager:
    def __init__(self, version_file="baoees/phoenix_core/versioning/phoenix_version.json"):
        self.version_file = Path(version_file)
        self.version_file.parent.mkdir(parents=True, exist_ok=True)

    def set_version(self, version="1.1.0"):
        data = {
            "product": "Project Phoenix Core",
            "version": version,
            "updated_at": datetime.now().isoformat(timespec="seconds")
        }
        self.version_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/versioning/version_manager.py"

@'
from pathlib import Path
from datetime import datetime
import json


class PhoenixPluginLoader:
    def __init__(self, registry_path="baoees/phoenix_core/registry/modules.json"):
        self.registry_path = Path(registry_path)

    def list_plugins(self):
        if not self.registry_path.exists():
            return {"plugins": [], "warning": "registry not found"}

        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        plugins = []
        for key, value in registry.get("modules", {}).items():
            plugins.append({
                "id": key,
                "name": value.get("name", key),
                "version": value.get("version", "0.0.0"),
                "status": value.get("status", "unknown"),
                "category": value.get("category", "unknown")
            })

        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "plugins": plugins
        }
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/plugin_loader/plugin_loader.py"

@'
from baoees.phoenix_core.dashboard.dashboard_builder import PhoenixDashboardBuilder
from baoees.phoenix_core.package_manager.package_manager import PhoenixPackageManager
from baoees.phoenix_core.versioning.version_manager import PhoenixVersionManager
from baoees.phoenix_core.plugin_loader.plugin_loader import PhoenixPluginLoader


def main():
    version = PhoenixVersionManager().set_version("1.1.0")
    dashboard = PhoenixDashboardBuilder().build()
    package = PhoenixPackageManager().create_package_manifest(
        "phoenix_core",
        "1.1.0",
        files=[
            "dashboard_builder.py",
            "package_manager.py",
            "version_manager.py",
            "plugin_loader.py"
        ]
    )
    plugins = PhoenixPluginLoader().list_plugins()

    print("Phoenix Core v1.1 Manager Upgrade voltooid.")
    print("Version:", version["version"])
    print("Dashboard cards:", len(dashboard["cards"]))
    print("Plugins:", len(plugins.get("plugins", [])))
    print("Package:", package["package_name"], package["version"])


if __name__ == "__main__":
    main()
'@ | Set-Content -Encoding UTF8 "baoees/phoenix_core/runtime/phoenix_core_v1_1_upgrade.py"

@'
# PROJECT PHOENIX CORE v1.1

## Toegevoegd

- Dashboard Builder
- Package Manager basis
- Version Manager
- Plugin Loader basis
- Dashboard payload export
- Package manifest export

## Doel

Phoenix Core wordt nu de vaste beheerlaag voor toekomstige suites.

## Volgende stap

Architectural Suite v1.0 aansluiten als eerste echte suite bovenop Phoenix Core.
'@ | Set-Content -Encoding UTF8 "docs/phoenix_core/PROJECT_PHOENIX_CORE_v1_1.md"

Write-Host "Stap 3 - v1.1 upgrade uitvoeren..." -ForegroundColor Yellow
python "baoees/phoenix_core/runtime/phoenix_core_v1_1_upgrade.py"

Write-Host "Stap 4 - Commit maken..." -ForegroundColor Yellow
git add baoees/phoenix_core docs/phoenix_core outputs/phoenix_core
git commit -m "feat: upgrade phoenix core to v1.1 manager layer"

Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Phoenix Core v1.1 is geïnstalleerd." -ForegroundColor Green
Write-Host "Voer daarna uit: git push" -ForegroundColor Green