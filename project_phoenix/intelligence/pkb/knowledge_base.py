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
                title="BIB wordt geÃ¯ntegreerd in PKB",
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
