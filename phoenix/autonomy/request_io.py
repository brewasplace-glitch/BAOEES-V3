from __future__ import annotations
from pathlib import Path
import json
from typing import Any

def load_json_request(path: Path) -> dict[str, Any]:
    """Read UTF-8 JSON with or without a BOM."""
    data=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict):
        raise ValueError("LOW-risk request root must be a JSON object")
    return data
