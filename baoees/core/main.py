from pprint import pprint

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
from baoees.project_zip_engine.main import ProjectZipEngine
from baoees.digital_twin.main import DigitalTwin
from baoees.workflow_engine.main import WorkflowEngine
from baoees.stee.main import STEEEngine


class BAOEESCore:

    def __init__(self):
        print("BAOEES Core gestart")

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
        self.project_zip = ProjectZipEngine()
        self.digital_twin = DigitalTwin()
        self.workflow = WorkflowEngine()
        self.stee = STEEEngine()

    def start_projectanalyse(self):

        print("\n=== START PROJECTANALYSE ===\n")

        project_result = self.project_analyzer.analyze(
            project_name="Plutostraat met BAOEES V3",
            project_description="Vrijstaande woning met fundering, constructie, geotechniek en SketchUp-integratie.",
            location="Plutostraat, Paramaribo",
            country="Suriname",
            project_type="Bouw"
        )

        print("Project Analyzer resultaat:")
        pprint(project_result)
        print("")

        aaie_result = self.aaie.infer_missing_parameters(project_result)

        print("AAIE resultaat:")
        pprint(aaie_result)
        print("")

        variant_result = self.variant.generate_variants(
            project_result=project_result,
            aaie_result=aaie_result
        )

        print("Variant Engine resultaat:")
        pprint(variant_result)
        print("")

        geo_result = self.geo.analyze_geotechnics(
            project_result=project_result,
            aaie_result=aaie_result
        )

        print("Geo Engine resultaat:")
        pprint(geo_result)
        print("")

        structural_result = self.structural.analyze_structure(
            project_result=project_result,
            geo_result=geo_result,
            aaie_result=aaie_result
        )

        print("Structural Engine resultaat:")
        pprint(structural_result)
        print("")

        permit_result = self.permit.prepare_permit_strategy(
            project_result=project_result,
            aaie_result=aaie_result,
            geo_result=geo_result,
            structural_result=structural_result,
            variant_result=variant_result
        )

        print("Permit Engine resultaat:")
        pprint(permit_result)
        print("")

        self.digital_twin.create_project_twin(
            project_result=project_result,
            aaie_result=aaie_result
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

        zip_result = self.project_zip.create_project_zip(
            export_result=export_result
        )

        self.digital_twin.add_object(
            object_type="project_zip",
            name="BAOEES Project ZIP Engine zipbestand",
            data=zip_result
        )

        print("STEE resultaat:")
        pprint(stee_result)
        print("")

        print("Workflow Engine resultaat:")
        pprint(workflow_result)
        print("")

        print("Reporting Engine resultaat:")
        pprint(reporting_result)
        print("")

        print("Project Export Engine resultaat:")
        pprint(export_result)
        print("")

        print("PDF/DOCX Export Engine resultaat:")
        pprint(document_result)
        print("")

        print("Drawing Export Engine resultaat:")
        pprint(drawing_result)
        print("")

        print("CAD/DXF Export Engine resultaat:")
        pprint(cad_result)
        print("")

        print("Cost Estimate Engine resultaat:")
        pprint(cost_result)
        print("")

        print("Planning Engine resultaat:")
        pprint(planning_result)
        print("")

        print("Traffic & Parking Engine resultaat:")
        pprint(traffic_parking_result)
        print("")

        print("Drainage & Sewerage Engine resultaat:")
        pprint(drainage_result)
        print("")

        print("AERIUS / Stikstof Engine resultaat:")
        pprint(aerius_result)
        print("")

        print("GIS / Map Engine resultaat:")
        pprint(gis_result)
        print("")

        print("Quantity / BOQ Engine resultaat:")
        pprint(quantity_result)
        print("")

        print("Validation & QA/QC Engine resultaat:")
        pprint(validation_result)
        print("")

        print("Specification / Bestek Engine resultaat:")
        pprint(specification_result)
        print("")

        print("Tender / Procurement Engine resultaat:")
        pprint(tender_result)
        print("")

        print("Contract / Agreement Engine resultaat:")
        pprint(contract_result)
        print("")

        print("Construction Execution Engine resultaat:")
        pprint(construction_execution_result)
        print("")

        print("Site Monitoring / Progress Engine resultaat:")
        pprint(site_monitoring_result)
        print("")

        print("As-Built / Oplever Engine resultaat:")
        pprint(as_built_result)
        print("")

        print("Asset Management / Maintenance Engine resultaat:")
        pprint(asset_result)
        print("")

        print("Sustainability / Climate Engine resultaat:")
        pprint(sustainability_result)
        print("")

        print("Global Codes / Standards Engine resultaat:")
        pprint(codes_result)
        print("")

        print("Autonomous Learning / Knowledge Engine resultaat:")
        pprint(learning_result)
        print("")

        print("Project ZIP Engine resultaat:")
        pprint(zip_result)
        print("")

        print("Digital Twin resultaat:")
        pprint(self.digital_twin.get_project_data())
        print("")

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
        self.project_zip.run()
        self.digital_twin.run()
        self.workflow.run()
        self.stee.run()

        print("\n=== PROJECTANALYSE GEREED ===")


if __name__ == "__main__":
    core = BAOEESCore()
    core.start_projectanalyse()