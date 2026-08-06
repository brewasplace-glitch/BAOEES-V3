from __future__ import annotations

import unittest
from pathlib import Path

from phoenix.autonomy.material_certification_engineering_mode import (
    continue_cost_calculation_with_unresolved_prices,
    split_cost_blockers_for_continuation,
)

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / 'phoenix' / 'autonomy' / 'session_adapters.py'


class CostRuntimeContinuationTests(unittest.TestCase):
    def test_current_local_price_gap_is_unresolved_not_blocking(self):
        hard, unresolved = split_cost_blockers_for_continuation([
            {'reason': 'CURRENT_LOCAL_MARKET_PRICE_DATA_REQUIRED', 'message': 'missing'}
        ])
        self.assertEqual(hard, [])
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]['reason'], 'PRICE_EVIDENCE_UNRESOLVED')
        self.assertFalse(unresolved[0]['price_fabricated'])

    def test_stale_and_currency_mismatch_are_unresolved_not_fabricated(self):
        hard, unresolved = split_cost_blockers_for_continuation([
            {'reason': 'LOCAL_MARKET_PRICE_DATA_STALE'},
            {'reason': 'LOCAL_MARKET_PRICE_CURRENCY_MISMATCH'},
        ])
        self.assertEqual(hard, [])
        self.assertEqual(len(unresolved), 2)
        self.assertTrue(all(x['price_fabricated'] is False for x in unresolved))

    def test_invalid_quantity_remains_blocking(self):
        calc = {'status': 'BLOCKED', 'items': [], 'blockers': [{'reason': 'INVALID_QUANTITY'}]}
        normalized, should_block = continue_cost_calculation_with_unresolved_prices(calc)
        self.assertTrue(should_block)
        self.assertEqual(normalized['status'], 'BLOCKED')

    def test_missing_quantity_price_match_becomes_partial_estimate(self):
        calc = {
            'status': 'BLOCKED',
            'items': [{'item_code': 'A', 'line_total': 25.0}],
            'total': 25.0,
            'blockers': [{'reason': 'QUANTITY_PRICE_MATCH_REQUIRED', 'item_code': 'B'}],
        }
        normalized, should_block = continue_cost_calculation_with_unresolved_prices(calc)
        self.assertFalse(should_block)
        self.assertEqual(normalized['status'], 'PARTIAL_UNRESOLVED_PRICES')
        self.assertEqual(normalized['total'], 25.0)
        self.assertEqual(normalized['blockers'], [])
        self.assertFalse(normalized['price_fabricated'])
        self.assertEqual(len(normalized['unresolved_price_evidence']), 1)

    def test_live_session_adapter_has_runtime_continuation_patch_and_runner_rebind(self):
        text = SESSION.read_text(encoding='utf-8-sig')
        self.assertIn('PHOENIX_COST_PRICE_RUNTIME_CONTINUATION_FIXED_R4', text)
        self.assertIn('_phoenix_split_cost_blockers(market.blockers)', text)
        self.assertIn('_phoenix_continue_cost_calculation(calc)', text)
        self.assertIn('RUNNERS["cost_planning"] = run_cost_planning', text)
        self.assertIn('PRICE_EVIDENCE_UNRESOLVED_ESTIMATE_CONTINUES', text)


if __name__ == '__main__':
    unittest.main()
