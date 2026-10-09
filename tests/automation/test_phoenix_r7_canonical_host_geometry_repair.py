from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from phoenix.design.tropical_residential.canonical_host_geometry import (
    finalize_canonical_host_geometry,
    validate_canonical_host_geometry,
)


class R7CanonicalHostGeometryTests(unittest.TestCase):
    def _latest_layout(self):
        repo=Path(__file__).resolve().parents[2]
        root=repo/"outputs"/"runtime"/"phase19_start_screen_bridge"
        files=sorted(
            root.rglob("real_spatial_layout.json"),
            key=lambda p:p.stat().st_mtime,
            reverse=True,
        )
        self.assertTrue(files)
        return json.loads(files[0].read_text(encoding="utf-8-sig"))

    def test_stale_runtime_layout_is_rederived_to_host_geometry(self):
        layout=self._latest_layout()
        finalize_canonical_host_geometry(layout)
        qa=validate_canonical_host_geometry(layout)
        self.assertTrue(qa["hard_pass"], qa["failures"])
        self.assertEqual(qa["failure_count"],0)

    def test_semantic_subsets_and_facades_are_explicit(self):
        layout=self._latest_layout()
        finalize_canonical_host_geometry(layout)
        self.assertEqual(set(layout["facades"]),{"N","E","S","W"})
        self.assertEqual(
            len(layout["windows"]),
            sum(1 for x in layout["openings"] if x["kind"]=="window"),
        )
        self.assertEqual(
            len(layout["doors"]),
            sum(1 for x in layout["openings"] if x["kind"]=="door"),
        )
        self.assertEqual(
            set(layout["opening_sides"]),
            {x["opening_id"] for x in layout["openings"]},
        )

    def test_finalization_is_idempotent(self):
        layout=self._latest_layout()
        finalize_canonical_host_geometry(layout)
        first=copy.deepcopy({
            "walls":layout["walls"],
            "openings":layout["openings"],
            "windows":layout["windows"],
            "doors":layout["doors"],
            "opening_sides":layout["opening_sides"],
            "facades":layout["facades"],
            "roof":layout["roof"],
        })
        finalize_canonical_host_geometry(layout)
        second={
            "walls":layout["walls"],
            "openings":layout["openings"],
            "windows":layout["windows"],
            "doors":layout["doors"],
            "opening_sides":layout["opening_sides"],
            "facades":layout["facades"],
            "roof":layout["roof"],
        }
        self.assertEqual(first,second)


if __name__=="__main__":
    unittest.main()
