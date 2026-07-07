param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX - Intelligence Layer v1.0" -ForegroundColor Cyan
Write-Host "PKB + BIB Integration" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) { throw "Geen git repository gevonden." }

Write-Host "Stap 1 - Huidige status veilig vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "PHOENIX_INTELLIGENCE_v1_pre_install_status.txt"

$changes = git status --short
if ($changes) {
    git add -A
    git commit -m "chore: stabilize before phoenix intelligence layer v1.0"
}

Write-Host "Stap 2 - Intelligence Layer structuur aanmaken..." -ForegroundColor Yellow

$dirs = @(
    "project_phoenix",
    "project_phoenix/intelligence",
    "project_phoenix/intelligence/pkb",
    "project_phoenix/intelligence/bib",
    "project_phoenix/intelligence/knowledge_graph",
    "project_phoenix/intelligence/decision_log",
    "project_phoenix/intelligence/source_evidence",
    "project_phoenix/intelligence/standards",
    "project_phoenix/intelligence/templates",
    "project_phoenix/intelligence/prompts",
    "project_phoenix/intelligence/master_specification",
    "project_phoenix/intelligence/search",
    "phoenix_intelligence/pkb",
    "phoenix_intelligence/bib",
    "phoenix_intelligence/knowledge_graph",
    "phoenix_intelligence/decision_log",
    "phoenix_intelligence/source_evidence",
    "docs/project_phoenix/intelligence",
    "outputs/phoenix_intelligence"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
"""
Project Phoenix package.

Nieuwe hoofdstructuur voor toekomstige ontwikkeling.
Bestaande BAOEES-code blijft voorlopig compatibel.
"""
__version__ = "0.1.0"
'@ | Set-Content -Encoding UTF8 "project_phoenix/__init__.py"

@'
"""
Phoenix Intelligence Layer

Integreert:
- PKB
- BIB
- Knowledge Graph
- Decision Log
- STEE / Source Evidence
- Standards
- Templates
- Prompt Library
- Master Specification
"""
__version__ = "1.0.0"
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/__init__.py"

@'
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import json


@dataclass
class KnowledgeItem:
    id: str
    title: str
    category: str
    discipline: str
    content: str
    source: str = "manual"
    tags: List[str] = None
    created_at: str = None

    def to_dict(self):
        data = asdict(self)
        if data["tags"] is None:
            data["tags"] = []
        if data["created_at"] is None:
            data["created_at"] = datetime.now().isoformat(timespec="seconds")
        return data


class PhoenixKnowledgeBase:
    def __init__(self, root="phoenix_intelligence/pkb"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.root / "pkb_registry.json"

    def bootstrap(self):
        items = [
            KnowledgeItem(
                id="pkb_001",
                title="Project Phoenix is het hoofdplatform",
                category="architecture",
                discipline="platform",
                content="BREWSTER ENGINEERING WIZARD blijft de gebruikersapplicatie; Project Phoenix wordt het onderliggende platform.",
                source="architecture_decision",
                tags=["phoenix", "brewster", "platform"]
            ),
            KnowledgeItem(
                id="pkb_002",
                title="BIB wordt geïntegreerd in PKB",
                category="knowledge",
                discipline="intelligence",
                content="De Brewster Intelligence Bibliotheek wordt opgenomen in de Phoenix Knowledge Base en niet separaat onderhouden.",
                source="architecture_decision",
                tags=["bib", "pkb", "knowledge"]
            ),
            KnowledgeItem(
                id="pkb_003",
                title="BAOEES blijft compatibiliteitslaag",
                category="migration",
                discipline="software",
                content="De bestaande baoees-map blijft voorlopig bestaan als legacy/compatibiliteitslaag tijdens de migratie.",
                source="migration_decision",
                tags=["baoees", "legacy", "migration"]
            )
        ]

        data = {
            "pkb_version": "1.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "items": [item.to_dict() for item in items]
        }

        self.registry_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data

    def search(self, query: str) -> Dict[str, Any]:
        if not self.registry_path.exists():
            self.bootstrap()

        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        q = query.lower()
        matches = []
        for item in data.get("items", []):
            haystack = " ".join([
                item.get("title", ""),
                item.get("category", ""),
                item.get("discipline", ""),
                item.get("content", ""),
                " ".join(item.get("tags", []))
            ]).lower()
            if q in haystack:
                matches.append(item)

        return {
            "query": query,
            "count": len(matches),
            "matches": matches
        }
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/pkb/knowledge_base.py"

@'
from datetime import datetime
from pathlib import Path
import json


class BrewsterIntelligenceBibliotheek:
    def __init__(self, root="phoenix_intelligence/bib"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "bib_index.json"

    def bootstrap(self):
        data = {
            "bib_version": "1.0.0",
            "status": "integrated_into_pkb",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "domains": [
                "vision",
                "master_specification",
                "architecture",
                "bouwkunde",
                "constructie",
                "geotechniek",
                "verkeer_parkeren",
                "vergunningen",
                "digital_twin",
                "ai_workflows",
                "standards",
                "templates",
                "lessons_learned",
                "source_evidence"
            ],
            "principle": "BIB wordt niet separaat ontwikkeld; BIB is de inhoudelijke kennislaag binnen PKB."
        }

        self.index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/bib/bib_manager.py"

@'
from datetime import datetime
from pathlib import Path
import json


class PhoenixKnowledgeGraph:
    def __init__(self, root="phoenix_intelligence/knowledge_graph"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.graph_path = self.root / "knowledge_graph.json"

    def bootstrap(self):
        graph = {
            "graph_version": "1.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "nodes": [
                {"id": "project_phoenix", "type": "platform", "label": "Project Phoenix"},
                {"id": "brewster_engineering_wizard", "type": "app", "label": "Brewster Engineering Wizard"},
                {"id": "pkb", "type": "knowledge_base", "label": "Phoenix Knowledge Base"},
                {"id": "bib", "type": "knowledge_library", "label": "Brewster Intelligence Bibliotheek"},
                {"id": "phoenix_core", "type": "core", "label": "Phoenix Core"},
                {"id": "architectural_suite", "type": "suite", "label": "Architectural Suite"}
            ],
            "edges": [
                {"from": "brewster_engineering_wizard", "to": "project_phoenix", "relation": "runs_on"},
                {"from": "pkb", "to": "bib", "relation": "integrates"},
                {"from": "phoenix_core", "to": "pkb", "relation": "reads_from"},
                {"from": "architectural_suite", "to": "pkb", "relation": "uses_knowledge_from"},
                {"from": "project_phoenix", "to": "phoenix_core", "relation": "contains"},
                {"from": "project_phoenix", "to": "pkb", "relation": "contains"}
            ]
        }

        self.graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
        return graph
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/knowledge_graph/knowledge_graph.py"

@'
from datetime import datetime
from pathlib import Path
import json


class PhoenixDecisionLog:
    def __init__(self, root="phoenix_intelligence/decision_log"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "decision_log.json"

    def bootstrap(self):
        decisions = {
            "decision_log_version": "1.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "decisions": [
                {
                    "id": "ADR-0001",
                    "title": "Repository wordt PROJECT-PHOENIX",
                    "status": "accepted",
                    "decision": "De repository is hernoemd naar PROJECT-PHOENIX.",
                    "impact": "Alle toekomstige ontwikkeling gebeurt binnen Project Phoenix."
                },
                {
                    "id": "ADR-0002",
                    "title": "BREWSTER ENGINEERING WIZARD wordt app-shell",
                    "status": "accepted",
                    "decision": "Brewster Engineering Wizard blijft de gebruikersinterface binnen apps/brewster_engineering_wizard.",
                    "impact": "Geen aparte parallelle ontwikkeling meer."
                },
                {
                    "id": "ADR-0003",
                    "title": "BIB integreert in PKB",
                    "status": "accepted",
                    "decision": "BIB wordt opgenomen in de Phoenix Knowledge Base.",
                    "impact": "Eén centrale kennislaag voor alle suites."
                }
            ]
        }

        self.path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False), encoding="utf-8")
        return decisions
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/decision_log/decision_log.py"

@'
from pathlib import Path
from datetime import datetime
import json


class PhoenixSourceEvidence:
    def __init__(self, root="phoenix_intelligence/source_evidence"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "source_evidence_registry.json"

    def bootstrap(self):
        data = {
            "source_evidence_version": "1.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "principle": "Alle belangrijke projectkennis moet herleidbaar zijn naar documenten, beslissingen, bronbestanden of projectoutputs.",
            "sources": []
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/source_evidence/source_evidence.py"

@'
from pathlib import Path
from datetime import datetime
import json

from project_phoenix.intelligence.pkb.knowledge_base import PhoenixKnowledgeBase
from project_phoenix.intelligence.bib.bib_manager import BrewsterIntelligenceBibliotheek
from project_phoenix.intelligence.knowledge_graph.knowledge_graph import PhoenixKnowledgeGraph
from project_phoenix.intelligence.decision_log.decision_log import PhoenixDecisionLog
from project_phoenix.intelligence.source_evidence.source_evidence import PhoenixSourceEvidence


class PhoenixIntelligenceOrchestrator:
    def __init__(self, output_dir="outputs/phoenix_intelligence"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def bootstrap(self):
        pkb = PhoenixKnowledgeBase().bootstrap()
        bib = BrewsterIntelligenceBibliotheek().bootstrap()
        graph = PhoenixKnowledgeGraph().bootstrap()
        decisions = PhoenixDecisionLog().bootstrap()
        evidence = PhoenixSourceEvidence().bootstrap()

        result = {
            "layer": "Phoenix Intelligence Layer",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "components": {
                "pkb": "installed",
                "bib": "integrated",
                "knowledge_graph": "installed",
                "decision_log": "installed",
                "source_evidence": "installed"
            },
            "counts": {
                "pkb_items": len(pkb.get("items", [])),
                "bib_domains": len(bib.get("domains", [])),
                "graph_nodes": len(graph.get("nodes", [])),
                "graph_edges": len(graph.get("edges", [])),
                "decisions": len(decisions.get("decisions", []))
            }
        }

        (self.output_dir / "phoenix_intelligence_v1_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        report = "# Phoenix Intelligence Layer v1.0\n\n"
        report += "PKB + BIB zijn geïntegreerd als centrale kennislaag.\n\n"
        report += "## Componenten\n"
        for key, value in result["components"].items():
            report += f"- {key}: {value}\n"

        (self.output_dir / "phoenix_intelligence_v1_report.md").write_text(report, encoding="utf-8")

        return result


if __name__ == "__main__":
    result = PhoenixIntelligenceOrchestrator().bootstrap()
    print("Phoenix Intelligence Layer v1.0 geïnstalleerd.")
    print(result)
'@ | Set-Content -Encoding UTF8 "project_phoenix/intelligence/orchestrator.py"

@'
# Phoenix Intelligence Layer v1.0

## Doel

Deze laag integreert de Phoenix Knowledge Base (PKB) en de Brewster Intelligence Bibliotheek (BIB).

## Architectuurbesluit

BIB wordt niet meer separaat onderhouden. BIB wordt de inhoudelijke kennislaag binnen PKB.

## Componenten

- PKB
- BIB
- Knowledge Graph
- Decision Log
- Source Evidence / STEE
- Standards Library
- Template Library
- Prompt Library
- Master Specification Library

## Relatie met BREWSTER ENGINEERING WIZARD

BREWSTER ENGINEERING WIZARD blijft de gebruikersapplicatie.  
Project Phoenix is het onderliggende platform.  
Phoenix Intelligence is de kennislaag waar alle suites op steunen.
'@ | Set-Content -Encoding UTF8 "docs/project_phoenix/intelligence/PHOENIX_INTELLIGENCE_LAYER_v1.md"

Write-Host "Stap 3 - Intelligence Layer bootstrap uitvoeren..." -ForegroundColor Yellow
python -m project_phoenix.intelligence.orchestrator

Write-Host "Stap 4 - Commit maken..." -ForegroundColor Yellow
git add project_phoenix phoenix_intelligence docs/project_phoenix/intelligence outputs/phoenix_intelligence PHOENIX_INTELLIGENCE_v1_pre_install_status.txt
git commit -m "feat: add phoenix intelligence layer v1 with pkb bib integration"

Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Phoenix Intelligence Layer v1.0 is geïnstalleerd." -ForegroundColor Green
Write-Host "Voer daarna uit: git push" -ForegroundColor Green