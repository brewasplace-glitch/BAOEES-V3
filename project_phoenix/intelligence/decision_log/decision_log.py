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
                    "impact": "EÃ©n centrale kennislaag voor alle suites."
                }
            ]
        }

        self.path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False), encoding="utf-8")
        return decisions
