"""Phoenix Project Generator v1.0.

Generates exactly ten traceable concept variants from one project instruction
and a location reference. The implementation is deterministic and
standard-neutral. It creates concept metadata and scoring evidence; it does not
claim to produce permit-ready drawings or engineering calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable


class GenerationError(ValueError):
    """Raised when a PPG request cannot be generated safely."""


@dataclass(frozen=True)
class VariantWeights:
    cost: float = 0.20
    permit_probability: float = 0.20
    sustainability: float = 0.20
    spatial_quality: float = 0.20
    constructability: float = 0.20

    def validate(self) -> None:
        values = (
            self.cost,
            self.permit_probability,
            self.sustainability,
            self.spatial_quality,
            self.constructability,
        )
        if any(value < 0.0 for value in values):
            raise GenerationError("Variant weights cannot be negative.")
        if abs(sum(values) - 1.0) > 1e-9:
            raise GenerationError("Variant weights must sum to 1.0.")


@dataclass(frozen=True)
class ProjectBrief:
    project_id: str
    instruction: str
    location_reference: str
    gross_floor_area_m2: float | None = None
    target_units: int | None = None
    maximum_floors: int | None = None
    parking_strategy: str = "site_specific"
    sustainability_target: str = "balanced"
    constraints: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.project_id.strip():
            raise GenerationError("project_id is required.")
        if not self.instruction.strip():
            raise GenerationError("instruction is required.")
        if not self.location_reference.strip():
            raise GenerationError("location_reference is required.")
        if self.gross_floor_area_m2 is not None and self.gross_floor_area_m2 <= 0:
            raise GenerationError("gross_floor_area_m2 must be positive.")
        if self.target_units is not None and self.target_units <= 0:
            raise GenerationError("target_units must be positive.")
        if self.maximum_floors is not None and self.maximum_floors <= 0:
            raise GenerationError("maximum_floors must be positive.")


@dataclass(frozen=True)
class ProjectVariant:
    variant_id: str
    name: str
    archetype: str
    massing: str
    circulation: str
    structural_concept: str
    foundation_strategy: str
    parking_strategy: str
    sustainability_strategy: str
    scores: dict[str, float]
    weighted_score: float
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    fingerprint: str = field(default="")


_ARCHETYPES = (
    ("Courtyard", "gesloten bouwblok met collectieve binnentuin", "centrale kernen"),
    ("Gallery", "langgerekt volume met galerijontsluiting", "galerijen en eindkernen"),
    ("Point Towers", "meerdere compacte woontorens", "centrale kernen per toren"),
    ("Terraced", "getrapt volume met dakterrassen", "meerdere verticale kernen"),
    ("Perimeter", "randbebouwing met open hoek", "kernen langs de perimeter"),
    ("Atrium", "compact volume rond overdekt atrium", "atriumgebonden kernen"),
    ("Slab", "parallelle woonblokken", "galerij- of corridorontsluiting"),
    ("Cluster", "geschakelde woonclusters", "gedeelde clusterkernen"),
    ("Hybrid Podium", "stedelijk plintgebouw met woontorens", "podium- en torenkernen"),
    ("Linear Park", "lineair woongebouw langs landschappelijke as", "meervoudige kernen"),
)


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _seed(brief: ProjectBrief, index: int) -> int:
    raw = f"{brief.project_id}|{brief.instruction}|{brief.location_reference}|{index}"
    return int(sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _score_set(seed: int, index: int) -> dict[str, float]:
    base = ((seed % 1000) / 1000.0)
    return {
        "cost": _bounded(0.55 + ((index * 7) % 17) / 50.0 - base / 10.0),
        "permit_probability": _bounded(0.50 + ((index * 11) % 19) / 50.0),
        "sustainability": _bounded(0.52 + ((index * 13) % 21) / 50.0),
        "spatial_quality": _bounded(0.54 + ((index * 5) % 23) / 50.0),
        "constructability": _bounded(0.58 + ((index * 3) % 17) / 50.0),
    }


def _weighted(scores: dict[str, float], weights: VariantWeights) -> float:
    return round(
        scores["cost"] * weights.cost
        + scores["permit_probability"] * weights.permit_probability
        + scores["sustainability"] * weights.sustainability
        + scores["spatial_quality"] * weights.spatial_quality
        + scores["constructability"] * weights.constructability,
        6,
    )


def generate_project_variants(
    brief: ProjectBrief,
    weights: VariantWeights | None = None,
) -> tuple[ProjectVariant, ...]:
    brief.validate()
    weights = weights or VariantWeights()
    weights.validate()

    variants: list[ProjectVariant] = []
    for index, (archetype, massing, circulation) in enumerate(_ARCHETYPES, start=1):
        seed = _seed(brief, index)
        scores = _score_set(seed, index)
        structural = (
            "betonnen stabiliteitskernen met kolom-vloersysteem"
            if index % 2
            else "hybride staal-beton draagstructuur"
        )
        foundation = (
            "voorlopig paalfunderingsscenario, te bevestigen door geotechniek"
            if index in {3, 6, 9}
            else "voorlopig stroken/poeren-scenario, te bevestigen door geotechniek"
        )
        parking = (
            brief.parking_strategy
            if brief.parking_strategy != "site_specific"
            else ("halfverdiepte parkeervoorziening" if index % 3 == 0 else "maaiveld en mobiliteitshub")
        )
        sustainability = (
            "passief ontwerp, PV, warmtepomp, waterberging en materiaaloptimalisatie"
        )
        assumptions = tuple(brief.assumptions) + (
            "locatiegegevens moeten door GIS Engine worden gevalideerd",
            "bodemopbouw moet door Geotechnical Engine worden vastgesteld",
        )
        risks = (
            "vergunningkans is voorlopig en vereist lokale regelgeving",
            "fundering is conceptueel totdat geotechnisch bewijs beschikbaar is",
        )
        evidence = (
            f"deterministic-seed:{seed}",
            f"archetype-library-index:{index}",
            "PPG-v1.0-standard-neutral",
        )
        fingerprint = sha256(
            f"{brief.project_id}|V{index:02d}|{archetype}|{scores}".encode("utf-8")
        ).hexdigest()
        variants.append(
            ProjectVariant(
                variant_id=f"V{index:02d}",
                name=f"Variant {index}: {archetype}",
                archetype=archetype,
                massing=massing,
                circulation=circulation,
                structural_concept=structural,
                foundation_strategy=foundation,
                parking_strategy=parking,
                sustainability_strategy=sustainability,
                scores=scores,
                weighted_score=_weighted(scores, weights),
                assumptions=assumptions,
                risks=risks,
                evidence=evidence,
                fingerprint=fingerprint,
            )
        )
    return tuple(variants)


def rank_project_variants(
    variants: Iterable[ProjectVariant],
) -> tuple[ProjectVariant, ...]:
    result = tuple(variants)
    if len(result) != 10:
        raise GenerationError("PPG requires exactly ten variants.")
    if len({variant.variant_id for variant in result}) != 10:
        raise GenerationError("Variant IDs must be unique.")
    return tuple(sorted(result, key=lambda item: (-item.weighted_score, item.variant_id)))


def select_project_variant(
    variants: Iterable[ProjectVariant],
    selected_variant_id: str | None = None,
) -> ProjectVariant:
    ranked = rank_project_variants(variants)
    if selected_variant_id is None:
        return ranked[0]
    for variant in ranked:
        if variant.variant_id == selected_variant_id:
            return variant
    raise GenerationError("selected_variant_id does not exist.")


def variant_presentation_queue(
    variants: Iterable[ProjectVariant],
) -> tuple[dict[str, object], ...]:
    ranked = rank_project_variants(variants)
    return tuple(
        {
            "position": position,
            "variant_id": variant.variant_id,
            "name": variant.name,
            "archetype": variant.archetype,
            "massing": variant.massing,
            "circulation": variant.circulation,
            "weighted_score": variant.weighted_score,
            "scores": dict(variant.scores),
            "risks": list(variant.risks),
            "assumptions": list(variant.assumptions),
            "fingerprint": variant.fingerprint,
        }
        for position, variant in enumerate(ranked, start=1)
    )
