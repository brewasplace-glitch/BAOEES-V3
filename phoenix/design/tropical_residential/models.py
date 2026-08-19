from dataclasses import dataclass, asdict
from typing import Any, Dict, List

@dataclass
class Variant:
    variant_id: str
    strategy: str
    floor_area_m2: float
    footprint_m2: float
    storeys: int
    bedrooms: int
    bathrooms: float
    width_m: float
    depth_m: float
    orientation_deg: float
    ceiling_height_m: float
    veranda_depth_m: float
    roof_pitch_deg: float
    eave_overhang_m: float
    raised_floor_m: float
    features: List[str]
    scores: Dict[str, float]
    assumptions: List[str]
    release_status: str = "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
