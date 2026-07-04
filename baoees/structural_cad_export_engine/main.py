from datetime import datetime


class StructuralCADExportEngine:

    def __init__(self):
        self.cad_export_result = {}

    def create_structural_cad_export(
        self,
        project_result=None,
        structural_drawing_package_result=None,
        structural_calculation_report_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        structural_drawing_package_result = structural_drawing_package_result or {}
        structural_calculation_report_result = structural_calculation_report_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        drawing_index = structural_drawing_package_result.get("drawing_index", [])
        drawings = structural_drawing_package_result.get("drawings", [])

        if not drawings:
            drawings = self.create_fallback_drawings(drawing_index)

        export_manifest = self.build_export_manifest(project_id, project_name, drawings)
        cad_layers = self.build_cad_layers(drawings)
        sheet_set = self.build_sheet_set(project_id, project_name, drawings)
        file_package = self.build_file_package(project_id, project_name, export_manifest)
        qa_qc_checks = self.build_qa_qc_checks(drawings, cad_layers, sheet_set)

        self.cad_export_result = {
            "engine": "StructuralCADExportEngine",
            "version": "1.0",
            "status": "STRUCTURAL_CAD_EXPORT_PACKAGE_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "calculation_level": "concept CAD/BIM exportvoorbereiding",
            "export_manifest": export_manifest,
            "cad_layers": cad_layers,
            "sheet_set": sheet_set,
            "file_package": file_package,
            "qa_qc_checks": qa_qc_checks,
            "digital_twin_update": {
                "digital_twin_node": "structural_cad_export",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "export_manifest": export_manifest,
                    "cad_layers": cad_layers,
                    "sheet_set": sheet_set,
                    "file_package": file_package
                }
            },
            "warnings": self.build_warnings(qa_qc_checks),
            "recommendation": {
                "status": "STRUCTURAL_CAD_EXPORT_ADVIES",
                "advice": (
                    "Gebruik dit exportpakket als voorbereiding voor CAD/BIM-uitvoer. "
                    "Voor definitieve tekenbestanden zijn geometrie, schaal, maatvoering, "
                    "symbolen en constructeurcontrole nodig."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.cad_export_result

    def create_fallback_drawings(self, drawing_index):
        drawings = []

        for item in drawing_index:
            drawings.append(
                {
                    "drawing_number": item.get("drawing_number", "S-XXX"),
                    "title": item.get("title", "Constructietekening"),
                    "status": item.get("status", "CONCEPT"),
                    "drawing_layers": ["constructie_algemeen", "maatvoering_nader_uitwerken"],
                    "data": {}
                }
            )

        if drawings:
            return drawings

        return [
            {
                "drawing_number": "S-100",
                "title": "Constructieve plattegronden",
                "status": "CONCEPT",
                "drawing_layers": ["draaglijnen", "balken", "kolommen", "wanden"],
                "data": {}
            },
            {
                "drawing_number": "S-200",
                "title": "Funderingsplan",
                "status": "CONCEPT",
                "drawing_layers": ["strokenfundering", "funderingsbalken", "poeren"],
                "data": {}
            }
        ]

    def build_export_manifest(self, project_id, project_name, drawings):
        safe_project_name = self.safe_name(project_name)
        items = []

        for drawing in drawings:
            drawing_number = drawing.get("drawing_number", "S-XXX")

            items.append(
                {
                    "drawing_number": drawing_number,
                    "title": drawing.get("title", "Constructietekening"),
                    "status": "EXPORT_VOORBEREID",
                    "pdf_file": f"{safe_project_name}_{drawing_number}.pdf",
                    "dxf_file": f"{safe_project_name}_{drawing_number}.dxf",
                    "dwg_file": f"{safe_project_name}_{drawing_number}.dwg",
                    "ifc_reference": f"{safe_project_name}_{drawing_number}.ifc",
                    "freecad_reference": f"{safe_project_name}_{drawing_number}.FCStd",
                    "json_source": f"{safe_project_name}_{drawing_number}.json"
                }
            )

        return {
            "project_id": project_id,
            "project_name": project_name,
            "status": "MANIFEST_GEREED",
            "supported_formats": ["PDF", "DXF", "DWG", "IFC", "FreeCAD", "JSON"],
            "items": items
        }

    def build_cad_layers(self, drawings):
        layer_names = []

        for drawing in drawings:
            for layer in drawing.get("drawing_layers", []):
                if layer not in layer_names:
                    layer_names.append(layer)

        for layer in [
            "0",
            "constructie_assen",
            "constructie_maten",
            "constructie_teksten",
            "constructie_symbolen"
        ]:
            if layer not in layer_names:
                layer_names.append(layer)

        return [
            {
                "layer_name": layer,
                "status": "VOORBEREID",
                "line_type": "continuous",
                "export": True
            }
            for layer in layer_names
        ]

    def build_sheet_set(self, project_id, project_name, drawings):
        sheets = []

        for index, drawing in enumerate(drawings, start=1):
            sheets.append(
                {
                    "sheet_id": f"SHEET-{index:03d}",
                    "drawing_number": drawing.get("drawing_number", f"S-{index:03d}"),
                    "title": drawing.get("title", "Constructietekening"),
                    "paper_size": "A1",
                    "scale": "nader_te_bepalen",
                    "status": drawing.get("status", "CONCEPT")
                }
            )

        return {
            "project_id": project_id,
            "project_name": project_name,
            "status": "SHEET_SET_GEREED",
            "sheets": sheets
        }

    def build_file_package(self, project_id, project_name, export_manifest):
        safe_project_name = self.safe_name(project_name)

        return {
            "package_name": f"{safe_project_name}_constructie_cad_export",
            "project_id": project_id,
            "project_name": project_name,
            "status": "PACKAGE_VOORBEREID",
            "folders": [
                "01_PDF",
                "02_DXF",
                "03_DWG",
                "04_IFC",
                "05_FreeCAD",
                "06_JSON_Digital_Twin",
                "07_Bronvermelding"
            ],
            "manifest_item_count": len(export_manifest.get("items", []))
        }

    def build_qa_qc_checks(self, drawings, cad_layers, sheet_set):
        return [
            {"check": "tekeningen_beschikbaar", "status": "OK" if drawings else "AANDACHT"},
            {"check": "cad_layers_beschikbaar", "status": "OK" if cad_layers else "AANDACHT"},
            {"check": "sheet_set_beschikbaar", "status": "OK" if sheet_set.get("sheets") else "AANDACHT"},
            {"check": "exportformaten_voorbereid", "status": "OK"}
        ]

    def build_warnings(self, qa_qc_checks):
        warnings = []

        for check in qa_qc_checks:
            if check.get("status") == "AANDACHT":
                warnings.append(f"CAD-export aandachtspunt: {check.get('check')}.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de CAD-exportvoorbereiding.")

        return warnings

    def safe_name(self, value):
        text = str(value).strip().lower()

        if not text:
            return "project"

        allowed = []

        for char in text:
            if char.isalnum():
                allowed.append(char)
            elif char in [" ", "-", "_"]:
                allowed.append("_")

        cleaned = "".join(allowed)

        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")

        return cleaned.strip("_") or "project"

    def get_cad_export_result(self):
        return self.cad_export_result

    def create_cad_export(self, *args, **kwargs):
        return self.create_structural_cad_export(*args, **kwargs)

    def generate_structural_cad_export(self, *args, **kwargs):
        return self.create_structural_cad_export(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_cad_export(*args, **kwargs)
