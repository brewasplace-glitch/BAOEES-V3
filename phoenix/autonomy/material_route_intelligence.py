from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

VERSION = "1.0.0"


@dataclass(frozen=True)
class MaterialRouteDecision:
    requirement_id: str
    material_family: str
    primary_route: str
    international_fallback_allowed: bool
    search_priority: List[str]
    rationale: str
    automatic_ordering: bool = False
    professional_review_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def decide_material_route(
    requirement_id: str,
    material_family: str,
    selection_status: Optional[str] = None,
    engineering_qualification_status: Optional[str] = None,
) -> MaterialRouteDecision:
    family = _norm(material_family)
    status = _norm(selection_status)
    qualification = _norm(engineering_qualification_status)

    if family == "structural_concrete":
        return MaterialRouteDecision(
            requirement_id=requirement_id,
            material_family=material_family,
            primary_route="LOCAL_READY_MIX_TECHNICAL_QUALIFICATION",
            international_fallback_allowed=False,
            search_priority=["SURINAME_LOCAL_TECHNICAL_EVIDENCE"],
            rationale=(
                "Normal structural ready-mix concrete is a local production/delivery product. "
                "Phoenix must qualify the local concrete class/mix and supplier evidence instead of "
                "treating ordinary ready-mix as an international import commodity."
            ),
        )

    if family == "masonry_unit":
        local_known = "local_availability_confirmed" in status or "technical_product_evidence_required" in qualification
        return MaterialRouteDecision(
            requirement_id=requirement_id,
            material_family=material_family,
            primary_route=(
                "LOCAL_TECHNICAL_QUALIFICATION_THEN_IMPORT_FALLBACK"
                if local_known
                else "LOCAL_DISCOVERY_THEN_IMPORT_FALLBACK"
            ),
            international_fallback_allowed=True,
            search_priority=["SURINAME_LOCAL_TECHNICAL_EVIDENCE", "NETHERLANDS", "BELGIUM", "EU27", "GLOBAL"],
            rationale=(
                "Masonry remains local-first. International sourcing is a fallback only when a local product cannot "
                "be technically qualified for the project."
            ),
        )

    if family == "structural_timber":
        return MaterialRouteDecision(
            requirement_id=requirement_id,
            material_family=material_family,
            primary_route="LOCAL_FIRST_THEN_CERTIFIED_IMPORT",
            international_fallback_allowed=True,
            search_priority=["SURINAME_LOCAL", "NETHERLANDS", "BELGIUM", "EU27", "GLOBAL"],
            rationale=(
                "Structural timber may be imported when no local technically qualified supply is demonstrated. "
                "European evidence is prioritized, while final procurement selection remains based on technical "
                "validity and complete landed cost."
            ),
        )

    if family == "reinforcement_steel":
        return MaterialRouteDecision(
            requirement_id=requirement_id,
            material_family=material_family,
            primary_route="LOCAL_FIRST_THEN_CERTIFIED_IMPORT",
            international_fallback_allowed=True,
            search_priority=["SURINAME_LOCAL", "NETHERLANDS", "BELGIUM", "EU27", "GLOBAL"],
            rationale=(
                "Reinforcement steel may be imported when local supply is unavailable or cannot be technically "
                "qualified. Technical grade/standard/certificate evidence is mandatory before structural use."
            ),
        )

    return MaterialRouteDecision(
        requirement_id=requirement_id,
        material_family=material_family,
        primary_route="LOCAL_FIRST_THEN_CONTROLLED_GLOBAL_FALLBACK",
        international_fallback_allowed=True,
        search_priority=["SURINAME_LOCAL", "NETHERLANDS", "BELGIUM", "EU27", "GLOBAL"],
        rationale="Conservative default: local-first, then controlled international fallback with engineering evidence.",
    )


def decide_routes(selections: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    decisions: List[Dict[str, Any]] = []
    for item in selections:
        if not isinstance(item, dict):
            continue
        decisions.append(
            decide_material_route(
                requirement_id=str(item.get("requirement_id") or "UNKNOWN"),
                material_family=str(item.get("material_family") or "unknown"),
                selection_status=item.get("selection_status"),
                engineering_qualification_status=item.get("engineering_qualification_status"),
            ).to_dict()
        )
    return decisions
