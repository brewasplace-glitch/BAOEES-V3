from pprint import pprint

from baoees.document_export_engine.main import DocumentExportEngine
from baoees.project_analyzer.main import ProjectAnalyzer
from baoees.aaie.main import AAIEEngine
from baoees.variant_engine.main import VariantEngine
from baoees.geo_engine.main import GeoEngine
from baoees.structural_engine.main import StructuralEngine
from baoees.permit_engine.main import PermitEngine
from baoees.reporting_engine.main import ReportingEngine
from baoees.project_export_engine.main import ProjectExportEngine
from baoees.document_export_engine.main import DocumentExportEngine
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
        self.project_zip.run()
        self.digital_twin.run()
        self.workflow.run()
        self.stee.run()

        print("\n=== PROJECTANALYSE GEREED ===")


if __name__ == "__main__":
    core = BAOEESCore()
    core.start_projectanalyse()