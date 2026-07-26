from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten import (
    MoskeeBunschotenPilotEngine,
    MoskeeBunschotenPilotExporter,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/projects/moskee_bunschoten_bb35_pilot_1.json"
EVIDENCE_ROOT = ROOT / "inputs/pilots/moskee_bunschoten/source_evidence"
MANIFEST = ROOT / "inputs/pilots/moskee_bunschoten/evidence_manifest.json"


class MoskeePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MoskeeBunschotenPilotEngine()
        self.exporter = MoskeeBunschotenPilotExporter()
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def evaluate(self):
        return self.engine.evaluate(
            config=self.config,
            evidence_manifest=self.manifest,
            evidence_root=EVIDENCE_ROOT,
        )

    def test_real_evidence_hashes_are_valid(self) -> None:
        report = self.evaluate()
        self.assertEqual(
            report["source_evidence_count"],
            report["source_evidence_valid_count"],
        )

    def test_pilot_is_started_but_not_completed(self) -> None:
        report = self.evaluate()
        self.assertTrue(report["pilot_started"])
        self.assertFalse(report["pilot_completed"])

    def test_status_requires_strategic_decision(self) -> None:
        report = self.evaluate()
        self.assertEqual(
            "BLOCKED_PENDING_STRATEGIC_DECISION",
            report["status"],
        )

    def test_bb36_remains_locked(self) -> None:
        report = self.evaluate()
        self.assertFalse(report["bb36_unlock_allowed"])

    def test_scope_conflict_is_registered(self) -> None:
        report = self.evaluate()
        self.assertTrue(any(
            item["conflict_id"] == "HBM-CONFLICT-001"
            for item in report["verified_conflicts"]
        ))

    def test_nine_commercial_deliverables_are_assessed(self) -> None:
        report = self.evaluate()
        self.assertEqual(9, report["commercial_deliverable_count"])

    def test_no_commercial_deliverable_is_falsely_ready(self) -> None:
        report = self.evaluate()
        self.assertEqual(0, report["ready_deliverable_count"])

    def test_missing_structural_inputs_are_blocking(self) -> None:
        report = self.evaluate()
        self.assertTrue(any(
            item["input_id"] == "HBM-IN-003"
            and item["blocking"]
            for item in report["required_input_evidence"]
        ))

    def test_modified_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = next(EVIDENCE_ROOT.iterdir())
            for item in EVIDENCE_ROOT.iterdir():
                target = root / item.name
                target.write_bytes(item.read_bytes())
            (root / source.name).write_bytes(b"modified")
            report = self.engine.evaluate(
                config=self.config,
                evidence_manifest=self.manifest,
                evidence_root=root,
            )
            self.assertEqual("INVALID_EVIDENCE", report["status"])

    def test_exports_create_complete_baseline_dossier(self) -> None:
        report = self.evaluate()
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(report, tmp)
            self.assertEqual(8, len(paths))
            self.assertTrue(all(path.is_file() for path in paths.values()))
            with zipfile.ZipFile(paths["dossier"]) as archive:
                names = set(archive.namelist())
            self.assertIn("bb35_pilot_1_baseline_report.json", names)
            self.assertIn("strategic_decision_register.json", names)
            self.assertIn("PILOT_README.txt", names)


if __name__ == "__main__":
    unittest.main()
