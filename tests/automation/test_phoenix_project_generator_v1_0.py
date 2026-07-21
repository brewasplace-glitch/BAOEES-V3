import unittest

from phoenix.project_generator import (
    GenerationError,
    ProjectBrief,
    VariantWeights,
    generate_project_variants,
    rank_project_variants,
    select_project_variant,
    variant_presentation_queue,
)


class PhoenixProjectGeneratorTests(unittest.TestCase):
    def brief(self):
        return ProjectBrief(
            project_id="PHX-APT-001",
            instruction="Ontwerp een appartementencomplex op deze locatie.",
            location_reference="kaart://testlocatie",
            target_units=80,
            maximum_floors=8,
        )

    def test_generates_exactly_ten_unique_variants(self):
        variants = generate_project_variants(self.brief())
        self.assertEqual(len(variants), 10)
        self.assertEqual(len({v.variant_id for v in variants}), 10)
        self.assertEqual(len({v.fingerprint for v in variants}), 10)

    def test_generation_is_deterministic(self):
        first = generate_project_variants(self.brief())
        second = generate_project_variants(self.brief())
        self.assertEqual(first, second)

    def test_ranking_is_descending(self):
        ranked = rank_project_variants(generate_project_variants(self.brief()))
        self.assertEqual(
            [v.weighted_score for v in ranked],
            sorted([v.weighted_score for v in ranked], reverse=True),
        )

    def test_automatic_and_manual_selection(self):
        variants = generate_project_variants(self.brief())
        automatic = select_project_variant(variants)
        manual = select_project_variant(variants, "V04")
        self.assertEqual(manual.variant_id, "V04")
        self.assertIn(automatic, variants)

    def test_presentation_queue_contains_ten_cards(self):
        queue = variant_presentation_queue(generate_project_variants(self.brief()))
        self.assertEqual(len(queue), 10)
        self.assertEqual(queue[0]["position"], 1)
        self.assertIn("weighted_score", queue[0])

    def test_invalid_weights_are_rejected(self):
        with self.assertRaises(GenerationError):
            generate_project_variants(
                self.brief(),
                VariantWeights(cost=0.5, permit_probability=0.5),
            )


if __name__ == "__main__":
    unittest.main()
