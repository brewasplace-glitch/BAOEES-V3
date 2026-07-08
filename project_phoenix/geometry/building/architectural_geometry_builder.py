from typing import Dict, Any, List
from project_phoenix.geometry.core.primitives_2d import Point2D, Rectangle2D
from project_phoenix.geometry.building.building_elements import SpaceGeometry, WallGeometry


class ArchitecturalGeometryBuilder:
    VERSION = "1.0.0"

    def build_from_floorplan(self, floorplan: Dict[str, Any]) -> Dict[str, Any]:
        spaces: List[SpaceGeometry] = []
        walls: List[WallGeometry] = []

        counter = 1
        wall_counter = 1

        for floor, rooms in floorplan.get("floors", {}).items():
            for room in rooms:
                rect = Rectangle2D(
                    origin=Point2D(float(room.get("x", 0.0)), float(room.get("y", 0.0))),
                    width=float(room.get("width_m", 0.0)),
                    depth=float(room.get("length_m", 0.0)),
                    layer=f"{floor}_spaces",
                    name=room.get("space", "")
                )

                space = SpaceGeometry(
                    space_id=f"space_{counter:04d}",
                    name=room.get("space", ""),
                    function=room.get("function", ""),
                    floor=floor,
                    rectangle=rect
                )
                spaces.append(space)
                counter += 1

                edges = rect.edges()
                for edge in edges:
                    walls.append(
                        WallGeometry(
                            wall_id=f"wall_{wall_counter:04d}",
                            floor=floor,
                            start=edge.start,
                            end=edge.end
                        )
                    )
                    wall_counter += 1

        return {
            "geometry_model_version": self.VERSION,
            "spaces": [s.to_dict() for s in spaces],
            "walls": [w.to_dict() for w in walls],
            "counts": {
                "spaces": len(spaces),
                "walls": len(walls)
            }
        }
