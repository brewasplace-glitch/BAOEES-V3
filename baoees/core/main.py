from pprint import pprint

from baoees.project_selector_engine.main import ProjectSelectorEngine
from baoees.project_config_engine.main import ProjectConfigEngine
from baoees.project_storage_engine.main import ProjectStorageEngine
from baoees.project_file_writer_engine.main import ProjectFileWriterEngine
from baoees.project_report_writer_engine.main import ProjectReportWriterEngine
from baoees.project_pdf_docx_writer_engine.main import ProjectPdfDocxWriterEngine
from baoees.project_dxf_writer_engine.main import ProjectDxfWriterEngine
from baoees.project_drawing_pdf_writer_engine.main import ProjectDrawingPdfWriterEngine
from baoees.project_csv_excel_export_engine.main import ProjectCsvExcelExportEngine
from baoees.project_xlsx_export_engine.main import ProjectXlsxExportEngine
from baoees.project_html_dashboard_export_engine.main import ProjectHtmlDashboardExportEngine
from baoees.project_index_startpage_engine.main import ProjectIndexStartpageEngine
from baoees.project_audit_trail_engine.main import ProjectAuditTrailEngine
from baoees.project_checksum_engine.main import ProjectChecksumEngine
from baoees.project_git_evidence_engine.main import ProjectGitEvidenceEngine

from baoees.project_analyzer.main import ProjectAnalyzer
from baoees.aaie.main import AAIEEngine
from baoees.variant_engine.main import VariantEngine
from baoees.geo_engine.main import GeoEngine
from baoees.structural_engine.main import StructuralEngine
from baoees.permit_engine.main import PermitEngine
from baoees.reporting_engine.main import ReportingEngine
from baoees.project_export_engine.main import ProjectExportEngine
from baoees.document_export_engine.main import DocumentExportEngine
from baoees.drawing_export_engine.main import DrawingExportEngine
from baoees.cad_export_engine.main import CADExportEngine
from baoees.cost_engine.main import CostEngine
from baoees.planning_engine.main import PlanningEngine
from baoees.traffic_parking_engine.main import TrafficParkingEngine
from baoees.drainage_sewerage_engine.main import DrainageSewerageEngine
from baoees.aerius_engine.main import AERIUSEngine
from baoees.gis_map_engine.main import GISMapEngine
from baoees.validation_engine.main import ValidationEngine
from baoees.quantity_engine.main import QuantityEngine
from baoees.specification_engine.main import SpecificationEngine
from baoees.tender_engine.main import TenderEngine
from baoees.contract_engine.main import ContractEngine
from baoees.construction_execution_engine.main import ConstructionExecutionEngine
from baoees.site_monitoring_engine.main import SiteMonitoringEngine
from baoees.as_built_engine.main import AsBuiltEngine
from baoees.asset_management_engine.main import AssetManagementEngine
from baoees.sustainability_engine.main import SustainabilityEngine
from baoees.global_codes_engine.main import GlobalCodesEngine
from baoees.learning_engine.main import LearningEngine
from baoees.runtime_engine.main import RuntimeEngine
from baoees.project_zip_engine.main import ProjectZipEngine
from baoees.digital_twin.main import DigitalTwin
from baoees.workflow_engine.main import WorkflowEngine
from baoees.stee.main import STEEEngine


class BAOEESCore:

    def __init__(self):
        print("BAOEES Core gestart")

        self.project_selector = ProjectSelectorEngine()
        self.project_config = ProjectConfigEngine()
        self.project_storage = ProjectStorageEngine()
        self.project_file_writer = ProjectFileWriterEngine()
        self.project_report_writer = ProjectReportWriterEngine()
        self.project_pdf_docx_writer = ProjectPdfDocxWriterEngine()
        self.project_dxf_writer = ProjectDxfWriterEngine()
        self.project_drawing_pdf_writer = ProjectDrawingPdfWriterEngine()
        self.project_csv_excel_export = ProjectCsvExcelExportEngine()
        self.project_xlsx_export = ProjectXlsxExportEngine()
        self.project_html_dashboard_export = ProjectHtmlDashboardExportEngine()
        self.project_index_startpage = ProjectIndexStartpageEngine()
        self.project_audit_trail = ProjectAuditTrailEngine()
        self.project_checksum = ProjectChecksumEngine()
        self.project_git_evidence = ProjectGitEvidenceEngine()

        self.project_analyzer = ProjectAnalyzer()
        self.aaie = AAIEEngine()
        self.variant = VariantEngine()
        self.geo = GeoEngine()
        self.structural = StructuralEngine()
        self.permit = PermitEngine()
        self.reporting = ReportingEngine()
        self.project_export = ProjectExportEngine()
        self.document_export = DocumentExportEngine()
        self.drawing_export = DrawingExportEngine()
        self.cad_export = CADExportEngine()
        self.cost = CostEngine()
        self.planning = PlanningEngine()
        self.traffic_parking = TrafficParkingEngine()
        self.drainage_sewerage = DrainageSewerageEngine()
        self.aerius = AERIUSEngine()
        self.gis_map = GISMapEngine()
        self.validation = ValidationEngine()
        self.quantity = QuantityEngine()
        self.specification = SpecificationEngine()
        self.tender = TenderEngine()
        self.contract = ContractEngine()
        self.construction_execution = ConstructionExecutionEngine()
        self.site_monitoring = SiteMonitoringEngine()
        self.as_built = AsBuiltEngine()
        self.asset_management = AssetManagementEngine()
        self.sustainability = SustainabilityEngine()
        self.global_codes = GlobalCodesEngine()
        self.learning = LearningEngine()
        self.runtime = RuntimeEngine()
        self.project_zip = ProjectZipEngine()
        self.digital_twin = DigitalTwin()
        self.workflow = WorkflowEngine()
        self.stee = STEEEngine()

    def print_result(self, title, result):
        print(title)
        pprint(result)
        print("")

    def start_projectanalyse(self, project_id=None, runtime_mode="autonomous"):

        print("\n=== START PROJECTANALYSE ===\n")

        selector_result = self.project_selector.select_project(project_id=project_id)
        selected_config_path = selector_result["selected_config_path"]
        self.print_result("Project Selector / Project Library Engine resultaat:", selector_result)

        config_result = self.project_config.load_project_config(
            config_path=selected_config_path
        )
        project_config = config_result["project_config"]
        self.print_result("Project Configuration / Input Engine resultaat:", config_result)

        project_result = self.project_analyzer.analyze(
            project_name=project_config["project_name"],
            project_description=project_config["project_description"],
            location=project_config["location"],
            country=project_config["country"],
            project_type=project_config["project_type"]
        )

        project_result["runtime_mode"] = runtime_mode
        project_result["selected_project_id"] = selector_result.get(
            "selected_project", {}
        ).get("project_id")

        self.print_result("Project Analyzer resultaat:", project_result)

        storage_result = self.project_storage.prepare_project_storage(
            project_result=project_result,
            selector_result=selector_result,
            config_result=config_result
        )
        self.print_result("Project Storage / Output Folder Engine resultaat:", storage_result)

        aaie_result = self.aaie.infer_missing_parameters(project_result)
        self.print_result("AAIE resultaat:", aaie_result)

        variant_result = self.variant.generate_variants(
            project_result=project_result,
            aaie_result=aaie_result
        )
        self.print_result("Variant Engine resultaat:", variant_result)

        geo_result = self.geo.analyze_geotechnics(
            project_result=project_result,
            aaie_result=aaie_result
        )
        self.print_result("Geo Engine resultaat:", geo_result)

        structural_result = self.structural.analyze_structure(
            project_result=project_result,
            geo_result=geo_result,
            aaie_result=aaie_result
        )
        self.print_result("Structural Engine resultaat:", structural_result)

        permit_result = self.permit.prepare_permit_strategy(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            structural_result=structural_result,
            variant_result=variant_result
        )
        self.print_result("Permit Engine resultaat:", permit_result)

        self.digital_twin.create_project_twin(
            project_result=project_result,
            aaie_result=aaie_result
        )

        self.digital_twin.add_object(
            object_type="project_selector",
            name="BAOEES Project Selector / Project Library Engine projectkeuze",
            data=selector_result
        )

        self.digital_twin.add_object(
            object_type="project_configuration",
            name="BAOEES Project Configuration / Input Engine projectinvoer",
            data=config_result
        )

        self.digital_twin.add_object(
            object_type="project_storage",
            name="BAOEES Project Storage / Output Folder Engine projectmap",
            data=storage_result
        )

        for variant in variant_result["variants"]:
            self.digital_twin.add_object(
                object_type="design_variant",
                name=f"Variant {variant['variant']} - {variant['name']}",
                data=variant
            )

        self.digital_twin.add_object(
            object_type="geo_analysis",
            name="BAOEES Geo Engine analyse",
            data=geo_result
        )

        self.digital_twin.add_object(
            object_type="structural_analysis",
            name="BAOEES Structural Engine analyse",
            data=structural_result
        )

        self.digital_twin.add_object(
            object_type="permit_strategy",
            name="BAOEES Permit Engine vergunningstrategie",
            data=permit_result
        )

        stee_result = self.stee.register_project_sources(
            project_result=project_result,
            aaie_result=aaie_result
        )

        for source_record in stee_result["source_register"]:
            self.digital_twin.add_source(
                source=source_record["source"],
                purpose=source_record["purpose"]
            )

        workflow_result = self.workflow.create_workflow(
            project_result=project_result,
            aaie_result=aaie_result,
            variant_result=variant_result,
            stee_result=stee_result
        )

        self.digital_twin.add_object(
            object_type="workflow",
            name="BAOEES automatische projectworkflow",
            data=workflow_result
        )

        reporting_result = self.reporting.generate_report_structure(
            project_result=project_result,
            aaie_result=aaie_result,
            variant_result=variant_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            stee_result=stee_result,
            workflow_result=workflow_result,
            digital_twin_data=self.digital_twin.get_project_data()
        )

        self.digital_twin.add_object(
            object_type="reporting_output",
            name="BAOEES Reporting Engine rapportstructuur",
            data=reporting_result
        )

        export_result = self.project_export.create_project_export(
            project_result=project_result,
            digital_twin_data=self.digital_twin.get_project_data(),
            reporting_result=reporting_result,
            stee_result=stee_result
        )

        self.digital_twin.add_object(
            object_type="project_export",
            name="BAOEES Project Export Engine exportpakket",
            data=export_result
        )

        document_result = self.document_export.create_documents(
            project_result=project_result,
            reporting_result=reporting_result,
            export_result=export_result
        )

        self.digital_twin.add_object(
            object_type="document_export",
            name="BAOEES PDF/DOCX Export Engine documenten",
            data=document_result
        )

        drawing_result = self.drawing_export.create_drawings(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            export_result=export_result
        )

        self.digital_twin.add_object(
            object_type="drawing_export",
            name="BAOEES Drawing Export Engine tekeningen",
            data=drawing_result
        )

        cad_result = self.cad_export.create_cad_exports(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            drawing_result=drawing_result,
            export_result=export_result
        )

        self.digital_twin.add_object(
            object_type="cad_export",
            name="BAOEES CAD/DXF Export Engine CAD-bestanden",
            data=cad_result
        )

        dxf_writer_result = self.project_dxf_writer.write_project_dxfs(
            project_result=project_result,
            storage_result=storage_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            geo_result=geo_result,
            structural_result=structural_result
        )

        self.digital_twin.add_object(
            object_type="project_dxf_writer",
            name="BAOEES Project DXF Writer Engine tekenbestanden",
            data=dxf_writer_result
        )

        drawing_pdf_result = self.project_drawing_pdf_writer.write_drawing_pdfs(
            project_result=project_result,
            storage_result=storage_result,
            drawing_result=drawing_result,
            dxf_writer_result=dxf_writer_result
        )

        self.digital_twin.add_object(
            object_type="project_drawing_pdf_writer",
            name="BAOEES Project Drawing PDF Writer Engine tekening-PDF-bestanden",
            data=drawing_pdf_result
        )

        cost_result = self.cost.estimate_costs(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            reporting_result=reporting_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        self.digital_twin.add_object(
            object_type="cost_estimate",
            name="BAOEES Cost Estimate Engine kostenraming",
            data=cost_result
        )

        planning_result = self.planning.create_planning(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            reporting_result=reporting_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            cost_result=cost_result
        )

        self.digital_twin.add_object(
            object_type="planning",
            name="BAOEES Planning Engine projectplanning",
            data=planning_result
        )

        traffic_parking_result = self.traffic_parking.analyze_traffic_and_parking(
            project_result=project_result,
            aaie_result=aaie_result,
            permit_result=permit_result,
            planning_result=planning_result,
            cost_result=cost_result
        )

        self.digital_twin.add_object(
            object_type="traffic_parking",
            name="BAOEES Traffic & Parking Engine verkeers- en parkeeranalyse",
            data=traffic_parking_result
        )

        drainage_result = self.drainage_sewerage.design_drainage_and_sewerage(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            structural_result=structural_result,
            traffic_parking_result=traffic_parking_result,
            cost_result=cost_result
        )

        self.digital_twin.add_object(
            object_type="drainage_sewerage",
            name="BAOEES Drainage & Sewerage Engine riolering en afwatering",
            data=drainage_result
        )

        aerius_result = self.aerius.prepare_aerius_assessment(
            project_result=project_result,
            aaie_result=aaie_result,
            traffic_parking_result=traffic_parking_result,
            planning_result=planning_result,
            cost_result=cost_result,
            drainage_result=drainage_result
        )

        self.digital_twin.add_object(
            object_type="aerius_stikstof",
            name="BAOEES AERIUS / Stikstof Engine voorbereiding",
            data=aerius_result
        )

        gis_result = self.gis_map.analyze_location_and_maps(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            traffic_parking_result=traffic_parking_result,
            drainage_result=drainage_result,
            aerius_result=aerius_result
        )

        self.digital_twin.add_object(
            object_type="gis_map",
            name="BAOEES GIS / Map Engine locatie- en kaartanalyse",
            data=gis_result
        )

        quantity_result = self.quantity.generate_quantities(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            structural_result=structural_result,
            drainage_result=drainage_result,
            traffic_parking_result=traffic_parking_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        self.digital_twin.add_object(
            object_type="quantity_boq",
            name="BAOEES Quantity / BOQ Engine hoeveelhedenstaat",
            data=quantity_result
        )

        validation_result = self.validation.validate_project(
            project_result=project_result,
            aaie_result=aaie_result,
            variant_result=variant_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            reporting_result=reporting_result,
            export_result=export_result,
            document_result=document_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            cost_result=cost_result,
            planning_result=planning_result,
            traffic_parking_result=traffic_parking_result,
            drainage_result=drainage_result,
            aerius_result=aerius_result,
            gis_result=gis_result,
            stee_result=stee_result,
            workflow_result=workflow_result,
            digital_twin_data=self.digital_twin.get_project_data()
        )

        self.digital_twin.add_object(
            object_type="validation_qa_qc",
            name="BAOEES Validation & QA/QC Engine controle",
            data=validation_result
        )

        specification_result = self.specification.generate_specification(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            structural_result=structural_result,
            drainage_result=drainage_result,
            traffic_parking_result=traffic_parking_result,
            quantity_result=quantity_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="specification_bestek",
            name="BAOEES Specification / Bestek Engine werkbeschrijving",
            data=specification_result
        )

        tender_result = self.tender.prepare_tender_package(
            project_result=project_result,
            cost_result=cost_result,
            planning_result=planning_result,
            quantity_result=quantity_result,
            specification_result=specification_result,
            validation_result=validation_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        self.digital_twin.add_object(
            object_type="tender_procurement",
            name="BAOEES Tender / Procurement Engine aanbestedingspakket",
            data=tender_result
        )

        contract_result = self.contract.prepare_contract_package(
            project_result=project_result,
            cost_result=cost_result,
            planning_result=planning_result,
            quantity_result=quantity_result,
            specification_result=specification_result,
            tender_result=tender_result,
            validation_result=validation_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        self.digital_twin.add_object(
            object_type="contract_agreement",
            name="BAOEES Contract / Agreement Engine contractpakket",
            data=contract_result
        )

        construction_execution_result = self.construction_execution.prepare_execution_plan(
            project_result=project_result,
            planning_result=planning_result,
            contract_result=contract_result,
            specification_result=specification_result,
            quantity_result=quantity_result,
            geo_result=geo_result,
            structural_result=structural_result,
            drainage_result=drainage_result,
            traffic_parking_result=traffic_parking_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="construction_execution",
            name="BAOEES Construction Execution Engine uitvoeringsplan",
            data=construction_execution_result
        )

        site_monitoring_result = self.site_monitoring.create_monitoring_plan(
            project_result=project_result,
            planning_result=planning_result,
            construction_execution_result=construction_execution_result,
            contract_result=contract_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="site_monitoring_progress",
            name="BAOEES Site Monitoring / Progress Engine bouwplaatsbewaking",
            data=site_monitoring_result
        )

        as_built_result = self.as_built.prepare_as_built_package(
            project_result=project_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            contract_result=contract_result,
            construction_execution_result=construction_execution_result,
            site_monitoring_result=site_monitoring_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="as_built_delivery",
            name="BAOEES As-Built / Oplever Engine opleverdossier",
            data=as_built_result
        )

        asset_result = self.asset_management.prepare_asset_management_plan(
            project_result=project_result,
            as_built_result=as_built_result,
            contract_result=contract_result,
            site_monitoring_result=site_monitoring_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="asset_management_maintenance",
            name="BAOEES Asset Management / Maintenance Engine beheerdossier",
            data=asset_result
        )

        sustainability_result = self.sustainability.analyze_sustainability(
            project_result=project_result,
            aaie_result=aaie_result,
            drainage_result=drainage_result,
            aerius_result=aerius_result,
            asset_result=asset_result,
            quantity_result=quantity_result,
            cost_result=cost_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="sustainability_climate",
            name="BAOEES Sustainability / Climate Engine duurzaamheid en klimaat",
            data=sustainability_result
        )

        codes_result = self.global_codes.analyze_codes_and_standards(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            drainage_result=drainage_result,
            traffic_parking_result=traffic_parking_result,
            sustainability_result=sustainability_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="global_codes_standards",
            name="BAOEES Global Codes / Standards Engine normen en regelgeving",
            data=codes_result
        )

        learning_result = self.learning.analyze_project_learning(
            project_result=project_result,
            aaie_result=aaie_result,
            validation_result=validation_result,
            codes_result=codes_result,
            stee_result=stee_result,
            digital_twin_data=self.digital_twin.get_project_data()
        )

        self.digital_twin.add_object(
            object_type="autonomous_learning_knowledge",
            name="BAOEES Autonomous Learning / Knowledge Engine leeranalyse",
            data=learning_result
        )

        engine_results = {
            "project_selector": selector_result,
            "project_config": config_result,
            "project_storage": storage_result,
            "project": project_result,
            "aaie": aaie_result,
            "variant": variant_result,
            "geo": geo_result,
            "structural": structural_result,
            "permit": permit_result,
            "stee": stee_result,
            "workflow": workflow_result,
            "reporting": reporting_result,
            "project_export": export_result,
            "document_export": document_result,
            "drawing_export": drawing_result,
            "cad_export": cad_result,
            "dxf_writer": dxf_writer_result,
            "drawing_pdf_writer": drawing_pdf_result,
            "cost": cost_result,
            "planning": planning_result,
            "traffic_parking": traffic_parking_result,
            "drainage_sewerage": drainage_result,
            "aerius": aerius_result,
            "gis": gis_result,
            "quantity": quantity_result,
            "validation": validation_result,
            "specification": specification_result,
            "tender": tender_result,
            "contract": contract_result,
            "construction_execution": construction_execution_result,
            "site_monitoring": site_monitoring_result,
            "as_built": as_built_result,
            "asset_management": asset_result,
            "sustainability": sustainability_result,
            "global_codes": codes_result,
            "learning": learning_result
        }

        runtime_result = self.runtime.create_runtime_log(
            project_result=project_result,
            engine_results=engine_results,
            digital_twin_data=self.digital_twin.get_project_data()
        )

        runtime_result["runtime_mode"] = runtime_mode
        runtime_result["launcher_project_id"] = project_id

        self.digital_twin.add_object(
            object_type="runtime_orchestration",
            name="BAOEES Runtime / Orchestration Engine runtime-log",
            data=runtime_result
        )

        csv_excel_result = self.project_csv_excel_export.export_project_tables(
            project_result=project_result,
            storage_result=storage_result,
            cost_result=cost_result,
            planning_result=planning_result,
            quantity_result=quantity_result,
            validation_result=validation_result,
            runtime_result=runtime_result
        )

        self.digital_twin.add_object(
            object_type="project_csv_excel_export",
            name="BAOEES Project CSV/Excel Export Engine projecttabellen",
            data=csv_excel_result
        )

        xlsx_result = self.project_xlsx_export.export_project_xlsx(
            project_result=project_result,
            storage_result=storage_result,
            cost_result=cost_result,
            planning_result=planning_result,
            quantity_result=quantity_result,
            validation_result=validation_result,
            runtime_result=runtime_result,
            csv_excel_result=csv_excel_result
        )

        self.digital_twin.add_object(
            object_type="project_xlsx_export",
            name="BAOEES Project XLSX Export Engine Excel-werkboek",
            data=xlsx_result
        )

        file_writer_result = self.project_file_writer.write_project_files(
            project_result=project_result,
            storage_result=storage_result,
            config_result=config_result,
            selector_result=selector_result,
            digital_twin_data=self.digital_twin.get_project_data(),
            stee_result=stee_result,
            runtime_result=runtime_result,
            validation_result=validation_result
        )

        self.digital_twin.add_object(
            object_type="project_file_writer",
            name="BAOEES Project File Writer / JSON Export Engine bestanden",
            data=file_writer_result
        )

        report_writer_result = self.project_report_writer.write_project_report(
            project_result=project_result,
            storage_result=storage_result,
            config_result=config_result,
            selector_result=selector_result,
            reporting_result=reporting_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            cost_result=cost_result,
            planning_result=planning_result,
            validation_result=validation_result,
            runtime_result=runtime_result
        )

        self.digital_twin.add_object(
            object_type="project_report_writer",
            name="BAOEES Project Report Writer Engine rapportbestanden",
            data=report_writer_result
        )

        pdf_docx_result = self.project_pdf_docx_writer.write_pdf_docx_reports(
            project_result=project_result,
            storage_result=storage_result,
            report_writer_result=report_writer_result,
            validation_result=validation_result,
            runtime_result=runtime_result
        )

        self.digital_twin.add_object(
            object_type="project_pdf_docx_writer",
            name="BAOEES PDF/DOCX Report Export Engine rapportbestanden",
            data=pdf_docx_result
        )

        html_dashboard_result = self.project_html_dashboard_export.export_project_dashboard(
            project_result=project_result,
            storage_result=storage_result,
            report_writer_result=report_writer_result,
            pdf_docx_result=pdf_docx_result,
            dxf_writer_result=dxf_writer_result,
            drawing_pdf_result=drawing_pdf_result,
            csv_excel_result=csv_excel_result,
            xlsx_result=xlsx_result,
            validation_result=validation_result,
            runtime_result=runtime_result
        )

        self.digital_twin.add_object(
            object_type="project_html_dashboard_export",
            name="BAOEES Project HTML Dashboard Export Engine dashboard",
            data=html_dashboard_result
        )

        index_result = self.project_index_startpage.create_project_index(
            projects_root="outputs/projects",
            project_index_path="configs/projects/project_index.json"
        )

        self.digital_twin.add_object(
            object_type="project_index_startpage",
            name="BAOEES Project Index / Startpage Engine centrale startpagina",
            data=index_result
        )

        zip_result = self.project_zip.create_project_zip(
            export_result=export_result,
            storage_result=storage_result,
            file_writer_result=file_writer_result
        )

        self.digital_twin.add_object(
            object_type="project_zip",
            name="BAOEES Project ZIP Engine zipbestand",
            data=zip_result
        )

        audit_result = self.project_audit_trail.register_project_run(
            project_result=project_result,
            storage_result=storage_result,
            selector_result=selector_result,
            config_result=config_result,
            runtime_result=runtime_result,
            validation_result=validation_result,
            file_writer_result=file_writer_result,
            report_writer_result=report_writer_result,
            pdf_docx_result=pdf_docx_result,
            dxf_writer_result=dxf_writer_result,
            drawing_pdf_result=drawing_pdf_result,
            csv_excel_result=csv_excel_result,
            xlsx_result=xlsx_result,
            html_dashboard_result=html_dashboard_result,
            zip_result=zip_result,
            index_result=index_result
        )

        self.digital_twin.add_object(
            object_type="project_audit_trail",
            name="BAOEES Project Run Log / Audit Trail Engine runregistratie",
            data=audit_result
        )

        checksum_result = self.project_checksum.create_file_manifest(
            project_result=project_result,
            storage_result=storage_result,
            audit_result=audit_result
        )

        self.digital_twin.add_object(
            object_type="project_checksum_file_integrity",
            name="BAOEES Project Checksum / File Integrity Engine file manifest",
            data=checksum_result
        )

        git_evidence_result = self.project_git_evidence.create_git_evidence(
            project_result=project_result,
            storage_result=storage_result,
            audit_result=audit_result,
            checksum_result=checksum_result,
            repo_root="."
        )

        self.digital_twin.add_object(
            object_type="project_git_evidence",
            name="BAOEES Project Version / Git Evidence Engine codeversiebewijs",
            data=git_evidence_result
        )

        final_zip_result = self.project_zip.create_project_zip(
            export_result=export_result,
            storage_result=storage_result,
            file_writer_result=file_writer_result
        )

        self.digital_twin.add_object(
            object_type="project_final_zip",
            name="BAOEES Project ZIP Engine finale zip inclusief audit trail, file manifest en Git evidence",
            data=final_zip_result
        )

        self.print_result("STEE resultaat:", stee_result)
        self.print_result("Workflow Engine resultaat:", workflow_result)
        self.print_result("Reporting Engine resultaat:", reporting_result)
        self.print_result("Project Export Engine resultaat:", export_result)
        self.print_result("PDF/DOCX Export Engine resultaat:", document_result)
        self.print_result("Drawing Export Engine resultaat:", drawing_result)
        self.print_result("CAD/DXF Export Engine resultaat:", cad_result)
        self.print_result("Project DXF Writer Engine resultaat:", dxf_writer_result)
        self.print_result("Project Drawing PDF Writer Engine resultaat:", drawing_pdf_result)
        self.print_result("Cost Estimate Engine resultaat:", cost_result)
        self.print_result("Planning Engine resultaat:", planning_result)
        self.print_result("Traffic & Parking Engine resultaat:", traffic_parking_result)
        self.print_result("Drainage & Sewerage Engine resultaat:", drainage_result)
        self.print_result("AERIUS / Stikstof Engine resultaat:", aerius_result)
        self.print_result("GIS / Map Engine resultaat:", gis_result)
        self.print_result("Quantity / BOQ Engine resultaat:", quantity_result)
        self.print_result("Validation & QA/QC Engine resultaat:", validation_result)
        self.print_result("Specification / Bestek Engine resultaat:", specification_result)
        self.print_result("Tender / Procurement Engine resultaat:", tender_result)
        self.print_result("Contract / Agreement Engine resultaat:", contract_result)
        self.print_result("Construction Execution Engine resultaat:", construction_execution_result)
        self.print_result("Site Monitoring / Progress Engine resultaat:", site_monitoring_result)
        self.print_result("As-Built / Oplever Engine resultaat:", as_built_result)
        self.print_result("Asset Management / Maintenance Engine resultaat:", asset_result)
        self.print_result("Sustainability / Climate Engine resultaat:", sustainability_result)
        self.print_result("Global Codes / Standards Engine resultaat:", codes_result)
        self.print_result("Autonomous Learning / Knowledge Engine resultaat:", learning_result)
        self.print_result("Runtime / Orchestration Engine resultaat:", runtime_result)
        self.print_result("Project CSV/Excel Export Engine resultaat:", csv_excel_result)
        self.print_result("Project XLSX Export Engine resultaat:", xlsx_result)
        self.print_result("Project File Writer / JSON Export Engine resultaat:", file_writer_result)
        self.print_result("Project Report Writer Engine resultaat:", report_writer_result)
        self.print_result("PDF/DOCX Report Export Engine resultaat:", pdf_docx_result)
        self.print_result("Project HTML Dashboard Export Engine resultaat:", html_dashboard_result)
        self.print_result("Project Index / Startpage Engine resultaat:", index_result)
        self.print_result("Project ZIP Engine resultaat:", zip_result)
        self.print_result("Project Run Log / Audit Trail Engine resultaat:", audit_result)
        self.print_result("Project Checksum / File Integrity Engine resultaat:", checksum_result)
        self.print_result("Project Version / Git Evidence Engine resultaat:", git_evidence_result)
        self.print_result("Finale Project ZIP Engine resultaat inclusief audit trail, file manifest en Git evidence:", final_zip_result)
        self.print_result("Digital Twin resultaat:", self.digital_twin.get_project_data())

        self.project_selector.run()
        self.project_config.run()
        self.project_storage.run()
        self.project_file_writer.run()
        self.project_report_writer.run()
        self.project_pdf_docx_writer.run()
        self.project_dxf_writer.run()
        self.project_drawing_pdf_writer.run()
        self.project_csv_excel_export.run()
        self.project_xlsx_export.run()
        self.project_html_dashboard_export.run()
        self.project_index_startpage.run()
        self.project_audit_trail.run()
        self.project_checksum.run()
        self.project_git_evidence.run()

        self.aaie.run()
        self.variant.run()
        self.geo.run()
        self.structural.run()
        self.permit.run()
        self.reporting.run()
        self.project_export.run()
        self.document_export.run()
        self.drawing_export.run()
        self.cad_export.run()
        self.cost.run()
        self.planning.run()
        self.traffic_parking.run()
        self.drainage_sewerage.run()
        self.aerius.run()
        self.gis_map.run()
        self.quantity.run()
        self.validation.run()
        self.specification.run()
        self.tender.run()
        self.contract.run()
        self.construction_execution.run()
        self.site_monitoring.run()
        self.as_built.run()
        self.asset_management.run()
        self.sustainability.run()
        self.global_codes.run()
        self.learning.run()
        self.runtime.run()
        self.project_zip.run()
        self.digital_twin.run()
        self.workflow.run()
        self.stee.run()

        print("\n=== PROJECTANALYSE GEREED ===")


if __name__ == "__main__":
    core = BAOEESCore()
    core.start_projectanalyse()