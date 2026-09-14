from __future__ import annotations
from pathlib import Path
import json
from .models import LearningEvent, as_jsonable

class LearningStore:
    def __init__(self,path:Path):
        self.path=Path(path)

    def append(self,event:LearningEvent):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8",newline="\n") as f:
            f.write(json.dumps(as_jsonable(event),ensure_ascii=False,sort_keys=True)+"\n")

    def read_all(self):
        if not self.path.exists():
            return []
        result=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                result.append(json.loads(line))
        return result
