import json
from datetime import datetime
from pathlib import Path


class DrawingExportEngine:

    def __init__(self):
        self.drawing_result = {}

    def create_drawings(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        export_result=None
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        export_result = export_result or {}

        export_folder = export_result.get("export_folder")

        if not export_folder:
            self.drawing_result = {
                "engine": "DrawingExportEngine",
                "status": "DRAWING_EXPORT_MISLUKT",
                "reason": "Geen export_folder gevonden in export_result."
            }
            return self.drawing_result

        export_folder_path = Path(export_folder)
        drawings_folder = export_folder_path / "tekeningen"
        drawings_folder.mkdir(parents=True, exist_ok=True)

        drawing_register = self.build_drawing_register(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result
        )

        files = []

        files.append(
            self.write_text_file(
                drawings_folder / "01_situatietekening.txt",
                self.create_situation_drawing_text(project_result)
            )
        )

        files.append(
            self.write_text_file(
                drawings_folder / "02_plattegrond.txt",
                self.create_floorplan_text(project_result)
            )
        )

        files.append(
            self.write_text_file(
                drawings_folder / "03_funderingsschema.txt",
                self.create_foundation_text(project_result, geo_result, structural_result)
            )
        )

        files.append(
            self.write_text_file(
                drawings_folder / "04_constructieschema.txt",
                self.create_structural_scheme_text(project_result, structural_result)
            )
        )

        files.append(
            self.write_json_file(
                drawings_folder / "tekeningregister.json",
                drawing_register
            )
        )

        files.append(
            self.write_dxf_placeholder(
                drawings_folder / "basis_tekening_placeholder.dxf",
                project_result
            )
        )

        self.drawing_result = {
            "engine": "DrawingExportEngine",
            "status": "DRAWING_EXPORT_GEREED",
            "drawings_folder": str(drawings_folder),
            "drawing_count": len(files),
            "files": files,
            "drawing_register": drawing_register,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "note": "Basis tekeningexport aangemaakt. Professionele maatvoering, schaal, CAD-layers en echte geometrie volgen in volgende versies."
        }

        return self.drawing_result

    def build_drawing_register(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None
    ):
        project_name = project_result.get("project_name", "Onbekend project")

        return {
            "project_name": project_name,
            "register_status": "CONCEPT",
            "drawings": [
                {
                    "drawing_number": "BAOEES-001",
                    "title": "Situatietekening",
                    "file": "01_situatietekening.txt",
                    "type": "situatie",
                    "status": "CONCEPT"
                },
                {
                    "drawing_number": "BAOEES-002",
                    "title": "Plattegrond",
                    "file": "02_plattegrond.txt",
                    "type": "plattegrond",
                    "status": "CONCEPT"
                },
                {
                    "drawing_number": "BAOEES-003",
                    "title": "Funderingsschema",
                    "file": "03_funderingsschema.txt",
                    "type": "fundering",
                    "status": "CONCEPT"
                },
                {
                    "drawing_number": "BAOEES-004",
                    "title": "Constructieschema",
                    "file": "04_constructieschema.txt",
                    "type": "constructie",
                    "status": "CONCEPT"
                },
                {
                    "drawing_number": "BAOEES-005",
                    "title": "Basis DXF placeholder",
                    "file": "basis_tekening_placeholder.dxf",
                    "type": "cad_placeholder",
                    "status": "CONCEPT"
                }
            ],
            "geo_basis": geo_result.get("status"),
            "structural_basis": structural_result.get("status"),
            "permit_basis": permit_result.get("status"),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

    def create_situation_drawing_text(self, project_result):
        return "\n".join([
            "BAOEES SITUATIETEKENING",
            "=======================",
            "",
            f"Project: {project_result.get('project_name', 'Onbekend')}",
            f"Locatie: {project_result.get('location', 'Onbekend')}",
            f"Land: {project_result.get('country', 'Onbekend')}",
            f"Projecttype: {project_result.get('project_type', 'Onbekend')}",
            "",
            "Inhoud:",
            "- projectlocatie",
            "- perceelcontour placeholder",
            "- noordpijl placeholder",
            "- schaal placeholder",
            "- omgeving placeholder",
            "",
            "Status: CONCEPT",
            "Opmerking: echte geometrie, kaartondergrond en maatvoering volgen in volgende versie."
        ])

    def create_floorplan_text(self, project_result):
        return "\n".join([
            "BAOEES PLATTEGROND",
            "==================",
            "",
            f"Project: {project_result.get('project_name', 'Onbekend')}",
            "",
            "Inhoud:",
            "- bouwcontour placeholder",
            "- ruimte-indeling placeholder",
            "- assen/grid placeholder",
            "- maatvoering placeholder",
            "- deuren/ramen placeholder",
            "",
            "Status: CONCEPT",
            "Opmerking: echte plattegrondgeometrie volgt via CAD/BIM-engine."
        ])

    def create_foundation_text(self, project_result, geo_result, structural_result):
        return "\n".join([
            "BAOEES FUNDERINGSSCHEMA",
            "=======================",
            "",
            f"Project: {project_result.get('project_name', 'Onbekend')}",
            "",
            "Geotechnische basis:",
            json.dumps(geo_result, ensure_ascii=False, indent=2),
            "",
            "Constructieve basis:",
            json.dumps(structural_result.get('foundation_assessment', {}), ensure_ascii=False, indent=2),
            "",
            "Status: CONCEPT",
            "Opmerking: funderingsafmetingen, wapening en details volgen na definitieve berekening."
        ])

    def create_structural_scheme_text(self, project_result, structural_result):
        return "\n".join([
            "BAOEES CONSTRUCTIESCHEMA",
            "========================",
            "",
            f"Project: {project_result.get('project_name', 'Onbekend')}",
            "",
            "Constructieve basisanalyse:",
            json.dumps(structural_result, ensure_ascii=False, indent=2),
            "",
            "Status: CONCEPT",
            "Opmerking: kolommen, balken, vloeren, dak, belastingen en opleggingen volgen in CAD/BIM-uitwerking."
        ])

    def write_text_file(self, file_path, text):
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text)

        return {
            "file": str(file_path),
            "format": "TXT",
            "status": "AANGEMAAKT"
        }

    def write_json_file(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        return {
            "file": str(file_path),
            "format": "JSON",
            "status": "AANGEMAAKT"
        }

    def write_dxf_placeholder(self, file_path, project_result):
        project_name = project_result.get("project_name", "BAOEES Project")

        dxf_text = "\n".join([
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
            "ENTITIES",
            "0",
            "TEXT",
            "8",
            "BAOEES_TEXT",
            "10",
            "0",
            "20",
            "0",
            "40",
            "2.5",
            "1",
            f"BAOEES DXF placeholder - {project_name}",
            "0",
            "LINE",
            "8",
            "BAOEES_CONTOUR",
            "10",
            "0",
            "20",
            "0",
            "11",
            "20",
            "21",
            "0",
            "0",
            "LINE",
            "8",
            "BAOEES_CONTOUR",
            "10",
            "20",
            "20",
            "0",
            "11",
            "20",
            "21",
            "10",
            "0",
            "LINE",
            "8",
            "BAOEES_CONTOUR",
            "10",
            "20",
            "20",
            "10",
            "11",
            "0",
            "21",
            "10",
            "0",
            "LINE",
            "8",
            "BAOEES_CONTOUR",
            "10",
            "0",
            "20",
            "10",
            "11",
            "0",
            "21",
            "0",
            "0",
            "ENDSEC",
            "0",
            "EOF"
        ])

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(dxf_text)

        return {
            "file": str(file_path),
            "format": "DXF",
            "status": "AANGEMAAKT"
        }

    def get_drawing_result(self):
        return self.drawing_result

    def run(self):
        print("Drawing Export Engine actief")