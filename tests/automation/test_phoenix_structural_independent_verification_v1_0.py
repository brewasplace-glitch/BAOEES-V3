from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.structural_independent_verification_v1_0 import (
    STATUS_CROSS_VERIFIED,
    STATUS_FAILED,
    STATUS_INPUT_REQUIRED,
    STATUS_VERIFIED,
    verify,
)


CATS = (
    "source_evidence",
    "global_equilibrium",
    "analytical_spot_checks",
    "load_path",
    "solver_health",
    "scia_calculix_cross_check",
    "mesh_convergence",
    "sensitivity",
    "evidence_integrity",
)


def na(reason="Not required by synthetic test"):
    return {"applicability": "NOT_APPLICABLE", "rationale": reason, "source_record_id": "TEST-SOURCE"}


def base_plan():
    return {
        "schema_version": "phoenix.structural-independent-verification-plan/1.0",
        "project_id": "TEST",
        "categories": {c: na() for c in CATS},
    }


class VerificationTests(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        scia = root / "scia_run_result.json"
        scia.write_text(json.dumps({
            "status": "CALCULATED_UNVERIFIED",
            "safety": {
                "automatic_professional_approval": False,
                "production_release": "LOCKED",
                "for_construction_release": "LOCKED",
            },
        }), encoding="utf-8")
        log = root / "solver.log"
        log.write_text("calculation completed", encoding="utf-8")
        evidence = root / "evidence.bin"
        evidence.write_bytes(b"evidence")
        values = root / "values.json"
        values.write_text(json.dumps({"scia": 100.0, "ccx": 100.5}), encoding="utf-8")
        return tmp, root, scia, log, evidence, values

    def test_01_no_default_tolerance_is_allowed(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["scia_calculix_cross_check"] = {
                "applicability": "REQUIRED",
                "comparisons": [{"comparison_id": "x", "scia": 1.0, "calculix": 1.0}],
            }
            r = verify(p, root)
            self.assertEqual(STATUS_INPUT_REQUIRED, r["status"])
        finally:
            tmp.cleanup()

    def test_02_source_scia_calculated_unverified_is_accepted_as_source_only(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["source_evidence"] = {
                "applicability": "REQUIRED",
                "scia_run_result": scia.relative_to(root).as_posix(),
            }
            r = verify(p, root)
            self.assertEqual(STATUS_VERIFIED, r["status"])
            self.assertEqual("PASS", r["categories"]["source_evidence"]["status"])
            self.assertEqual("NOT_PERFORMED_BY_THIS_ENGINE", r["professional_review_status"])
        finally:
            tmp.cleanup()

    def test_03_equilibrium_passes_only_with_explicit_tolerances(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            tol = {"mode": "ALL", "absolute": 0.01}
            p = base_plan()
            p["categories"]["global_equilibrium"] = {
                "applicability": "REQUIRED",
                "cases": [{
                    "case_id": "LC1",
                    "applied": {"Fx": 0, "Fy": 0, "Fz": -100, "Mx": 0, "My": 0, "Mz": 0},
                    "reactions": {"Fx": 0, "Fy": 0, "Fz": 100, "Mx": 0, "My": 0, "Mz": 0},
                    "tolerances": {k: tol for k in ("Fx","Fy","Fz","Mx","My","Mz")},
                }],
            }
            r = verify(p, root)
            self.assertEqual(STATUS_VERIFIED, r["status"])
        finally:
            tmp.cleanup()

    def test_04_analytical_beam_formula(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["analytical_spot_checks"] = {
                "applicability": "REQUIRED",
                "checks": [{
                    "check_id": "beam",
                    "formula": "simply_supported_udl_max_moment",
                    "parameters": {"q": 10.0, "L": 4.0},
                    "observed": 20.0,
                    "tolerance": {"mode": "ALL", "absolute": 0.0001},
                }],
            }
            self.assertEqual(STATUS_VERIFIED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_05_cross_solver_with_json_pointer_can_cross_verify(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            rel = values.relative_to(root).as_posix()
            p = base_plan()
            p["categories"]["scia_calculix_cross_check"] = {
                "applicability": "REQUIRED",
                "comparisons": [{
                    "comparison_id": "M1",
                    "metric": "moment",
                    "scia": {"source_file": rel, "json_pointer": "/scia"},
                    "calculix": {"source_file": rel, "json_pointer": "/ccx"},
                    "tolerance": {"mode": "ALL", "relative": 0.01},
                }],
            }
            r = verify(p, root)
            self.assertEqual(STATUS_CROSS_VERIFIED, r["status"])
        finally:
            tmp.cleanup()

    def test_06_incomplete_load_path_fails(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["load_path"] = {
                "applicability": "REQUIRED",
                "paths": [{"path_id": "P1", "nodes": ["roof", "beam"], "complete_to_support": False, "source_records": ["X"]}],
            }
            self.assertEqual(STATUS_FAILED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_07_solver_blocking_pattern_fails(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            log.write_text("singular stiffness matrix", encoding="utf-8")
            p = base_plan()
            p["categories"]["solver_health"] = {
                "applicability": "REQUIRED",
                "log_files": [log.relative_to(root).as_posix()],
                "blocking_patterns": ["singular stiffness"],
            }
            self.assertEqual(STATUS_FAILED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_08_mesh_convergence_uses_explicit_limit(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["mesh_convergence"] = {
                "applicability": "REQUIRED",
                "studies": [{
                    "study_id": "S1",
                    "points": [{"mesh": 500, "value": 100}, {"mesh": 250, "value": 101}],
                    "max_relative_change": 0.02,
                }],
            }
            self.assertEqual(STATUS_VERIFIED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_09_sensitivity_direction(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["sensitivity"] = {
                "applicability": "REQUIRED",
                "studies": [{"study_id": "S", "baseline": 10, "perturbed": 11, "expected_direction": "INCREASE"}],
            }
            self.assertEqual(STATUS_VERIFIED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_10_evidence_sha_mismatch_fails(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["evidence_integrity"] = {
                "applicability": "REQUIRED",
                "files": [{"path": evidence.relative_to(root).as_posix(), "sha256": "0"*64}],
            }
            self.assertEqual(STATUS_FAILED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_11_not_applicable_requires_traceability(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["mesh_convergence"] = {"applicability": "NOT_APPLICABLE"}
            self.assertEqual(STATUS_INPUT_REQUIRED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_12_solver_health_requires_explicit_patterns_even_empty_list_is_valid(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["solver_health"] = {
                "applicability": "REQUIRED",
                "log_files": [log.relative_to(root).as_posix()],
                "blocking_patterns": [],
            }
            self.assertEqual(STATUS_VERIFIED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_13_cross_solver_failure_blocks_cross_verification(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            p = base_plan()
            p["categories"]["scia_calculix_cross_check"] = {
                "applicability": "REQUIRED",
                "comparisons": [{
                    "comparison_id": "x",
                    "scia": 100.0,
                    "calculix": 130.0,
                    "tolerance": {"mode": "ALL", "relative": 0.05},
                }],
            }
            self.assertEqual(STATUS_FAILED, verify(p, root)["status"])
        finally:
            tmp.cleanup()

    def test_14_release_and_professional_boundaries_are_hard(self):
        tmp, root, scia, log, evidence, values = self.make_repo()
        try:
            r = verify(base_plan(), root)
            self.assertFalse(r["safety"]["automatic_professional_approval"])
            self.assertFalse(r["safety"]["automatic_code_compliance_claim"])
            self.assertTrue(r["safety"]["second_solver_is_not_independent_professional_review"])
            self.assertEqual("LOCKED", r["safety"]["production_release"])
            self.assertEqual("LOCKED", r["safety"]["for_construction_release"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
