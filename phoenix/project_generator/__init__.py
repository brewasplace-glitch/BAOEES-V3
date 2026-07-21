"""Phoenix Project Generator (PPG) public API."""

from .generator import (
    GenerationError,
    ProjectBrief,
    ProjectVariant,
    VariantWeights,
    generate_project_variants,
    rank_project_variants,
    select_project_variant,
    variant_presentation_queue,
)

__all__ = [
    "GenerationError",
    "ProjectBrief",
    "ProjectVariant",
    "VariantWeights",
    "generate_project_variants",
    "rank_project_variants",
    "select_project_variant",
    "variant_presentation_queue",
]
