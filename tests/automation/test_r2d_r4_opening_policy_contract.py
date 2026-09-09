import json
import unittest
from pathlib import Path

class PolicyContractTests(unittest.TestCase):
    def test_policy_has_hard_user_rules(self):
        p = Path('configs/phoenix/r2d_r4_opening_policy.json')
        data = json.loads(p.read_text(encoding='utf-8'))
        r = data['rules']
        self.assertTrue(r['windows_exterior_only'])
        self.assertTrue(r['exterior_windows_always_cyan'])
        self.assertTrue(r['exterior_doors_always_light_brown'])
        self.assertEqual(r['bathroom_minimum_exterior_window_count'], 1)
        self.assertEqual(r['minimum_rear_or_side_door_per_design'], 1)
        self.assertTrue(r['all_rooms_reachable_by_swing_or_sliding_door'])
        self.assertTrue(r['opening_ids_authoritative_across_2d_cad_3d'])
        self.assertTrue(r['construction_release_locked'])

if __name__ == '__main__':
    unittest.main()
