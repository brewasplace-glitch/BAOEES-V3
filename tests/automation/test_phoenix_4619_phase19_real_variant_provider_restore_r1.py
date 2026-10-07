from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.local_app.integrated_project_bridge import OfficialStartIntegratedProjectBridge

ROOT = Path(__file__).resolve().parents[2]


class Phase19RealVariantProviderRestoreR1(unittest.TestCase):
    def bridge(self, root: Path) -> OfficialStartIntegratedProjectBridge:
        value = object.__new__(OfficialStartIntegratedProjectBridge)
        value.repository = root
        value.output_root = root / "outputs/runtime/phase19_start_screen_bridge"
        return value

    def fixture(self, root: Path):
        batch = "20261007T210000Z_cafebabe"
        folder = root / "inputs/runtime/official_start_v3_uploads" / batch
        folder.mkdir(parents=True)
        raw = b"real-spatial-variant-provider"
        (folder / "terrain.png").write_bytes(raw)
        (folder / "upload_manifest.json").write_text(json.dumps({
            "batch_id": batch,
            "file_count": 1,
            "files": [{"name": "terrain.png", "size_bytes": len(raw)}],
        }), encoding="utf-8")

        for relative in (
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"status":"REFERENCE_ONLY"}\n', encoding="utf-8")

        return {
            "session_id": "PHX-R31-REAL-VARIANTS",
            "project_type": "BOUW",
            "project_mode": "autonomous",
            "brief": "Urban villa 300 m2, 2 verdiepingen, 3 slaapkamers, garage voor 2 wagens.",
            "location_reference": "Perceel 314, Heliosstraat / Plutostraat",
            "upload_batch": batch,
            "desired_outputs": ["drawings", "ifc", "digital_twin"],
        }

    def test_real_spatial_provider_generates_five_distinct_layouts_and_ifc(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.bridge(root).prepare_concept_inputs(
                self.fixture(root), "P19-0123456789ABCDEF"
            )

            self.assertEqual(len(result["variant_files"]), 5)
            self.assertEqual(
                [item["variant_id"] for item in result["variant_files"]],
                list("ABCDE"),
            )

            hashes = []
            for item in result["variant_files"]:
                self.assertEqual(
                    item["provider"],
                    "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
                )
                svg = root / item["svg_path"]
                layout_path = root / item["json_path"]
                ifc = root / item["ifc_path"]

                self.assertTrue(svg.is_file(), svg)
                self.assertTrue(layout_path.is_file(), layout_path)
                self.assertTrue(ifc.is_file(), ifc)
                self.assertGreater(ifc.stat().st_size, 3000)

                self.assertIn(
                    "REAL SPATIAL CONCEPT LAYOUT",
                    svg.read_text(encoding="utf-8"),
                )

                layout = json.loads(layout_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    layout["governance"]["layout_status"],
                    "REAL_GEOMETRIC_CONCEPT_LAYOUT",
                )
                self.assertGreater(len(layout["rooms"]), 5)
                self.assertGreater(len(layout["walls"]), 4)
                self.assertGreater(len(layout["openings"]), 2)
                self.assertTrue(layout["geometry_validation"]["valid"])
                hashes.append(item["topology_sha256"])

            self.assertEqual(len(set(hashes)), 5)

            manifest = json.loads(
                (root / result["manifest_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                manifest["variant_provider"],
                "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
            )
            self.assertEqual(manifest["unique_topology_count"], 5)

            real_manifest = json.loads(
                (root / result["real_spatial_manifest_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(real_manifest["variant_count"], 5)
            self.assertEqual(real_manifest["unique_topology_count"], 5)
            self.assertEqual(real_manifest["variant_order"], list("ABCDE"))

    def test_source_no_longer_exposes_foundation_svg_as_primary(self):
        source = (
            ROOT / "phoenix/local_app/integrated_project_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "PHOENIX_4_6_19_PHASE19_REAL_VARIANT_PROVIDER_RESTORE_R1",
            source,
        )
        self.assertIn('"variant_files": real_variant_files', source)
        self.assertIn("PHASE19_REAL_VARIANT_DISTINCTNESS_DENY", source)


if __name__ == "__main__":
    unittest.main()
