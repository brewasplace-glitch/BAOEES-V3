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

        digital_twin_result = self.digital_twin.create_project_twin(
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
        self.project_zip.run()
        self.digital_twin.run()
        self.workflow.run()
        self.stee.run()

        print("\n=== PROJECTANALYSE GEREED ===")


if __name__ == "__main__":
    core = BAOEESCore()
    core.start_projectanalyse()