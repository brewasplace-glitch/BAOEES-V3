from __future__ import annotations
from pathlib import Path
import json

DEFAULT_CATALOG = {
    "schema":"PHOENIX_OPEN_SOURCE_SCOUT_CATALOG_V1",
    "researched_on":"2026-09-14",
    "candidates":[
        {
            "id":"langgraph",
            "capability":"orchestration",
            "role":"primary",
            "name":"LangGraph",
            "license":"MIT",
            "url":"https://github.com/langchain-ai/langgraph",
            "fit":["stateful workflows","durable execution","human-in-the-loop"],
            "integration":"adapter",
        },
        {
            "id":"prefect",
            "capability":"orchestration",
            "role":"fallback",
            "name":"Prefect",
            "license":"Apache-2.0",
            "url":"https://github.com/PrefectHQ/prefect",
            "fit":["workflow orchestration","retries","scheduling","event automation"],
            "integration":"adapter",
        },
        {
            "id":"gitpython",
            "capability":"git",
            "role":"primary",
            "name":"GitPython",
            "license":"BSD-3-Clause",
            "url":"https://github.com/gitpython-developers/GitPython",
            "fit":["repository API","diff/status/refs"],
            "integration":"optional-adapter",
        },
        {
            "id":"dulwich",
            "capability":"git",
            "role":"fallback",
            "name":"Dulwich",
            "license":"Apache-2.0 OR GPL-2.0-or-later",
            "url":"https://github.com/jelmer/dulwich",
            "fit":["pure Python Git implementation","repository operations"],
            "integration":"optional-adapter",
        },
    ]
}

class OpenSourceScout:
    def __init__(self, catalog=None):
        self.catalog=catalog or DEFAULT_CATALOG

    @classmethod
    def from_json(cls,path:Path):
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def candidates_for(self, capability: str):
        return tuple(
            c for c in self.catalog["candidates"]
            if c["capability"].lower()==capability.lower()
        )

    def select(self, capability: str):
        items=list(self.candidates_for(capability))
        primary=next((c for c in items if c["role"]=="primary"),None)
        fallback=next((c for c in items if c["role"]=="fallback"),None)
        return {"capability":capability,"primary":primary,"fallback":fallback}

    def save(self,path:Path):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.catalog,indent=2,ensure_ascii=False),encoding="utf-8")
