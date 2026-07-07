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
