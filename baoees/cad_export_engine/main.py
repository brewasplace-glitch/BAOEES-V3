import json
from datetime import datetime
from pathlib import Path


class CADExportEngine:

    def __init__(self):
        self.cad_result = {}

    def create_cad_exports(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        drawing_result=None,
        export_result=None
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        drawing_result = drawing_result or {}
        export_result = export_result or {}

        export_folder = export_result.get("export_folder")

        if not export_folder:
            self.cad_result = {
                "engine": "CADExportEngine",
                "version": "1.0",
                "status": "CAD_EXPORT_MISLUKT",
                "reason": "Geen export_folder gevonden in export_result."
            }
            return self.cad_result

        export_folder_path = Path(export_folder)
        cad_folder = export_folder_path / "cad_exports"
        cad_folder.mkdir(parents=True, exist_ok=True)

        dxf_path = cad_folder / "BAOEES_basis_cad_export.dxf"
        metadata_path = cad_folder / "cad_export_metadata.json"
        dwg_placeholder_path = cad_folder / "BAOEES_DWG_placeholder.txt"
        skp_placeholder_path = cad_folder / "BAOEES_SKP_placeholder.txt"
        ifc_placeholder_path = cad_folder / "BAOEES_IFC_placeholder.txt"

        files = []

        files.append(
            self.write_dxf_file(
                file_path=dxf_path,
                project_result=project_result,
                geo_result=geo_result,
                structural_result=structural_result
            )
        )

        metadata = self.build_metadata(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            drawing_result=drawing_result,
            dxf_path=dxf_path
        )

        files.append(
            self.write_json_file(
                file_path=metadata_path,
                data=metadata
            )
        )

        files.append(
            self.write_placeholder_file(
                file_path=dwg_placeholder_path,
                file_type="DWG",
                note="DWG-export volgt later via CAD-conversie of AutoCAD/ODA-koppeling."
            )
        )

        files.append(
            self.write_placeholder_file(
                file_path=skp_placeholder_path,
                file_type="SKP",
                note="SketchUp-export volgt later via SketchUp/FreeCAD/BIM-koppeling."
            )
        )

        files.append(
            self.write_placeholder_file(
                file_path=ifc_placeholder_path,
                file_type="IFC",
                note="IFC-export volgt later via FreeCAD/IFC BIM-koppeling."
            )
        )

        self.cad_result = {
            "engine": "CADExportEngine",
            "version": "1.0",
            "status": "CAD_EXPORT_GEREED",
            "cad_folder": str(cad_folder),
            "files": files,
            "metadata": metadata,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "note": "CAD/DXF basisexport aangemaakt. DWG/SKP/IFC zijn voorbereid als placeholders voor latere koppeling."
        }

        return self.cad_result

    def build_metadata(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        drawing_result=None,
        dxf_path=None
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        drawing_result = drawing_result or {}

        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Onbekend"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "engine": "CADExportEngine",
            "version": "1.0",
            "main_dxf": str(dxf_path),
            "units": "meter",
            "drawing_status": "CONCEPT",
            "layers": [
                {
                    "name": "BAOEES_CONTOUR",
                    "description": "Bouwcontour / basiscontour"
                },
                {
                    "name": "BAOEES_GRID",
                    "description": "Assen en hulplijnen"
                },
                {
                    "name": "BAOEES_FOUNDATION",
                    "description": "Funderingsschema"
                },
                {
                    "name": "BAOEES_STRUCTURAL",
                    "description": "Constructieve hoofdopzet"
                },
                {
                    "name": "BAOEES_TEXT",
                    "description": "Teksten en labels"
                }
            ],
            "geo_status": geo_result.get("status"),
            "structural_status": structural_result.get("status"),
            "drawing_export_status": drawing_result.get("status"),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

    def write_dxf_file(
        self,
        file_path,
        project_result=None,
        geo_result=None,
        structural_result=None
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}

        project_name = project_result.get("project_name", "BAOEES Project")
        location = project_result.get("location", "Onbekend")
        country = project_result.get("country", "Onbekend")

        dxf_lines = []

        self.add_dxf_header(dxf_lines)
        self.add_dxf_tables(dxf_lines)
        self.add_dxf_entities_start(dxf_lines)

        self.add_text(
            dxf_lines,
            layer="BAOEES_TEXT",
            x=0,
            y=15,
            height=0.5,
            text=f"BAOEES CAD/DXF EXPORT - {project_name}"
        )

        self.add_text(
            dxf_lines,
            layer="BAOEES_TEXT",
            x=0,
            y=14,
            height=0.3,
            text=f"Locatie: {location} - {country}"
        )

        self.add_text(
            dxf_lines,
            layer="BAOEES_TEXT",
            x=0,
            y=13.3,
            height=0.3,
            text="Status: CONCEPT DXF v1.0"
        )

        self.add_rectangle(
            dxf_lines,
            layer="BAOEES_CONTOUR",
            x=0,
            y=0,
            width=20,
            height=10
        )

        self.add_grid(
            dxf_lines,
            x=0,
            y=0,
            width=20,
            height=10,
            spacing=5
        )

        self.add_rectangle(
            dxf_lines,
            layer="BAOEES_FOUNDATION",
            x=1,
            y=1,
            width=18,
            height=8
        )

        self.add_line(
            dxf_lines,
            layer="BAOEES_STRUCTURAL",
            x1=0,
            y1=5,
            x2=20,
            y2=5
        )

        self.add_line(
            dxf_lines,
            layer="BAOEES_STRUCTURAL",
            x1=10,
            y1=0,
            x2=10,
            y2=10
        )

        self.add_text(
            dxf_lines,
            layer="BAOEES_TEXT",
            x=1,
            y=-1,
            height=0.3,
            text="Bouwcontour placeholder 20m x 10m"
        )

        self.add_text(
            dxf_lines,
            layer="BAOEES_TEXT",
            x=1,
            y=-1.7,
            height=0.3,
            text=f"Geo-status: {geo_result.get('status', 'onbekend')}"
        )

        self.add_text(
            dxf_lines,
            layer="BAOEES_TEXT",
            x=1,
            y=-2.4,
            height=0.3,
            text=f"Constructiestatus: {structural_result.get('status', 'onbekend')}"
        )

        self.add_dxf_end(dxf_lines)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write("\n".join(dxf_lines))

        return {
            "file": str(file_path),
            "format": "DXF",
            "status": "AANGEMAAKT"
        }

    def add_dxf_header(self, dxf_lines):
        dxf_lines.extend([
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$ACADVER",
            "1",
            "AC1009",
            "9",
            "$INSUNITS",
            "70",
            "6",
            "0",
            "ENDSEC"
        ])

    def add_dxf_tables(self, dxf_lines):
        layers = [
            "BAOEES_CONTOUR",
            "BAOEES_GRID",
            "BAOEES_FOUNDATION",
            "BAOEES_STRUCTURAL",
            "BAOEES_TEXT"
        ]

        dxf_lines.extend([
            "0",
            "SECTION",
            "2",
            "TABLES",
            "0",
            "TABLE",
            "2",
            "LAYER",
            "70",
            str(len(layers))
        ])

        for layer in layers:
            dxf_lines.extend([
                "0",
                "LAYER",
                "2",
                layer,
                "70",
                "0",
                "62",
                "7",
                "6",
                "CONTINUOUS"
            ])

        dxf_lines.extend([
            "0",
            "ENDTAB",
            "0",
            "ENDSEC"
        ])

    def add_dxf_entities_start(self, dxf_lines):
        dxf_lines.extend([
            "0",
            "SECTION",
            "2",
            "ENTITIES"
        ])

    def add_dxf_end(self, dxf_lines):
        dxf_lines.extend([
            "0",
            "ENDSEC",
            "0",
            "EOF"
        ])

    def add_line(self, dxf_lines, layer, x1, y1, x2, y2):
        dxf_lines.extend([
            "0",
            "LINE",
            "8",
            layer,
            "10",
            str(x1),
            "20",
            str(y1),
            "30",
            "0",
            "11",
            str(x2),
            "21",
            str(y2),
            "31",
            "0"
        ])

    def add_text(self, dxf_lines, layer, x, y, height, text):
        dxf_lines.extend([
            "0",
            "TEXT",
            "8",
            layer,
            "10",
            str(x),
            "20",
            str(y),
            "30",
            "0",
            "40",
            str(height),
            "1",
            str(text)
        ])

    def add_rectangle(self, dxf_lines, layer, x, y, width, height):
        self.add_line(dxf_lines, layer, x, y, x + width, y)
        self.add_line(dxf_lines, layer, x + width, y, x + width, y + height)
        self.add_line(dxf_lines, layer, x + width, y + height, x, y + height)
        self.add_line(dxf_lines, layer, x, y + height, x, y)

    def add_grid(self, dxf_lines, x, y, width, height, spacing):
        current_x = x

        while current_x <= x + width:
            self.add_line(
                dxf_lines,
                layer="BAOEES_GRID",
                x1=current_x,
                y1=y,
                x2=current_x,
                y2=y + height
            )
            current_x += spacing

        current_y = y

        while current_y <= y + height:
            self.add_line(
                dxf_lines,
                layer="BAOEES_GRID",
                x1=x,
                y1=current_y,
                x2=x + width,
                y2=current_y
            )
            current_y += spacing

    def write_json_file(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        return {
            "file": str(file_path),
            "format": "JSON",
            "status": "AANGEMAAKT"
        }

    def write_placeholder_file(self, file_path, file_type, note):
        lines = [
            f"BAOEES {file_type} EXPORT PLACEHOLDER",
            "=" * 40,
            "",
            f"Type: {file_type}",
            "Status: VOORBEREID",
            f"Opmerking: {note}",
            "",
            "Deze placeholder voorkomt dat de exportketen breekt.",
            "De echte exportmodule wordt in een latere versie gekoppeld."
        ]

        with open(file_path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))

        return {
            "file": str(file_path),
            "format": file_type,
            "status": "PLACEHOLDER_AANGEMAAKT"
        }

    def get_cad_result(self):
        return self.cad_result

    def run(self):
        print("CAD/DXF Export Engine actief")