from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class ArchitecturalSpace:
    name: str
    function: str
    floor: str
    area_m2: float = 0.0
    width_m: float = 0.0
    length_m: float = 0.0
    notes: str = ""


@dataclass
class ArchitecturalProject:
    project_id: str
    project_name: str
    location: str
    building_type: str
    client: str = ""
    extension_area_m2: float = 0.0
    gross_floor_area_m2: float = 0.0
    spaces: List[ArchitecturalSpace] = None
    assumptions: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        if data["spaces"] is None:
            data["spaces"] = []
        if data["assumptions"] is None:
            data["assumptions"] = []
        return data
