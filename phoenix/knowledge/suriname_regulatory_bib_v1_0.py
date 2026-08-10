from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict, List, Optional
ENGINE_NAME="PHOENIX SURINAME REGULATORY ENGINEERING KNOWLEDGE BIB"
ENGINE_VERSION="v1.0.0"
SOURCE_REGISTRY_REL=Path("outputs/bib/index/suriname_regulatory_source_registry_v1_0.json")
RULE_REGISTRY_REL=Path("configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json")
POLICY_REL=Path("configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json")
KNOWLEDGE_REL=Path("outputs/bib/knowledge/jurisdictions/suriname/suriname_regulatory_knowledge_v1_0.json")
def repository_root()->Path:
    v=os.environ.get("PHOENIX_REPO_ROOT")
    return Path(v).resolve() if v else Path(__file__).resolve().parents[2]
def _read(p:Path)->Dict[str,Any]:
    d=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(d,dict): raise ValueError(f"Expected JSON object: {p}")
    return d
def load_source_registry(root:Optional[Path]=None): return _read((root or repository_root()).resolve()/SOURCE_REGISTRY_REL)
def load_rule_registry(root:Optional[Path]=None): return _read((root or repository_root()).resolve()/RULE_REGISTRY_REL)
def load_policy(root:Optional[Path]=None): return _read((root or repository_root()).resolve()/POLICY_REL)
def load_knowledge(root:Optional[Path]=None): return _read((root or repository_root()).resolve()/KNOWLEDGE_REL)
def source_by_id(source_id:str, root:Optional[Path]=None):
    for s in load_source_registry(root).get("sources",[]):
        if s.get("source_id")==source_id: return s
    raise KeyError(source_id)
def source_priority(s): return {"PRIMARY_LEGISLATION_USER_PROVIDED":300,"PRIMARY_REGULATION_USER_PROVIDED":250,"UNVERIFIED_SECONDARY_BACKGROUND":10}.get(str(s.get("source_class")),0)
def is_paramaribo_location(location:str)->bool:
    v=(location or "").strip().lower(); return "paramaribo" in v and ("suriname" in v or v=="paramaribo")
def applicable_sources(location:str, root:Optional[Path]=None)->List[Dict[str,Any]]:
    if not is_paramaribo_location(location): return []
    return sorted(load_source_registry(root).get("sources",[]),key=source_priority,reverse=True)
def rules(*,category:Optional[str]=None,occupancy:Optional[str]=None,root:Optional[Path]=None):
    rows=list(load_rule_registry(root).get("rules",[]))
    if category: rows=[r for r in rows if str(r.get("category","")).upper()==category.upper()]
    if occupancy: rows=[r for r in rows if r.get("occupancy")==occupancy]
    return rows
def rule_by_id(rule_id:str,root:Optional[Path]=None):
    for r in rules(root=root):
        if r.get("rule_id")==rule_id: return r
    raise KeyError(rule_id)
def automatic_numeric_use_allowed(source_id:str,root:Optional[Path]=None)->bool: return source_by_id(source_id,root).get("automatic_numeric_use") is True
def build_project_regulatory_context(*,location:str,occupancy:Optional[str]=None,root:Optional[Path]=None):
    base=(root or repository_root()).resolve(); src=applicable_sources(location,base); rr=rules(root=base) if src else []
    if occupancy: rr=[r for r in rr if r.get("occupancy") in (None,occupancy)]
    return {"schema_version":"phoenix.suriname.project-regulatory-context/1.0","engine":ENGINE_NAME,"engine_version":ENGINE_VERSION,"location":location,"jurisdiction_match":bool(src),"source_ids":[s.get("source_id") for s in src],"rule_ids":[r.get("rule_id") for r in rr],"policy":load_policy(base),"safety":{"background_numeric_auto_use":False,"automatic_foreign_standard_legal_adoption_claim":False,"automatic_local_foreign_conflict_resolution":False,"current_2026_legal_status_assumed":False,"professional_review_required":True,"production_release":"LOCKED"}}
def r9_4_local_source_bridge(root:Optional[Path]=None): return dict(load_rule_registry(root).get("r9_4_local_source_bridge",{}))
