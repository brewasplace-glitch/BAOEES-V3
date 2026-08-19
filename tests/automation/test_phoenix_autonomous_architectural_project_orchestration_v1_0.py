from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.design.tropical_residential.project_orchestration import (
    RELEASE_STATUS,
    orchestrate_real_project_delivery,
)


class Variant:
    def __init__(self, variant_id: str):
        self.variant_id = variant_id
        self.strategy = "BALANCED"

    def to_dict(self):
        return {"variant_id": self.variant_id, "strategy": self.strategy}


class TestPhoenixAutonomousArchitecturalProjectOrchestration(unittest.TestCase):
    def test_project_scoped_delivery_contract(self):
        project = {"project_id": "PHOENIX-ORCH-TEST-001", "project_name": "Test"}
        variants = [Variant(x) for x in "ABCDE"]
        recommended = variants[-1]

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / project["project_id"]
            detv = project_dir / "results" / "generated_visual_media" / "blender_presentation"
            detv.mkdir(parents=True)

            authoritative_ifc = project_dir / "authoritative.ifc"
            authoritative_ifc.write_bytes(b"IFC" + b"x" * 4000)
            authoritative_blend = detv / "recommended_E.blend"
            authoritative_blend.write_bytes(b"BLEND" + b"x" * 2000)
            fcstd = project_dir / "recommended_E.FCStd"
            fcstd.write_bytes(b"FCSTD" + b"x" * 2000)

            canonical = {}
            for name in ("exterior_front", "exterior_rear", "bird_view", "interior_cutaway"):
                p = detv / f"{name}.png"
                p.write_bytes(b"PNG" + b"x" * 3000)
                canonical[name] = {
                    "file": str(p),
                    "animation": "APNG",
                    "frame_count": 5,
                }

            presentation = {
                "freecad_handoff": {"status": "PASS", "output": str(fcstd)},
                "variant_outputs": {x: {"status": "PASS"} for x in "ABCDE"},
            }
            (detv / "tropical_residential_presentation_manifest.json").write_text(
                json.dumps(presentation), encoding="utf-8"
            )

            media_summary = {
                "variant_count": 5,
                "render_count": 20,
                "recommended_variant_id": "E",
                "authoritative_ifc": str(authoritative_ifc),
                "authoritative_blend": str(authoritative_blend),
                "freecad_status": "PASS",
                "blender_status": "PASS",
                "blender_render_engine": "CYCLES",
                "blender_render_device": "CPU",
                "blender_cycles_cpu_proven": True,
                "detv_media_dir": str(detv),
                "detv_canonical": canonical,
                "detv_core_player_modified": False,
                "release_status": RELEASE_STATUS,
            }

            with patch(
                "phoenix.design.tropical_residential.project_orchestration.generate_variants",
                return_value=variants,
            ), patch(
                "phoenix.design.tropical_residential.project_orchestration.select_balanced",
                return_value=recommended,
            ), patch(
                "phoenix.design.tropical_residential.project_orchestration.generate_tropical_real_3d_detv_package",
                return_value=media_summary,
            ) as pipeline:
                result = orchestrate_real_project_delivery(project, root, quick_smoke=True)

            pipeline.assert_called_once()
            self.assertEqual(result.recommended_variant_id, "E")
            self.assertTrue(Path(result.manifest_path).is_file())
            self.assertTrue(Path(result.evidence_json_path).is_file())
            self.assertTrue(Path(result.summary_md_path).is_file())

            manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
            self.assertEqual(manifest["variant_order"], list("ABCDE"))
            self.assertEqual(manifest["recommended_variant_id"], "E")
            self.assertTrue(manifest["governance"]["production_locked"])
            self.assertTrue(manifest["governance"]["for_construction_locked"])

    def test_release_remains_locked(self):
        self.assertEqual(RELEASE_STATUS, "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
