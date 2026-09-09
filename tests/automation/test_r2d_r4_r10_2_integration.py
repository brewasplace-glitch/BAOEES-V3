import unittest
from phoenix.architecture.r10_2_optimizer import refine_variant

class R10R2DR4IntegrationTests(unittest.TestCase):
    def test_every_variant_declares_permanent_opening_gate(self):
        for code in 'ABCDE':
            d=refine_variant(code,{})
            g=d['r10_2_guidance']['opening_rule_engine']
            self.assertTrue(g['required_before_cad_or_render'])
            self.assertTrue(g['windows_exterior_only'])
            self.assertEqual(g['bathroom_minimum_exterior_window_count'],1)
            self.assertEqual(g['minimum_rear_or_side_door_per_design'],1)
            self.assertTrue(g['all_rooms_reachable_by_swing_or_sliding_door'])
            self.assertTrue(g['opening_ids_authoritative_across_2d_cad_3d'])
            self.assertIn('r2d_r4_permanent_opening_rule_engine_required',d['refinement_tags'])

if __name__=='__main__': unittest.main()
