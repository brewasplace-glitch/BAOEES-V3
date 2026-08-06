from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'tests' / 'automation' / 'test_phoenix_project_context_structural_profile_drawing_production_v1_0.py'
NEW_NAME = 'test_09_permit_and_cost_consume_context_and_cost_continues_with_unresolved_price_evidence'


def target_method_text(text: str) -> str:
    tree = ast.parse(text)
    node = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == NEW_NAME)
    lines = text.splitlines(keepends=True)
    return ''.join(lines[node.lineno - 1:node.end_lineno])


class CostContinuationLegacyContractMigrationTests(unittest.TestCase):
    def test_legacy_blocking_contract_is_fully_migrated(self):
        text = TARGET.read_text(encoding='utf-8')
        self.assertIn(NEW_NAME, text)
        method = target_method_text(text)
        self.assertNotIn('run_adapter("cost_planning",repo,sf,ws,cost_out),10', method)
        self.assertNotIn('blocked["status"],"BLOCKED_INPUT"', method)
        self.assertNotIn('material_blocked["status"],"BLOCKED_INPUT"', method)
        self.assertGreaterEqual(method.count('run_adapter("cost_planning",repo,sf,ws,cost_out),0'), 3)
        self.assertIn('cost_input["price_evidence_status"],"UNRESOLVED"', method)
        self.assertIn('cost_input["price_evidence_status"],"CONFIRMED"', method)
        self.assertIn('price_fabricated', method)
        self.assertIn('[PHOENIX_MATERIAL_CERTIFICATION_MODE=UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED]', method)

    def test_new_material_contract_still_forbids_price_fabrication(self):
        module = (ROOT / 'phoenix' / 'autonomy' / 'material_certification_engineering_mode.py').read_text(encoding='utf-8')
        self.assertIn('PRICE_EVIDENCE_UNRESOLVED', module)
        self.assertIn('PARTIAL_UNRESOLVED_PRICES', module)
        self.assertNotIn('FABRICATE_PRICE', module)


if __name__ == '__main__':
    unittest.main()
