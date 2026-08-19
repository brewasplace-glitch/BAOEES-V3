from __future__ import annotations

import binascii
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from phoenix.design.tropical_residential.apng_writer import inspect_apng, write_apng
from phoenix.design.tropical_residential.freecad_bridge import _build_freecad_python_command
from phoenix.design.tropical_residential.tropical_3d_detv_pipeline import VIEWS


ROOT = Path(__file__).resolve().parents[2]


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(kind)
    crc = binascii.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",crc)


def _tiny_png(path: Path, rgba: tuple[int,int,int,int]) -> None:
    width,height=2,2
    raw=b"".join(
        b"\x00"+bytes(rgba)*width
        for _ in range(height)
    )
    ihdr=struct.pack(">IIBBBBB",width,height,8,6,0,0,0)
    data=b"\x89PNG\r\n\x1a\n"+_chunk(b"IHDR",ihdr)+_chunk(b"IDAT",zlib.compress(raw))+_chunk(b"IEND",b"")
    path.write_bytes(data)


class TestTropicalResidentialReal3dDetv(unittest.TestCase):
    def test_freecad_bundled_python_command(self):
        cmd=_build_freecad_python_command(
            r"C:\Program Files\FreeCAD 1.1\bin\python.exe",
            Path("bridge.py"),
            Path("layout.json"),
            Path("out.FCStd"),
        )
        self.assertTrue(cmd[0].lower().endswith("python.exe"))
        self.assertEqual(cmd[-3:],["bridge.py","layout.json","out.FCStd"])

    def test_freecad_primary_is_bundled_python_with_cmd_fallback(self):
        source=(ROOT/"phoenix/design/tropical_residential/freecad_bridge.py").read_text(encoding="utf-8")
        self.assertIn("BUNDLED_FREECAD_PYTHON",source)
        self.assertIn("FREECADCMD_FALLBACK",source)
        self.assertIn("PHOENIX_FREECAD_HANDOFF_OK",source)
        self.assertIn("_discover_freecad_python",source)

    def test_apng_five_variant_frames(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            frames=[]
            colors=[
                (220,80,80,255),(80,180,100,255),(80,120,220,255),
                (220,170,70,255),(150,100,200,255)
            ]
            for i,c in enumerate(colors):
                p=root/f"{i}.png"
                _tiny_png(p,c)
                frames.append(p)
            out=root/"animated.png"
            ev=write_apng(frames,out,delay_ms=500)
            self.assertTrue(ev["is_apng"])
            self.assertEqual(ev["frame_count"],5)
            self.assertEqual(ev["frame_control_count"],5)
            self.assertEqual(inspect_apng(out)["frame_count"],5)

    def test_existing_detv_four_file_contract_is_preserved(self):
        self.assertEqual(
            [x[1] for x in VIEWS],
            [
                "phoenix_exterior_front.png",
                "phoenix_exterior_rear.png",
                "phoenix_bird_view.png",
                "phoenix_interior_cutaway.png",
            ],
        )

    def test_blender_headless_renderer_is_cycles_cpu(self):
        script=(ROOT/"phoenix/design/tropical_residential/blender_tropical_scene_script.py").read_text(encoding="utf-8")
        self.assertIn('scene.render.engine = "CYCLES"',script)
        self.assertIn('scene.cycles.device = "CPU"',script)
        self.assertNotIn('scene.render.engine = "BLENDER_EEVEE_NEXT"',script)
        self.assertIn("PHOENIX_BLENDER_RENDER_ENGINE",script)
        self.assertIn("PHOENIX_BLENDER_RENDER_DEVICE",script)

    def test_blender_scene_has_real_tropical_features(self):
        script=(ROOT/"phoenix/design/tropical_residential/blender_tropical_scene_script.py").read_text(encoding="utf-8")
        for token in (
            "build_wall_with_openings",
            "gable_roof",
            "hip_roof",
            "shed_roof",
            "Veranda_Roof",
            "interior_cutaway",
            "PHOENIX_VARIANT_LABEL",
            "bpy.ops.render.render",
            "bpy.ops.wm.save_as_mainfile",
        ):
            self.assertIn(token,script)

    def test_pipeline_does_not_patch_detv_core(self):
        policy=(ROOT/"configs/phoenix/tropical_residential_real_3d_detv_v1_0.json").read_text(encoding="utf-8")
        self.assertIn('"core_player_patch": false',policy.lower())
        pipeline=(ROOT/"phoenix/design/tropical_residential/tropical_3d_detv_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("existing_single_visual_authority_preserved",pipeline)

    def test_release_stays_locked(self):
        pipeline=(ROOT/"phoenix/design/tropical_residential/tropical_3d_detv_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",pipeline)


if __name__=="__main__":
    unittest.main(verbosity=2)
