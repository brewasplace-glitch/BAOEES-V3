param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX - Phoenix Geometry Engine v1.0" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) { throw "Geen git repository gevonden." }

Write-Host "Stap 1 - Upstream branch herstellen naar origin/project-phoenix..." -ForegroundColor Yellow
git branch --unset-upstream 2>$null
git branch --set-upstream-to=origin/project-phoenix project-phoenix 2>$null

Write-Host "Stap 2 - Status veilig vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "PGE_v1_0_pre_build_status.txt"

$changes = git status --short
if ($changes) {
    git add -A
    git commit -m "chore: stabilize before phoenix geometry engine v1.0"
}

Write-Host "Stap 3 - PGE structuur aanmaken..." -ForegroundColor Yellow

$dirs = @(
    "project_phoenix/geometry",
    "project_phoenix/geometry/core",
    "project_phoenix/geometry/building",
    "project_phoenix/geometry/exporters",
    "project_phoenix/geometry/digital_twin",
    "project_phoenix/geometry/tests",
    "docs/project_phoenix/geometry",
    "outputs/geometry_engine_v1_0",
    "outputs/geometry_engine_v1_0/dxf",
    "outputs/geometry_engine_v1_0/digital_twin"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
"""
Phoenix Geometry Engine (PGE) v1.0

Shared geometry kernel for Project Phoenix.
"""
__version__ = "1.0.0"
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/__init__.py"

@'
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import math


@dataclass
class Point2D:
    x: float
    y: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class Line2D:
    start: Point2D
    end: Point2D
    layer: str = "0"

    def length(self) -> float:
        return round(math.sqrt((self.end.x - self.start.x) ** 2 + (self.end.y - self.start.y) ** 2), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "line2d",
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "layer": self.layer,
            "length": self.length()
        }


@dataclass
class Rectangle2D:
    origin: Point2D
    width: float
    depth: float
    layer: str = "0"
    name: str = ""

    def area(self) -> float:
        return round(self.width * self.depth, 4)

    def perimeter(self) -> float:
        return round(2 * (self.width + self.depth), 4)

    def corners(self) -> List[Point2D]:
        x = self.origin.x
        y = self.origin.y
        return [
            Point2D(x, y),
            Point2D(x + self.width, y),
            Point2D(x + self.width, y + self.depth),
            Point2D(x, y + self.depth)
        ]

    def edges(self) -> List[Line2D]:
        c = self.corners()
        return [
            Line2D(c[0], c[1], self.layer),
            Line2D(c[1], c[2], self.layer),
            Line2D(c[2], c[3], self.layer),
            Line2D(c[3], c[0], self.layer),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "rectangle2d",
            "name": self.name,
            "origin": self.origin.to_dict(),
            "width": self.width,
            "depth": self.depth,
            "area": self.area(),
            "perimeter": self.perimeter(),
            "layer": self.layer,
            "corners": [p.to_dict() for p in self.corners()]
        }
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/core/primitives_2d.py"

@'
from dataclasses import dataclass, asdict
from typing import Dict, Any
from project_phoenix.geometry.core.primitives_2d import Point2D, Rectangle2D


@dataclass
class SpaceGeometry:
    space_id: str
    name: str
    function: str
    floor: str
    rectangle: Rectangle2D

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "space_geometry",
            "space_id": self.space_id,
            "name": self.name,
            "function": self.function,
            "floor": self.floor,
            "geometry": self.rectangle.to_dict()
        }


@dataclass
class WallGeometry:
    wall_id: str
    floor: str
    start: Point2D
    end: Point2D
    thickness_m: float = 0.2
    height_m: float = 3.2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "wall_geometry",
            "wall_id": self.wall_id,
            "floor": self.floor,
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "thickness_m": self.thickness_m,
            "height_m": self.height_m
        }


@dataclass
class OpeningGeometry:
    opening_id: str
    floor: str
    opening_type: str
    x: float
    y: float
    width_m: float
    height_m: float
    sill_height_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/building/building_elements.py"

@'
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
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/building/architectural_geometry_builder.py"

@'
from pathlib import Path


class PhoenixDxfGeometryExporter:
    VERSION = "1.0.0"

    def __init__(self, output_dir="outputs/geometry_engine_v1_0/dxf"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_geometry_model(self, geometry_model, filename="pge_geometry_model_v1_0.dxf"):
        path = self.output_dir / filename
        lines = ["0", "SECTION", "2", "ENTITIES"]

        for wall in geometry_model.get("walls", []):
            start = wall["start"]
            end = wall["end"]
            layer = wall.get("floor", "walls")
            lines.extend([
                "0", "LINE",
                "8", layer,
                "10", str(start["x"]), "20", str(start["y"]), "30", "0",
                "11", str(end["x"]), "21", str(end["y"]), "31", "0"
            ])

        lines.extend(["0", "ENDSEC", "0", "EOF"])
        path.write_text("\n".join(lines), encoding="utf-8")

        return {
            "exporter": "PhoenixDxfGeometryExporter",
            "version": self.VERSION,
            "status": "ok",
            "path": str(path)
        }
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/exporters/dxf_geometry_exporter.py"

@'
from pathlib import Path
from datetime import datetime
import json


class PhoenixGeometryDigitalTwinExporter:
    VERSION = "1.0.0"

    def __init__(self, output_dir="outputs/geometry_engine_v1_0/digital_twin"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, geometry_model, filename="pge_geometry_digital_twin_v1_0.json"):
        payload = {
            "digital_twin_layer": "geometry",
            "version": self.VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "geometry_model": geometry_model,
            "source": {
                "engine": "Phoenix Geometry Engine",
                "version": self.VERSION
            }
        }

        path = self.output_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "exporter": "PhoenixGeometryDigitalTwinExporter",
            "version": self.VERSION,
            "status": "ok",
            "path": str(path)
        }
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/digital_twin/geometry_digital_twin_exporter.py"

@'
from pathlib import Path
from datetime import datetime
import json

from project_phoenix.geometry.building.architectural_geometry_builder import ArchitecturalGeometryBuilder
from project_phoenix.geometry.exporters.dxf_geometry_exporter import PhoenixDxfGeometryExporter
from project_phoenix.geometry.digital_twin.geometry_digital_twin_exporter import PhoenixGeometryDigitalTwinExporter


class PhoenixGeometryEngine:
    VERSION = "1.0.0"

    def run_from_floorplan(self, floorplan):
        geometry_model = ArchitecturalGeometryBuilder().build_from_floorplan(floorplan)
        dxf_export = PhoenixDxfGeometryExporter().export_geometry_model(geometry_model)
        dt_export = PhoenixGeometryDigitalTwinExporter().export(geometry_model)

        result = {
            "engine": "Phoenix Geometry Engine",
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "geometry_model": geometry_model,
            "exports": {
                "dxf": dxf_export,
                "digital_twin": dt_export
            },
            "status": "ok"
        }

        out = Path("outputs/geometry_engine_v1_0")
        out.mkdir(parents=True, exist_ok=True)
        (out / "pge_v1_0_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return result


def run_demo():
    floorplan = {
        "floors": {
            "begane grond": [
                {"space": "Entree", "function": "verkeersruimte", "x": 0, "y": 0, "width_m": 3, "length_m": 3.5},
                {"space": "Gebedsruimte heren", "function": "bijeenkomstfunctie", "x": 3, "y": 0, "width_m": 10, "length_m": 12},
                {"space": "Wasruimte", "function": "sanitair", "x": 13, "y": 0, "width_m": 3, "length_m": 4}
            ],
            "verdieping": [
                {"space": "Gebedsruimte dames", "function": "bijeenkomstfunctie", "x": 0, "y": 0, "width_m": 8, "length_m": 10},
                {"space": "Leslokaal", "function": "onderwijs", "x": 8, "y": 0, "width_m": 5, "length_m": 6}
            ]
        }
    }
    return PhoenixGeometryEngine().run_from_floorplan(floorplan)


if __name__ == "__main__":
    result = run_demo()
    print("Phoenix Geometry Engine v1.0 uitgevoerd.")
    print("Status:", result["status"])
    print("Spaces:", result["geometry_model"]["counts"]["spaces"])
    print("Walls:", result["geometry_model"]["counts"]["walls"])
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/geometry_engine.py"

@'
def test_rectangle_area():
    from project_phoenix.geometry.core.primitives_2d import Point2D, Rectangle2D
    rect = Rectangle2D(Point2D(0, 0), 4, 5)
    assert rect.area() == 20


def test_geometry_builder_counts():
    from project_phoenix.geometry.building.architectural_geometry_builder import ArchitecturalGeometryBuilder
    floorplan = {"floors": {"bg": [{"space": "A", "function": "test", "x": 0, "y": 0, "width_m": 2, "length_m": 3}]}}
    result = ArchitecturalGeometryBuilder().build_from_floorplan(floorplan)
    assert result["counts"]["spaces"] == 1
    assert result["counts"]["walls"] == 4
'@ | Set-Content -Encoding UTF8 "project_phoenix/geometry/tests/test_geometry_engine.py"

@'
# Phoenix Geometry Engine (PGE) v1.0

## Doel

De Phoenix Geometry Engine is de gedeelde geometriekern voor Project Phoenix.

## Functies v1.0

- Point2D
- Line2D
- Rectangle2D
- SpaceGeometry
- WallGeometry
- OpeningGeometry
- ArchitecturalGeometryBuilder
- DXF geometry exporter
- Digital Twin geometry exporter

## Waarom

De geometrische logica moet niet in iedere suite apart worden gebouwd.  
Architectural, Structural, Infrastructure, MEP en Digital Twin gebruiken dezelfde PGE-basis.

## Volgende release

PGE v1.1:
- 3D primitives
- Floor slabs
- Roof geometry
- Door/window openings in walls
- IFC object preparation
- FreeCAD payload
'@ | Set-Content -Encoding UTF8 "docs/project_phoenix/geometry/PHOENIX_GEOMETRY_ENGINE_v1_0.md"

Write-Host "Stap 4 - PGE demo uitvoeren..." -ForegroundColor Yellow
python -m project_phoenix.geometry.geometry_engine

Write-Host "Stap 5 - Commit maken..." -ForegroundColor Yellow
git add project_phoenix/geometry docs/project_phoenix/geometry outputs/geometry_engine_v1_0 PGE_v1_0_pre_build_status.txt
git commit -m "feat: add phoenix geometry engine v1.0"

Write-Host "Stap 6 - Upstream instellen en status tonen..." -ForegroundColor Yellow
git push --set-upstream origin project-phoenix
git status

Write-Host ""
Write-Host "KLAAR: Phoenix Geometry Engine v1.0 is gebouwd." -ForegroundColor Green