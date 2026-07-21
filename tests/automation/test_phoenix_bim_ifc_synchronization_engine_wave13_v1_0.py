import json
from pathlib import Path
import tempfile
import unittest

from phoenix.adapters.bim_ifc_synchronization import (
    BIMIFCSynchronizationConfig,
    BIMIFCSynchronizationError,
    create_bim_ifc_synchronization_adapter,
)
from phoenix.adapters.foundation_bootstrap import (
    FoundationBootstrapConfig,
    create_foundation_bootstrap_adapter,
)
from phoenix.adapters.geotechnical_bootstrap import (
    GeotechnicalBootstrapConfig,
    SoilLayer,
    create_geotechnical_bootstrap_adapter,
)
from phoenix.adapters.gis_bootstrap import GISBootstrapConfig, create_gis_bootstrap_adapter
from phoenix.adapters.structural_analysis_bootstrap import (
    StructuralBootstrapConfig,
    StructuralElement,
    StructuralLoadCase,
    StructuralMaterial,
    create_structural_analysis_bootstrap_adapter,
)


class PhoenixBIMIFCSynchronizationTests(unittest.TestCase):
    def build_structural(self, directory):
        project_id = "PHX-W13-001"
        gis = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://wave13",
                output_directory=Path(directory) / "gis",
            )
        )(project_id=project_id, engine_id="gis", plan_fingerprint="gis-fp")
        geo = create_geotechnical_bootstrap_adapter(
            GeotechnicalBootstrapConfig(
                project_id=project_id,
                gis_artifact=gis.outputs[0],
                output_directory=Path(directory) / "geo",
                soil_layers=(
                    SoilLayer(
                        layer_id="L1",
                        top_level_m=0.0,
                        bottom_level_m=-2.0,
                        classification="sand",
                        friction_angle_deg=30.0,
                        source_reference="report://wave13",
                    ),
                ),
                allow_assumed_groundwater=True,
            )
        )(project_id=project_id, engine_id="geotechnical", plan_fingerprint="geo-fp")
        foundation = create_foundation_bootstrap_adapter(
            FoundationBootstrapConfig(
                project_id=project_id,
                geotechnical_artifact=geo.outputs[0],
                output_directory=Path(directory) / "foundation",
                use_phoenix_standard_strip_concept=True,
            )
        )(project_id=project_id, engine_id="foundation", plan_fingerprint="foundation-fp")
        structural = create_structural_analysis_bootstrap_adapter(
            StructuralBootstrapConfig(
                project_id=project_id,
                foundation_artifact=foundation.outputs[0],
                output_directory=Path(directory) / "structural",
                nodes={"N1": (0.0, 0.0, 0.0), "N2": (4.0, 0.0, 0.0)},
                materials=(
                    StructuralMaterial(
                        material_id="S",
                        material_type="steel",
                        grade="S355",
                        elastic_modulus_pa=200e9,
                    ),
                ),
                elements=(
                    StructuralElement(
                        element_id="E1",
                        element_type="truss",
                        material_id="S",
                        node_ids=("N1", "N2"),
                    ),
                ),
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="G",
                        load_type="dead",
                        description="Permanent action",
                    ),
                ),
            )
        )(project_id=project_id, engine_id="structural", plan_fingerprint="structural-fp")
        return structural.outputs[0]

    def write_design_artifact(self, directory, element_id="E1"):
        artifact = {
            "schema": "phoenix-steel-axial-design-results-v1.0",
            "project_id": "PHX-W13-001",
            "member_results": [
                {
                    "element_id": element_id,
                    "action_mode": "tension",
                    "utilization": 0.4,
                    "checks": {"member_passed": True},
                }
            ],
        }
        from hashlib import sha256
        raw = json.dumps(artifact, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        artifact["artifact_sha256"] = sha256(raw.encode("utf-8")).hexdigest()
        path = Path(directory) / "steel_design.json"
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return path

    def test_structural_model_maps_to_ifc_entities(self):
        with tempfile.TemporaryDirectory() as directory:
            structural = self.build_structural(directory)
            result = create_bim_ifc_synchronization_adapter(
                BIMIFCSynchronizationConfig(
                    project_id="PHX-W13-001",
                    structural_artifact=structural,
                    output_directory=Path(directory) / "bim",
                )
            )(project_id="PHX-W13-001", engine_id="bim_ifc_synchronization", plan_fingerprint="bim-fp")
            artifact = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertEqual(artifact["elements"][0]["ifc_entity"], "IfcMember")
            self.assertEqual(artifact["synchronization_summary"]["element_count"], 1)
            self.assertEqual(
                artifact["synchronization_summary"]["synchronization_status"],
                "ready_for_ifc_serialization",
            )

    def test_design_evidence_is_linked(self):
        with tempfile.TemporaryDirectory() as directory:
            structural = self.build_structural(directory)
            design = self.write_design_artifact(directory)
            result = create_bim_ifc_synchronization_adapter(
                BIMIFCSynchronizationConfig(
                    project_id="PHX-W13-001",
                    structural_artifact=structural,
                    design_artifacts=(design,),
                    output_directory=Path(directory) / "bim",
                )
            )(project_id="PHX-W13-001", engine_id="bim_ifc_synchronization", plan_fingerprint="bim-fp")
            artifact = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            evidence = artifact["elements"][0]["property_sets"]["Pset_PhoenixDesignEvidence"]
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["summary"]["utilization"], 0.4)

    def test_unresolved_design_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            structural = self.build_structural(directory)
            design = self.write_design_artifact(directory, element_id="UNKNOWN")
            adapter = create_bim_ifc_synchronization_adapter(
                BIMIFCSynchronizationConfig(
                    project_id="PHX-W13-001",
                    structural_artifact=structural,
                    design_artifacts=(design,),
                    output_directory=Path(directory) / "bim",
                )
            )
            with self.assertRaises(BIMIFCSynchronizationError):
                adapter(project_id="PHX-W13-001", engine_id="bim_ifc_synchronization", plan_fingerprint="bim-fp")

    def test_tampered_structural_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(self.build_structural(directory))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["nodes"]["N2"] = [99.0, 0.0, 0.0]
            path.write_text(json.dumps(data), encoding="utf-8")
            adapter = create_bim_ifc_synchronization_adapter(
                BIMIFCSynchronizationConfig(
                    project_id="PHX-W13-001",
                    structural_artifact=path,
                    output_directory=Path(directory) / "bim",
                )
            )
            with self.assertRaises(BIMIFCSynchronizationError):
                adapter(project_id="PHX-W13-001", engine_id="bim_ifc_synchronization", plan_fingerprint="bim-fp")

    def test_unsupported_ifc_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            structural = self.build_structural(directory)
            with self.assertRaises(BIMIFCSynchronizationError):
                create_bim_ifc_synchronization_adapter(
                    BIMIFCSynchronizationConfig(
                        project_id="PHX-W13-001",
                        structural_artifact=structural,
                        output_directory=Path(directory) / "bim",
                        ifc_schema_target="IFC2X3",
                    )
                )

    def test_binary_ifc_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            structural = self.build_structural(directory)
            result = create_bim_ifc_synchronization_adapter(
                BIMIFCSynchronizationConfig(
                    project_id="PHX-W13-001",
                    structural_artifact=structural,
                    output_directory=Path(directory) / "bim",
                )
            )(project_id="PHX-W13-001", engine_id="bim_ifc_synchronization", plan_fingerprint="bim-fp")
            artifact = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertFalse(artifact["ifc_exchange"]["binary_ifc_written"])
            self.assertTrue(artifact["claims_policy"]["binary_ifc_not_written"])

if __name__ == "__main__":
    unittest.main()
