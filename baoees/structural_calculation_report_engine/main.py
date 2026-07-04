from datetime import datetime


class StructuralCalculationReportEngine:

    def __init__(self):
        self.report_result = {}

    def create_structural_calculation_report(
        self,
        project_result=None,
        building_technical_result=None,
        structural_load_result=None,
        element_load_result=None,
        foundation_load_transfer_result=None,
        foundation_design_result=None,
        foundation_verification_result=None,
        structural_element_sizing_result=None,
        structural_reinforcement_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        building_technical_result = building_technical_result or {}
        structural_load_result = structural_load_result or {}
        element_load_result = element_load_result or {}
        foundation_load_transfer_result = foundation_load_transfer_result or {}
        foundation_design_result = foundation_design_result or {}
        foundation_verification_result = foundation_verification_result or {}
        structural_element_sizing_result = structural_element_sizing_result or {}
        structural_reinforcement_result = structural_reinforcement_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        sections = [
            self.build_project_section(project_id, project_name, project_result),
            self.build_load_section(structural_load_result, element_load_result),
            self.build_foundation_section(
                foundation_load_transfer_result,
                foundation_design_result,
                foundation_verification_result
            ),
            self.build_sizing_section(structural_element_sizing_result),
            self.build_reinforcement_section(structural_reinforcement_result),
            self.build_qa_qc_section(
                structural_load_result,
                element_load_result,
                foundation_design_result,
                foundation_verification_result,
                structural_element_sizing_result,
                structural_reinforcement_result
            )
        ]

        qa_qc_checks = self.build_qa_qc_checks(sections)

        self.report_result = {
            "engine": "StructuralCalculationReportEngine",
            "version": "1.0",
            "status": "STRUCTURAL_CALCULATION_REPORT_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "report_type": "constructieve berekeningssamenvatting",
            "calculation_level": "indicatief / concept engineering",
            "sections": sections,
            "qa_qc_checks": qa_qc_checks,
            "digital_twin_update": {
                "digital_twin_node": "structural_calculation_report",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "sections": sections,
                    "qa_qc_checks": qa_qc_checks
                }
            },
            "warnings": self.build_warnings(sections, qa_qc_checks),
            "recommendation": {
                "status": "STRUCTURAL_REPORT_ADVIES",
                "advice": (
                    "Gebruik deze rapportage als conceptberekeningssamenvatting. "
                    "Voor definitieve engineering moeten projectspecifieke normen, "
                    "belastingen, detailberekeningen en constructeurcontrole worden toegevoegd."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.report_result

    def build_project_section(self, project_id, project_name, project_result):
        return {
            "section_id": "projectgegevens",
            "title": "Projectgegevens",
            "status": "GEREED",
            "content": {
                "project_id": project_id,
                "project_name": project_name,
                "location": project_result.get("location", project_result.get("address", "Onbekend")),
                "building_function": project_result.get("building_function", "nog_te_bepalen")
            }
        }

    def build_load_section(self, structural_load_result, element_load_result):
        return {
            "section_id": "belastingen_en_elementlasten",
            "title": "Belastingen en elementlasten",
            "status": self.status_from_inputs(structural_load_result, element_load_result),
            "content": {
                "structural_load_status": structural_load_result.get("status", "ONTBREEKT"),
                "element_load_status": element_load_result.get("status", "ONTBREEKT"),
                "permanent_loads": structural_load_result.get("permanent_loads", {}),
                "imposed_loads": structural_load_result.get("imposed_loads", {}),
                "load_combinations": structural_load_result.get("load_combinations", {}),
                "load_takeoff_summary": element_load_result.get("load_takeoff_summary", {})
            }
        }

    def build_foundation_section(
        self,
        foundation_load_transfer_result,
        foundation_design_result,
        foundation_verification_result
    ):
        return {
            "section_id": "fundering",
            "title": "Funderingsontwerp en controle",
            "status": self.status_from_inputs(
                foundation_load_transfer_result,
                foundation_design_result,
                foundation_verification_result
            ),
            "content": {
                "load_transfer_status": foundation_load_transfer_result.get("status", "ONTBREEKT"),
                "foundation_design_status": foundation_design_result.get("status", "ONTBREEKT"),
                "foundation_verification_status": foundation_verification_result.get("status", "ONTBREEKT"),
                "foundation_loads": foundation_load_transfer_result.get("foundation_loads", {}),
                "foundation_design": foundation_design_result.get("foundation_design", {}),
                "foundation_verification": foundation_verification_result.get("foundation_verification", {})
            }
        }

    def build_sizing_section(self, structural_element_sizing_result):
        return {
            "section_id": "elementafmetingen",
            "title": "Voorlopige constructieve elementafmetingen",
            "status": self.status_from_inputs(structural_element_sizing_result),
            "content": {
                "sizing_status": structural_element_sizing_result.get("status", "ONTBREEKT"),
                "sizing_summary": structural_element_sizing_result.get("sizing_summary", {}),
                "element_dimensions": structural_element_sizing_result.get("element_dimensions", {})
            }
        }

    def build_reinforcement_section(self, structural_reinforcement_result):
        return {
            "section_id": "wapeningsvoorstellen",
            "title": "Voorlopige wapeningsvoorstellen",
            "status": self.status_from_inputs(structural_reinforcement_result),
            "content": {
                "reinforcement_status": structural_reinforcement_result.get("status", "ONTBREEKT"),
                "reinforcement_summary": structural_reinforcement_result.get("reinforcement_summary", {}),
                "reinforcement_proposals": structural_reinforcement_result.get("reinforcement_proposals", {})
            }
        }

    def build_qa_qc_section(
        self,
        structural_load_result,
        element_load_result,
        foundation_design_result,
        foundation_verification_result,
        structural_element_sizing_result,
        structural_reinforcement_result
    ):
        source_statuses = {
            "structural_loads": structural_load_result.get("status", "ONTBREEKT"),
            "element_loads": element_load_result.get("status", "ONTBREEKT"),
            "foundation_design": foundation_design_result.get("status", "ONTBREEKT"),
            "foundation_verification": foundation_verification_result.get("status", "ONTBREEKT"),
            "structural_element_sizing": structural_element_sizing_result.get("status", "ONTBREEKT"),
            "structural_reinforcement": structural_reinforcement_result.get("status", "ONTBREEKT")
        }

        return {
            "section_id": "qa_qc_en_aandachtspunten",
            "title": "QA/QC en aandachtspunten",
            "status": "GEREED",
            "content": {
                "source_statuses": source_statuses,
                "note": (
                    "Deze samenvatting is gebaseerd op indicatieve engines. "
                    "Ontbrekende of foutstatussen moeten voor definitieve rapportage worden opgelost."
                )
            }
        }

    def build_qa_qc_checks(self, sections):
        checks = []

        for section in sections:
            checks.append(
                {
                    "check": f"sectie_{section.get('section_id')}",
                    "status": "OK" if section.get("status") != "ONTBREEKT" else "AANDACHT"
                }
            )

        return checks

    def build_warnings(self, sections, qa_qc_checks):
        warnings = []

        for section in sections:
            if section.get("status") == "ONTBREEKT":
                warnings.append(f"Sectie ontbreekt of heeft onvoldoende brondata: {section.get('title')}.")

        for check in qa_qc_checks:
            if check.get("status") == "AANDACHT":
                warnings.append(f"QA/QC aandachtspunt: {check.get('check')}.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de constructieve rapportagesamenvatting.")

        return warnings

    def status_from_inputs(self, *items):
        for item in items:
            if item and item.get("status"):
                return "GEREED"

        return "ONTBREEKT"

    def get_report_result(self):
        return self.report_result

    def create_report(self, *args, **kwargs):
        return self.create_structural_calculation_report(*args, **kwargs)

    def generate_report(self, *args, **kwargs):
        return self.create_structural_calculation_report(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_calculation_report(*args, **kwargs)
