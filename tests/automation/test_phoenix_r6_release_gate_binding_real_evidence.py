from __future__ import annotations

import json
from pathlib import Path
import unittest

from phoenix.commercial_release_masterpack.engine import CommercialReleaseEngine


class R6ReleaseGateRealEvidenceTests(unittest.TestCase):
    def _latest_r6_evidence(self) -> dict:
        repo = Path(__file__).resolve().parents[2]
        root = repo / "outputs" / "runtime" / "r6_runtime_canonical_geometry_qa"
        files = sorted(
            root.rglob("R6_RUNTIME_CANONICAL_GEOMETRY_QA.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        self.assertTrue(files, "No R6 runtime evidence found")
        return json.loads(files[0].read_text(encoding="utf-8-sig"))

    def test_real_runtime_r6_evidence_unlocks_only_r6_check(self):
        r6 = self._latest_r6_evidence()
        report = CommercialReleaseEngine().create_release(
            version="2.0.0",
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": True},
            security_report={"security_passed": True},
            documentation_available=True,
            support_plan_available=True,
            release_requested=True,
            r6_canonical_geometry_report=r6,
        )
        self.assertTrue(report["checks"]["r6_canonical_geometry_passed"])
        self.assertTrue(report["r6_canonical_geometry_gate"]["passed"])
        self.assertFalse(report["release_semantics"]["professional_approval_inferred"])
        self.assertFalse(report["release_semantics"]["approved_for_construction_inferred"])

    def test_tampered_real_runtime_r6_evidence_fails_closed(self):
        r6 = self._latest_r6_evidence()
        r6 = json.loads(json.dumps(r6))
        r6["variants"][0]["result"]["hard_pass"] = False
        report = CommercialReleaseEngine().create_release(
            version="2.0.0",
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": True},
            security_report={"security_passed": True},
            documentation_available=True,
            support_plan_available=True,
            release_requested=True,
            r6_canonical_geometry_report=r6,
        )
        self.assertFalse(report["production_release_ready"])
        self.assertIn("r6_canonical_geometry_passed", report["failed_checks"])


if __name__ == "__main__":
    unittest.main()
