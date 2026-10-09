
from __future__ import annotations
import unittest

from phoenix.autonomy.local_material_supply_intelligence import (
    _explicit_project_roof_material_override,
    derive_material_requirements,
)

class ExplicitRoofMaterialRequirementOverrideTests(unittest.TestCase):
    def profile(self):
        return {"assumptions":{
            "default_wall_material":"masonry_candidate",
            "default_column_material":"reinforced_concrete_candidate",
            "default_slab_material":"reinforced_concrete_candidate",
            "default_beam_material":"reinforced_concrete_candidate",
            "default_roof_material":"timber_candidate",
        }}

    def test_metal_tube_truss_overrides_generic_timber_hypothesis(self):
        brief=("Plat dak met metalen buisvakwerkspanten. "
               "Constructiemodules 3x6 m en 2x6 m. "
               "Gebruik beton, staal, metselwerk en hout waar nuttig.")

        resolved,evidence=_explicit_project_roof_material_override(
            structural_profile=self.profile(),
            project_context={},
            manifest={"_project_session_for_material_resolution":{"brief":brief}},
        )

        self.assertEqual(
            resolved["assumptions"]["default_roof_material"],
            "steel_tube_truss_candidate",
        )
        self.assertEqual(
            evidence["basis"],
            "EXPLICIT_PROJECT_ROOF_STRUCTURE_REQUIREMENT",
        )
        self.assertFalse(evidence["member_size_inferred"])
        self.assertFalse(evidence["steel_grade_inferred"])

        req=derive_material_requirements(
            project_id="PLUTOSTRAAT",
            architectural_model={"building":{"type":"house"}},
            structural_profile=resolved,
        )
        roof=[x for x in req["requirements"] if x["element_role"]=="roof_structure"]

        self.assertEqual(len(roof),1)
        self.assertEqual(roof[0]["material_family"],"structural_steel_section")
        self.assertEqual(
            roof[0]["requirement_id"],
            "REQ-ROOF-STRUCTURE-STRUCTURAL-STEEL-SECTION",
        )

    def test_generic_wood_clause_does_not_override_by_itself(self):
        resolved,evidence=_explicit_project_roof_material_override(
            structural_profile=self.profile(),
            project_context={},
            manifest={"brief":"Gebruik beton, staal, metselwerk en hout waar nuttig."},
        )

        self.assertIsNone(evidence)
        self.assertEqual(
            resolved["assumptions"]["default_roof_material"],
            "timber_candidate",
        )

    def test_conflicting_explicit_roof_materials_fail_closed(self):
        resolved,evidence=_explicit_project_roof_material_override(
            structural_profile=self.profile(),
            project_context={},
            manifest={"brief":"Dakspanten in staal; roof truss in structural timber."},
        )

        self.assertEqual(evidence["status"],"CONFLICT")
        self.assertEqual(
            resolved["assumptions"]["default_roof_material"],
            "timber_candidate",
        )

if __name__=="__main__":
    unittest.main()
