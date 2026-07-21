import unittest
from phoenix.orchestration.autonomous_project_delivery import (
    DeliveryError, DesignVariant, StageStatus, create_project_state,
    dossier_manifest, ready_engines, select_variant, validate_variants,
)

class AutonomousProjectDeliveryTests(unittest.TestCase):
    def variants(self):
        return tuple(DesignVariant(f"V{i:02d}", f"Concept {i}", i / 10.0) for i in range(1, 11))

    def test_exactly_ten_variants(self):
        self.assertEqual(len(validate_variants(self.variants())), 10)

    def test_automatic_and_manual_selection(self):
        state = create_project_state("P1", "Ontwerp een appartementencomplex.", "kaart://locatie")
        self.assertEqual(select_variant(state, self.variants()).variant_id, "V10")
        self.assertEqual(select_variant(state, self.variants(), "V03").variant_id, "V03")

    def test_ready_engines_after_gis(self):
        state = create_project_state("P1", "Ontwerp.", "locatie")
        state.stage_status["gis"] = StageStatus.COMPLETE
        ready = ready_engines(state)
        self.assertIn("concept_generation", ready)
        self.assertIn("geotechnical", ready)
        self.assertIn("traffic", ready)

    def test_manifest_contract(self):
        state = create_project_state("P1", "Ontwerp.", "locatie")
        manifest = dossier_manifest(state)
        self.assertIn("structural_report", manifest["deliverables"])
        self.assertIn("bill_of_quantities", manifest["deliverables"])

    def test_invalid_count_fails(self):
        with self.assertRaises(DeliveryError):
            validate_variants(self.variants()[:9])

if __name__ == "__main__":
    unittest.main()
