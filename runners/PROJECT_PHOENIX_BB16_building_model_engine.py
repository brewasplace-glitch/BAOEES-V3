from __future__ import annotations
import json, sys, tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from phoenix.building_model import BuildingModelEngine, ElementCategory
from phoenix.building_model.adapters import SciaEngineerAdapter, SketchUpAdapter

def main() -> int:
    engine = BuildingModelEngine()
    model = engine.create_model("PHX-BB16-SELFTEST", "Building Model Engine Self-Test",
                                metadata={"build_block": "BB16", "version": "1.0.2"})
    engine.add_level(model, level_id="LVL-00", name="Ground floor",
                     elevation_m=0.0, height_m=3.0)
    engine.add_space(model, space_id="SPC-001", name="Test space",
                     level_id="LVL-00", area_m2=20.0)
    engine.add_element(
        model, element_id="ELM-SLAB-001", name="Ground floor slab",
        category=ElementCategory.SLAB, level_id="LVL-00",
        geometry={"length_m": 5.0, "width_m": 4.0, "thickness_m": 0.2},
        material={"name": "concrete"})
    errors = [i.to_dict() for i in engine.validate(model) if i.severity == "error"]
    if errors:
        print(json.dumps({"status": "FAILED", "errors": errors}, indent=2))
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = engine.export_json(model, Path(tmp) / "bb16_selftest_model.json")
        result = {
            "status": "PASSED", "build_block": "BB16", "version": "1.0.2",
            "fingerprint_sha256": engine.fingerprint(model),
            "snapshot_created": snapshot.is_file(),
            "sketchup": SketchUpAdapter().detect().to_dict(),
            "scia": SciaEngineerAdapter().detect().to_dict(),
        }
        print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
