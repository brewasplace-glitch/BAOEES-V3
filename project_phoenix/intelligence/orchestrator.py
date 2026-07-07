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
        report += "PKB + BIB zijn geÃ¯ntegreerd als centrale kennislaag.\n\n"
        report += "## Componenten\n"
        for key, value in result["components"].items():
            report += f"- {key}: {value}\n"

        (self.output_dir / "phoenix_intelligence_v1_report.md").write_text(report, encoding="utf-8")

        return result


if __name__ == "__main__":
    result = PhoenixIntelligenceOrchestrator().bootstrap()
    print("Phoenix Intelligence Layer v1.0 geÃ¯nstalleerd.")
    print(result)
