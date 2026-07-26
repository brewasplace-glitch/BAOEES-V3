from __future__ import annotations
import json, re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")
SHA = re.compile(r"^[0-9a-fA-F]{64}$")

@dataclass(frozen=True)
class Artifact:
    path: str
    policy: str
    required: bool = True
    sha256: str | None = None

@dataclass(frozen=True)
class Gate:
    id: str
    command: tuple[str,...]
    allowed_exit_codes: tuple[int,...] = (0,)

@dataclass(frozen=True)
class ReleaseManifest:
    id: str
    name: str
    version: str
    branch: str
    commit_message: str
    artifacts: tuple[Artifact,...]
    gates: tuple[Gate,...]

    def to_dict(self):
        return {
            "id":self.id,"name":self.name,"version":self.version,
            "branch":self.branch,"commit_message":self.commit_message,
            "artifacts":[a.__dict__ for a in self.artifacts],
            "gates":[{"id":g.id,"command":list(g.command),
                      "allowed_exit_codes":list(g.allowed_exit_codes)} for g in self.gates],
        }

class ReleaseManifestLoader:
    def load_file(self,path):
        return self.load_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def load_dict(self,d):
        for key in ("id","name","version","branch","commit_message"):
            if not isinstance(d.get(key),str) or not d[key].strip():
                raise ValueError(f"Missing field: {key}")
        if not ID.fullmatch(d["id"]): raise ValueError("Invalid release id.")
        raw=d.get("artifacts")
        if not isinstance(raw,list) or not raw: raise ValueError("Artifacts required.")
        artifacts=[]
        for a in raw:
            path=a.get("path","").replace("\\","/")
            pure=PurePosixPath(path)
            if not path or pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"Unsafe artifact path: {path}")
            if a.get("policy") not in ("track","ignore","clean"):
                raise ValueError("Invalid artifact policy.")
            if a.get("sha256") and not SHA.fullmatch(a["sha256"]):
                raise ValueError("Invalid artifact SHA-256.")
            artifacts.append(Artifact(path,a["policy"],bool(a.get("required",True)),a.get("sha256")))
        paths=[a.path for a in artifacts]
        if len(paths)!=len(set(paths)): raise ValueError("Duplicate artifact paths.")
        gates=[]
        for g in d.get("gates",[]):
            if not ID.fullmatch(g.get("id","")): raise ValueError("Invalid gate id.")
            cmd=g.get("command")
            if not isinstance(cmd,list) or not cmd or not all(isinstance(x,str) and x for x in cmd):
                raise ValueError("Invalid gate command.")
            allowed=g.get("allowed_exit_codes",[0])
            if not isinstance(allowed,list) or not all(isinstance(x,int) for x in allowed):
                raise ValueError("Invalid gate exit codes.")
            gates.append(Gate(g["id"],tuple(cmd),tuple(allowed)))
        if len({g.id for g in gates})!=len(gates): raise ValueError("Duplicate gate ids.")
        return ReleaseManifest(d["id"],d["name"],d["version"],d["branch"],
                               d["commit_message"],tuple(artifacts),tuple(gates))
