import copy
import unittest

from phoenix.architecture.r2d_r4_opening_rule_engine import (
    apply_rules,
    WINDOW_COLOR,
    EXTERIOR_DOOR_COLOR,
    Segment,
    _safe_center_on_segment,
    _spans_overlap,
)


def fixture():
    # Rectangle 12 x 8, front = south (y=0), rear = north.
    # Ground: entree/trap/toilet lower strip, woonkamer/keuken/badkamer upper.
    rooms = [
        ["entree", 0, 0, 3, 2],
        ["trap", 3, 0, 3, 2],
        ["toilet", 6, 0, 2, 2],
        ["techniek", 8, 0, 4, 2],
        ["woonkamer", 0, 2, 6, 6],
        ["keuken_eetruimte", 6, 2, 4, 6],
        ["badkamer_hoof", 10, 2, 2, 6]
    ]
    return {
        "schema": "TEST",
        "variants": {
            "A": {
                "rooms": {"ground": rooms, "upper": []},
                "windows": [
                    # legal living exterior window west
                    {"opening_id":"A-W01","opening_type":"WINDOW","kind":"window","level":"ground","storey":0,"source_room":"woonkamer","orientation":"V","center_xy":[0,5],"width_m":1.4},
                    # illegal internal window on living/kitchen boundary
                    {"opening_id":"A-W02","opening_type":"WINDOW","kind":"window","level":"ground","storey":0,"source_room":"woonkamer","orientation":"V","center_xy":[6,5],"width_m":1.2}
                ],
                "doors_internal_ground": [
                    {"opening_id":"A-DG01","opening_type":"DOOR","kind":"door","level":"ground","storey":0,"from":"entree","to":"trap","orientation":"V","center_xy":[3,1],"width_m":0.9},
                    # open passage must be converted to a real door for required link
                    {"opening_id":"A-DG02","opening_type":"OPEN_PASSAGE","kind":"open_passage","level":"ground","storey":0,"from":"woonkamer","to":"keuken_eetruimte","orientation":"V","center_xy":[6,5],"width_m":1.2},
                    # duplicate door
                    {"opening_id":"A-DG03","opening_type":"DOOR","kind":"door","level":"ground","storey":0,"from":"entree","to":"trap","orientation":"V","center_xy":[3,1.02],"width_m":0.9}
                ],
                "doors_internal_upper": [],
                "doors_external": [
                    {"opening_id":"A-DE01","opening_type":"DOOR","kind":"front_door","level":"ground","storey":0,"from":"OUTSIDE","to":"entree","room":"entree","orientation":"H","center_xy":[1.5,0],"width_m":1.0}
                ],
                "openings": []
            }
        }
    }


class R2DR4RuleEngineTests(unittest.TestCase):
    def test_autorepair_contract(self):
        repaired, report = apply_rules(fixture())
        v = repaired["variants"]["A"]
        ids = {o["opening_id"] for o in v["openings"]}
        self.assertEqual(len(ids), len(v["openings"]))
        self.assertFalse(any(w.get("center_xy") == [6,5] for w in v["windows"]))  # internal window geometry removed
        self.assertTrue(any(a.get("action")=="REMOVE_INTERNAL_OR_NONBOUNDARY_WINDOW" for a in report["actions"]))
        self.assertTrue(any(w.get("source_room") == "badkamer_hoof" for w in v["windows"]))
        self.assertTrue(any(d.get("kind") in {"rear_garden_door","side_service_door"} for d in v["doors_external"]))
        req = [d for d in v["doors_internal_ground"] if frozenset((d.get("from"),d.get("to"))) == frozenset(("woonkamer","keuken_eetruimte"))]
        self.assertTrue(req)
        self.assertTrue(all(d.get("kind") != "open_passage" for d in req))
        self.assertTrue(all(w["render_style"]["stroke"] == WINDOW_COLOR for w in v["windows"]))
        self.assertTrue(all(d["render_style"]["stroke"] == EXTERIOR_DOOR_COLOR for d in v["doors_external"]))
        self.assertEqual(report["status"], "PASS_AUTOREPAIRED_MACHINE_RULES_VISUAL_REVIEW_REQUIRED")
        self.assertEqual(report["variants"]["A"]["unreachable_ground"], [])

    def test_overlapping_different_pair_doors_are_relocated(self):
        m=fixture()
        # Add a different room-pair door nearly on top of the existing living/kitchen opening.
        m["variants"]["A"]["doors_internal_ground"].append({
            "opening_id":"A-DG09","opening_type":"DOOR","kind":"door","level":"ground","storey":0,
            "from":"keuken_eetruimte","to":"badkamer_hoof","orientation":"V","center_xy":[10,5],"width_m":.9
        })
        repaired,report=apply_rules(m)
        self.assertTrue(any(a.get("action") in {"RELOCATE_OVERLAPPING_DOOR","ADD_CIRCULATION_DOOR"} for a in report["actions"]))
        self.assertEqual(report["variants"]["A"]["unreachable_ground"],[])


    def test_cross_storey_opening_does_not_block_upper_window_capacity(self):
        seg = Segment("H", 0.0, 0.0, 2.0)
        ground = {
            "opening_id": "C-DE99", "opening_type": "DOOR", "kind": "front_door",
            "level": "ground", "storey": 0, "orientation": "H",
            "center_xy": [1.0, 0.0], "width_m": 1.0,
        }
        self.assertIsNotNone(_safe_center_on_segment(seg, 0.8, [ground], margin=0.15, level="upper"))
        self.assertIsNone(_safe_center_on_segment(seg, 0.8, [ground], margin=0.15, level="ground"))

    def test_cross_storey_geometry_is_not_an_overlap(self):
        ground = {
            "opening_id": "X-DG01", "level": "ground", "storey": 0,
            "orientation": "H", "center_xy": [1.0, 0.0], "width_m": 1.0,
        }
        upper = {
            "opening_id": "X-W01", "level": "upper", "storey": 1,
            "orientation": "H", "center_xy": [1.0, 0.0], "width_m": 1.0,
        }
        self.assertFalse(_spans_overlap(ground, upper))

    def test_production_kind_only_schema_is_normalized_before_downstream_cad(self):
        m = fixture()
        v = m["variants"]["A"]
        # Mirror the production structured-collection shape that triggered R2 host authority:
        # kind is present but opening_type is absent.
        for key in ("windows", "doors_internal_ground", "doors_internal_upper", "doors_external"):
            for rec in v.get(key, []):
                rec.pop("opening_type", None)
        repaired, report = apply_rules(m)
        out = repaired["variants"]["A"]["openings"]
        self.assertTrue(out)
        self.assertTrue(all(o.get("opening_type") in {"WINDOW", "DOOR", "OPEN_PASSAGE"} for o in out))
        self.assertTrue(all(o.get("opening_type") == "WINDOW" for o in repaired["variants"]["A"]["windows"]))
        self.assertTrue(all(o.get("opening_type") == "DOOR" for o in repaired["variants"]["A"]["doors_external"]))
        self.assertEqual(report["status"], "PASS_AUTOREPAIRED_MACHINE_RULES_VISUAL_REVIEW_REQUIRED")

    def test_bathroom_without_exterior_boundary_fails_closed(self):
        m = fixture()
        # Put bathroom in a fully internal location by replacing rooms with a ring around it.
        m["variants"]["A"]["rooms"]["ground"] = [
            ["entree",0,0,3,2], ["trap",3,0,3,2], ["toilet",6,0,2,2], ["techniek",8,0,4,2],
            ["woonkamer",0,2,4,6], ["keuken_eetruimte",8,2,4,6],
            ["badkamer_hoof",4,2,4,2], ["berging",4,4,4,4]
        ]
        with self.assertRaises(RuntimeError):
            apply_rules(m)


if __name__ == "__main__":
    unittest.main()
