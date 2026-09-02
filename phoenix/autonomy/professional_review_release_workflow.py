from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import hashlib, json
REQUIRED_REVIEW_FIELDS=("reviewer_identity_or_organization","review_document_reference","review_document_version","review_date","review_comments_or_markups","accepted_or_corrected_design_inputs","source_artifact_hashes")
@dataclass(frozen=True)
class ReviewGateResult:
    status: str
    blockers: List[Dict[str, Any]]
    controlled_baseline: Dict[str, Any] | None
def validate_review_return(payload: Dict[str, Any]) -> ReviewGateResult:
    blockers=[]
    for field in REQUIRED_REVIEW_FIELDS:
        value=payload.get(field)
        if value is None or value=="" or value==[] or value=={}: blockers.append({"reason":"REVIEW_EVIDENCE_FIELD_REQUIRED","field":field})
    if blockers: return ReviewGateResult("BLOCKED",blockers,None)
    canonical=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"); digest=hashlib.sha256(canonical).hexdigest()
    baseline={"schema_version":"phoenix.reviewed-project-baseline/1.0","baseline_class":"PROFESSIONALLY_REVIEWED_INPUT_BASELINE","review_return_sha256":digest,"professional_review_input_accepted":True,"automatic_professional_approval":False,"formal_release":"LOCKED_PENDING_FINAL_QAQC_AND_EXPLICIT_APPROVAL","review_evidence":payload}
    return ReviewGateResult("PASSED",[],baseline)
def write_reviewed_baseline(output_path: Path, baseline: Dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True,exist_ok=True); output_path.write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")