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
