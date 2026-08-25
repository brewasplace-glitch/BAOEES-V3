import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.cost_estimate_artifact_bridge_v1_0 import (
    emit_level_a_cost_estimate_artifact,
)

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "phoenix" / "autonomy" / "session_adapters.py"


class CostEstimateArtifactBridgeTests(unittest.TestCase):
    def test_unresolved_prices_emit_real_artifact_without_fabrication(self):
        with tempfile.TemporaryDirectory() as td:
            path = emit_level_a_cost_estimate_artifact(
                output_dir=Path(td),
                project_id="P",
                session_id="S",
                plan={
                    "currency": "EUR",
                    "pricing_level": None,
                    "pricing_as_of_date": "2026-08-25",
                    "price_evidence_status": "UNRESOLVED",
                    "price_source_register": "prices.json",
                    "market_context": "market.json",
                    "cost_calculation": None,
                    "automatic_tax_application": False,
                    "fx_used": False,
                    "international_fx_fallback": False,
                    "unresolved_price_evidence": [
                        {"reason": "PRICE_EVIDENCE_UNRESOLVED"}
                    ],
                },
            )
            self.assertEqual(path.name, "cost_estimate.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["status"],
                "PRICE_EVIDENCE_UNRESOLVED_ESTIMATE_CONTINUES",
            )
            self.assertEqual(payload["currency"], "EUR")
            self.assertFalse(payload["pricing_rules"]["price_fabricated"])
            self.assertIsNone(payload["estimate"]["total"])
            self.assertEqual(payload["for_construction"], "LOCKED")
            self.assertFalse(payload["automatic_professional_approval"])

    def test_existing_cost_calculation_reference_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            path = emit_level_a_cost_estimate_artifact(
                output_dir=Path(td),
                project_id="P",
                session_id=None,
                plan={
                    "currency": "EUR",
                    "price_evidence_status": "RESOLVED",
                    "cost_calculation": "cost_calculation.json",
                },
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["status"], "LOCAL_COST_CALCULATION_AVAILABLE"
            )
            self.assertEqual(
                payload["cost_calculation"], "cost_calculation.json"
            )

    def test_session_adapter_emits_cost_estimate_on_success_path(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        cost_start = text.index("def run_cost_planning(")
        next_fn = text.index("def run_reporting(", cost_start)
        block = text[cost_start:next_fn]

        call = "emit_level_a_cost_estimate_artifact("
        plan_write = 'plan_path=ctx["output_dir"]/"cost_planning_plan.json"'
        output_append = 'outputs.append(repo_ref(cost_estimate_path,ctx["repository"]))'

        self.assertIn(call, block)
        self.assertIn(plan_write, block)
        self.assertIn(output_append, block)

        call_pos = block.index(call)
        plan_pos = block.index(plan_write)
        append_pos = block.index(output_append)
        success_finish_pos = block.index("return finish(", append_pos)

        self.assertLess(call_pos, plan_pos)
        self.assertLess(plan_pos, append_pos)
        self.assertLess(append_pos, success_finish_pos)

    def test_existing_cost_engine_remains_available(self):
        self.assertTrue(
            (ROOT / "runners" / "PROJECT_PHOENIX_BB21_cost_estimation_engine.py").is_file()
        )


if __name__ == "__main__":
    unittest.main()
