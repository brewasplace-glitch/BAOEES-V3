from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json
REGISTRY_REL = Path("configs/phoenix/jurisdictions/netherlands/nl_structural_norm_regulatory_registry_v1_0.json")
@dataclass(frozen=True)
class RegulatoryBasisAssessment:
    status: str
    mode: str
    sources: List[Dict[str, Any]]
    blockers: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
def load_nl_registry(repository: Path) -> Dict[str, Any]:
    return json.loads((repository / REGISTRY_REL).read_text(encoding="utf-8"))
def assess_nl_structural_basis(repository: Path, mode: str = "PROFESSIONAL_REVIEW_PACKAGE") -> RegulatoryBasisAssessment:
    registry = load_nl_registry(repository); sources=list(registry.get("sources") or []); blockers=[]; warnings=[]
    if mode not in {"WORKFLOW_VALIDATION","PROFESSIONAL_REVIEW_PACKAGE","REVIEWED_FINAL_RELEASE_RUN"}:
        blockers.append({"reason":"UNKNOWN_STRUCTURAL_RELEASE_MODE","mode":mode}); return RegulatoryBasisAssessment("BLOCKED",mode,sources,blockers,warnings)
    if mode == "REVIEWED_FINAL_RELEASE_RUN":
        blockers.append({"reason":"PROFESSIONAL_REVIEW_INPUT_REQUIRED","message":"Final release run requires returned professional review evidence and a reviewed controlled baseline."})
    for src in sources:
        if src.get("technical_status") == "DRAFT": warnings.append({"reason":"DRAFT_STANDARD_REFERENCE_ONLY","source_id":src.get("source_id"),"formal_project_code_basis":False})
    wind_2026=next((s for s in sources if s.get("source_id")=="PHX-NL-EC1-WIND-2026"),None)
    if wind_2026 and "NOT_YET_PROVEN" in str(wind_2026.get("national_annex_status")):
        warnings.append({"reason":"SECOND_GENERATION_NL_WIND_NATIONAL_ANNEX_PENDING","message":"Use first-generation regulatory candidate only when current Dutch regulation applicability is explicitly verified."})
    status="PASSED_FOR_REVIEW_PACKAGE" if mode != "REVIEWED_FINAL_RELEASE_RUN" and not blockers else "BLOCKED"
    return RegulatoryBasisAssessment(status,mode,sources,blockers,warnings)
def build_review_candidate_action_basis() -> Dict[str, Any]:
    return {"basis":"NL_NEN_BIB_PROFESSIONAL_REVIEW_CANDIDATE","release_class":"PROFESSIONAL_REVIEW_PACKAGE_ONLY","unit_system":{"length":"m","force":"kN","moment":"kNm","stress":"kPa","mass":"kg"},"actions":[{"id":"ACT-G-SW","case_id":"LC-G","case_name":"Permanent self weight","category":"permanent","kind":"self_weight","direction":"GRAVITY","factor":1.0,"target":{"all_elements":True}},{"id":"ACT-Q-C-REVIEW","case_id":"LC-Q-C","case_name":"Category C imposed floor action - review candidate","category":"variable","kind":"area","direction":"GLOBAL_Z","magnitude":-5.0,"target":{"element_types":["slab_panel"]},"project_mapping_state":"C_SUBCATEGORY_REVIEW_REQUIRED"}],"combinations":[{"id":"COMB-SLS-CHAR-C-REVIEW","name":"SLS characteristic - review candidate","limit_state":"SLS","terms":[{"case_id":"LC-G","coefficient":1.0},{"case_id":"LC-Q-C","coefficient":1.0}]},{"id":"COMB-SLS-FREQ-C-REVIEW","name":"SLS frequent - review candidate","limit_state":"SLS","terms":[{"case_id":"LC-G","coefficient":1.0},{"case_id":"LC-Q-C","coefficient":0.7}]},{"id":"COMB-SLS-QP-C-REVIEW","name":"SLS quasi-permanent - review candidate","limit_state":"SLS","terms":[{"case_id":"LC-G","coefficient":1.0},{"case_id":"LC-Q-C","coefficient":0.6}]}],"explicit_unresolved_items":["CURRENT_DUTCH_REGULATORY_REFERENCE_VERIFICATION","WIND_PROJECT_MAGNITUDE_AND_NATIONAL_PARAMETERS","SNOW_ROOF_SHAPE_FACTOR_AND_PROJECT_GEOMETRY","ULS_PARTIAL_FACTORS_AND_PROJECT_COMBINATION_MAPPING","EXACT_CATEGORY_C_SUBCATEGORY"],"formal_release":False,"for_construction":False,"professional_review_required":True}