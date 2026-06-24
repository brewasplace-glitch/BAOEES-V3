from datetime import datetime
from pathlib import Path


class ProjectDxfWriterEngine:

    def __init__(self):
        self.dxf_writer_result = {}

    def write_project_dxfs(
        self,
        project_result=None,
        storage_result=None,
        drawing_result=None,
        cad_result=None,
        geo_result=None,
        structural_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        cad_dir = Path(
            folder_structure.get(
                "cad",
                project_output_dir / "03_cad"
            )
        )

        cad_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        dxf_files = {
            "situatie": cad_dir / f"{project_id}_situatie.dxf",
            "plattegrond": cad_dir / f"{project_id}_plattegrond.dxf",
            "doorsnede": cad_dir / f"{project_id}_doorsnede.dxf"
        }

        written_files = []

        written_files.append(
            self.write_dxf_file(
                file_path=dxf_files["situatie"],
                title=f"{project_name} - Situatietekening",
                drawing_type="situatie",
                project_result=project_result
            )
        )

        written_files.append(
            self.write_dxf_file(
                file_path=dxf_files["plattegrond"],
                title=f"{project_name} - Plattegrond",
                drawing_type="plattegrond",
                project_result=project_result
            )
        )

        written_files.append(
            self.write_dxf_file(
                file_path=dxf_files["doorsnede"],
                title=f"{project_name} - Doorsnede",
                drawing_type="doorsnede",
                project_result=project_result
            )
        )

        self.dxf_writer_result = {
            "engine": "ProjectDxfWriterEngine",
            "version": "1.0",
            "status": "PROJECT_DXF_FILES_OPGESLAGEN",
            "calculation_level": "basis DXF tekeningen export",
            "project_id": project_id,
            "project_name": project_name,
            "cad_dir": str(cad_dir),
            "written_files": written_files,
            "written_file_count": len(written_files),
            "drawing_engine_status": drawing_result.get("status", "ONBEKEND"),
            "cad_engine_status": cad_result.get("status", "ONBEKEND"),
            "geo_engine_status": geo_result.get("status", "ONBEKEND"),
            "structural_engine_status": structural_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(written_files),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project DXF Writer Engine v1.0 schrijft eenvoudige basis-DXF-bestanden. "
                "De tekeningen zijn schematisch en moeten later worden uitgebreid met echte geometrie, "
                "schaal, maatvoering, lagen, blokken, legenda en projectdata uit BIM/Digital Twin."
            )
        }

        return self.dxf_writer_result

    def write_dxf_file(self, file_path, title, drawing_type, project_result):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            dxf_content = self.build_dxf_content(
                title=title,
                drawing_type=drawing_type,
                project_result=project_result
            )

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(dxf_content)

            return {
                "drawing_type": drawing_type,
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }

        except Exception as error:
            return {
                "drawing_type": drawing_type,
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_dxf_content(self, title, drawing_type, project_result):
        project_name = project_result.get("project_name", "Onbekend project")
        location = project_result.get("location", "Onbekend")
        country = project_result.get("country", "Onbekend")
        project_type = project_result.get("project_type", "Onbekend")

        entities = []

        if drawing_type == "situatie":
            entities.extend(self.build_situation_entities())

        elif drawing_type == "plattegrond":
            entities.extend(self.build_floorplan_entities())

        elif drawing_type == "doorsnede":
            entities.extend(self.build_section_entities())

        entities.extend(
            self.build_title_block_entities(
                title=title,
                project_name=project_name,
                location=location,
                country=country,
                project_type=project_type
            )
        )

        return "\n".join([
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$ACADVER",
            "1",
            "AC1009",
            "0",
            "ENDSEC",
            "0",
            "SECTION",
            "2",
            "TABLES",
            "0",
            "TABLE",
            "2",
            "LAYER",
            "70",
            "4",
            self.layer_record("0"),
            self.layer_record("BAOEES_PROJECT"),
            self.layer_record("BAOEES_GEOMETRY"),
            self.layer_record("BAOEES_TEXT"),
            "0",
            "ENDTAB",
            "0",
            "ENDSEC",
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            *entities,
            "0",
            "ENDSEC",
            "0",
            "EOF"
        ])

    def layer_record(self, layer_name):
        return "\n".join([
            "0",
            "LAYER",
            "2",
            layer_name,
            "70",
            "0",
            "62",
            "7",
            "6",
            "CONTINUOUS"
        ])

    def build_situation_entities(self):
        entities = []

        entities.extend(self.dxf_rectangle(0, 0, 100, 70, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_rectangle(30, 20, 70, 50, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(0, -10, 100, -10, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_text(2, -18, 3, "Schematische situatie / perceel en gebouw", "BAOEES_TEXT"))

        return entities

    def build_floorplan_entities(self):
        entities = []

        entities.extend(self.dxf_rectangle(0, 0, 60, 40, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(20, 0, 20, 40, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(40, 0, 40, 40, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(0, 20, 60, 20, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_text(3, 32, 2.5, "Ruimte 1", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(23, 32, 2.5, "Ruimte 2", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(43, 32, 2.5, "Ruimte 3", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(2, -8, 3, "Schematische plattegrond", "BAOEES_TEXT"))

        return entities

    def build_section_entities(self):
        entities = []

        entities.extend(self.dxf_line(0, 0, 70, 0, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(5, 0, 5, 25, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(65, 0, 65, 25, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(5, 25, 35, 40, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(35, 40, 65, 25, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_line(5, 12, 65, 12, "BAOEES_GEOMETRY"))
        entities.extend(self.dxf_text(2, -8, 3, "Schematische doorsnede", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(8, 14, 2.5, "Verdieping / constructieniveau", "BAOEES_TEXT"))

        return entities

    def build_title_block_entities(
        self,
        title,
        project_name,
        location,
        country,
        project_type
    ):
        entities = []

        entities.extend(self.dxf_rectangle(0, -40, 100, -22, "BAOEES_PROJECT"))
        entities.extend(self.dxf_text(2, -26, 2.5, f"Titel: {title}", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(2, -30, 2.5, f"Project: {project_name}", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(2, -34, 2.5, f"Locatie: {location}, {country}", "BAOEES_TEXT"))
        entities.extend(self.dxf_text(2, -38, 2.5, f"Type: {project_type} | BAOEES V3 DXF export", "BAOEES_TEXT"))

        return entities

    def dxf_line(self, x1, y1, x2, y2, layer):
        return [
            "0", "LINE",
            "8", layer,
            "10", str(x1),
            "20", str(y1),
            "30", "0",
            "11", str(x2),
            "21", str(y2),
            "31", "0"
        ]

    def dxf_rectangle(self, x1, y1, x2, y2, layer):
        entities = []
        entities.extend(self.dxf_line(x1, y1, x2, y1, layer))
        entities.extend(self.dxf_line(x2, y1, x2, y2, layer))
        entities.extend(self.dxf_line(x2, y2, x1, y2, layer))
        entities.extend(self.dxf_line(x1, y2, x1, y1, layer))
        return entities

    def dxf_text(self, x, y, height, text, layer):
        clean_text = str(text).replace("\n", " ").replace("\r", " ")

        return [
            "0", "TEXT",
            "8", layer,
            "10", str(x),
            "20", str(y),
            "30", "0",
            "40", str(height),
            "1", clean_text[:240]
        ]

    def build_warnings(self, written_files):
        warnings = []

        for file_info in written_files:
            if file_info.get("status") != "OPGESLAGEN":
                warnings.append(
                    f"DXF-bestand niet opgeslagen: {file_info.get('path')}"
                )

        if not warnings:
            warnings.append("Geen kritieke DXF-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_DXF_WRITER_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste echte CAD/DXF-exportlaag. "
                "De volgende stap is om echte geometrie, maatvoering en lagen uit de Digital Twin "
                "te genereren."
            ),
            "next_steps": [
                "ProjectDxfWriterEngine koppelen aan BAOEES Core",
                "DXF-bestanden opnemen in ZIP-export",
                "maatvoering toevoegen",
                "lagenstructuur professionaliseren",
                "geometrie uit Digital Twin lezen",
                "per projecttype specifieke tekeningen genereren",
                "later DWG-export via externe converter toevoegen"
            ]
        }

    def get_dxf_writer_result(self):
        return self.dxf_writer_result

    def run(self):
        print("Project DXF Writer Engine actief")