import json
import tempfile
import unittest
from pathlib import Path

from phoenix.adapters.optimization_core_adapter import run_optimization_core
from phoenix.optimization import (
    Constraint,
    Objective,
    OptimizationConfig,
    OptimizationCore,
    OptimizationError,
    Variant,
)


def sample_core() -> OptimizationCore:
    return OptimizationCore(
        OptimizationConfig(
            project_id="PHX-TEST-15-1",
            objectives=(
                Objective("cost", "minimize", 0.4),
                Objective("carbon", "minimize", 0.2),
                Objective("safety", "maximize", 0.4),
            ),
            constraints=(
                Constraint("utilization", "utilization", "<=", 1.0),
            ),
        )
    )


def sample_variants():
    return (
        Variant(
            "A",
            {"cost": 100.0, "carbon": 80.0, "safety": 1.25, "utilization": 0.80},
        ),
        Variant(
            "B",
            {"cost": 90.0, "carbon": 70.0, "safety": 1.10, "utilization": 0.90},
        ),
        Variant(
            "C",
            {"cost": 110.0, "carbon": 95.0, "safety": 1.05, "utilization": 1.10},
        ),
    )


class OptimizationCoreWave151Tests(unittest.TestCase):
    def test_rejects_infeasible_variant(self):
        result = sample_core().evaluate(sample_variants())
        self.assertEqual(result["rejected_variant_ids"], ["C"])
        self.assertEqual(result["feasible_variant_ids"], ["A", "B"])

    def test_pareto_front_contains_tradeoff_variants(self):
        result = sample_core().evaluate(sample_variants())
        self.assertEqual(result["pareto_front"], ["A", "B"])

    def test_ranking_is_deterministic(self):
        core = sample_core()
        first = core.evaluate(reversed(sample_variants()))
        second = core.evaluate(sample_variants())
        self.assertEqual(first["ranking"], second["ranking"])
        self.assertEqual(first["recommended_variant_id"], "B")

    def test_evidence_hash_has_sha256_length(self):
        result = sample_core().evaluate(sample_variants())
        self.assertEqual(result["evidence"]["algorithm"], "sha256")
        self.assertEqual(len(result["evidence"]["payload_sha256"]), 64)

    def test_missing_objective_metric_is_rejected(self):
        bad = Variant("BAD", {"cost": 1.0, "utilization": 0.1})
        with self.assertRaises(OptimizationError):
            sample_core().evaluate([bad])

    def test_no_feasible_variant_is_rejected(self):
        bad = Variant(
            "BAD",
            {"cost": 1.0, "carbon": 1.0, "safety": 1.0, "utilization": 2.0},
        )
        with self.assertRaisesRegex(OptimizationError, "No feasible variants"):
            sample_core().evaluate([bad])

    def test_adapter_writes_json_output(self):
        request = {
            "config": {
                "project_id": "PHX-ADAPTER",
                "objectives": [
                    {"name": "cost", "direction": "minimize", "weight": 1.0}
                ],
            },
            "variants": [
                {"variant_id": "A", "metrics": {"cost": 2.0}},
                {"variant_id": "B", "metrics": {"cost": 1.0}},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "optimization_result.json"
            result = run_optimization_core(request, output)
            stored = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["recommended_variant_id"], "B")
        self.assertEqual(stored["adapter"]["id"], "phoenix.adapter.optimization_core.wave15_1")

    def test_write_result_is_atomic_and_valid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "result.json"
            path = sample_core().write_result(sample_variants(), destination)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "optimization_complete")
            self.assertFalse(destination.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
