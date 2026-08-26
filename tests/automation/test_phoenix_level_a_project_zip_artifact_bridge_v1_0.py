import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.autonomy.level_a_project_zip_artifact_bridge_v1_0 import (
    ARCHIVE_NAME,
    INTERNAL_MANIFEST_NAME,
    SIDECAR_NAME,
    emit_level_a_project_zip_artifact,
)


class LevelAProjectZipArtifactBridgeTests(unittest.TestCase):
    def _build_workspace(self, root: Path):
        workspace = root / "workspace"
        closure = workspace / "results" / "session_adapters" / "closure"
        architecture = workspace / "results" / "session_adapters" / "architecture"
        closure.mkdir(parents=True)
        architecture.mkdir(parents=True)
        (architecture / "site_plan.svg").write_text("<svg/>", encoding="utf-8")
        (workspace / "result_index.json").write_text('{"status":"BLOCKED"}', encoding="utf-8")
        gate = closure / "qaqc_release_gate.json"
        gate.write_text(
            json.dumps(
                {
                    "qaqc_status": "BLOCKED",
                    "upstream_blocker_count": 3,
                    "production_release": "LOCKED",
                }
            ),
            encoding="utf-8",
        )
        return workspace, closure, gate

    def test_emits_valid_candidate_zip_while_qaqc_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace, closure, gate = self._build_workspace(root)
            archive, sidecar = emit_level_a_project_zip_artifact(
                workspace=workspace,
                output_dir=closure,
                project_id="P",
                session_id="S",
                qaqc_gate_path=gate,
            )
            self.assertTrue(archive.is_file())
            self.assertTrue(sidecar.is_file())
            self.assertTrue(zipfile.is_zipfile(archive))

            side = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual("PROJECT_ZIP", side["artifact_type"])
            self.assertEqual("LEVEL_A_CANDIDATE_PROJECT_EVIDENCE", side["package_class"])
            self.assertFalse(side["formal_release"])
            self.assertTrue(side["professional_review_required"])
            self.assertFalse(side["automatic_professional_approval"])
            self.assertEqual("LOCKED", side["production_release"])
            self.assertEqual("LOCKED", side["for_construction"])
            self.assertEqual("BLOCKED", side["qaqc_gate_state"]["qaqc_status"])

    def test_archive_contains_manifest_and_project_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace, closure, gate = self._build_workspace(root)
            archive, _ = emit_level_a_project_zip_artifact(
                workspace=workspace,
                output_dir=closure,
                project_id="P",
                session_id="S",
                qaqc_gate_path=gate,
            )
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
                self.assertIn(INTERNAL_MANIFEST_NAME, names)
                self.assertIn(
                    "results/session_adapters/architecture/site_plan.svg",
                    names,
                )
                internal = json.loads(zf.read(INTERNAL_MANIFEST_NAME).decode("utf-8"))
                self.assertFalse(internal["formal_release"])
                self.assertEqual("LOCKED", internal["for_construction"])

    def test_existing_zip_is_not_nested(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace, closure, gate = self._build_workspace(root)
            old_zip = workspace / "old_project_package.zip"
            old_zip.write_bytes(b"not-relevant")
            archive, _ = emit_level_a_project_zip_artifact(
                workspace=workspace,
                output_dir=closure,
                project_id="P",
                session_id="S",
                qaqc_gate_path=gate,
            )
            with zipfile.ZipFile(archive) as zf:
                self.assertNotIn("old_project_package.zip", zf.namelist())

    def test_two_exports_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            wa, ca, ga = self._build_workspace(Path(a))
            wb, cb, gb = self._build_workspace(Path(b))
            za, _ = emit_level_a_project_zip_artifact(
                workspace=wa,
                output_dir=ca,
                project_id="P",
                session_id="S",
                qaqc_gate_path=ga,
            )
            zb, _ = emit_level_a_project_zip_artifact(
                workspace=wb,
                output_dir=cb,
                project_id="P",
                session_id="S",
                qaqc_gate_path=gb,
            )
            self.assertEqual(
                hashlib.sha256(za.read_bytes()).hexdigest(),
                hashlib.sha256(zb.read_bytes()).hexdigest(),
            )

    def test_sidecar_is_excluded_from_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace, closure, gate = self._build_workspace(root)
            archive, sidecar = emit_level_a_project_zip_artifact(
                workspace=workspace,
                output_dir=closure,
                project_id="P",
                session_id="S",
                qaqc_gate_path=gate,
            )
            with zipfile.ZipFile(archive) as zf:
                expected_sidecar_member = (
                    "results/session_adapters/closure/" + SIDECAR_NAME
                )
                self.assertNotIn(
                    expected_sidecar_member,
                    zf.namelist(),
                )


if __name__ == "__main__":
    unittest.main()
