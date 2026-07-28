from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.professional_evidence_intake_closure_gate import (
    ProfessionalEvidenceIntakeClosureExporter,
    ProfessionalEvidenceIntakeClosureGate,
    canonical_output_files,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'configs/projects/moskee_bunschoten_professional_evidence_intake_closure_gate_v2_3_0.json').read_text(encoding='utf-8'))


class ProfessionalEvidenceIntakeClosureGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = ProfessionalEvidenceIntakeClosureGate(CONFIG)
        self.exporter = ProfessionalEvidenceIntakeClosureExporter(CONFIG)

    def _valid_submission(self, root: Path, requirement_id: str) -> Path:
        rule = CONFIG['requirements'][requirement_id]
        req = root / requirement_id
        evidence = req / 'evidence'
        evidence.mkdir(parents=True, exist_ok=True)
        documents = []
        for index, document_type in enumerate(rule['required_document_types'], start=1):
            file = evidence / f'{requirement_id}_{index}.pdf'
            file.write_bytes(f'{requirement_id} professional evidence {document_type}\n'.encode('utf-8'))
            documents.append({
                'document_type': document_type,
                'relative_path': f'evidence/{file.name}',
                'title': f'{requirement_id} professional {document_type}',
                'revision': 'A',
                'issue_date': '2026-07-28',
                'sha256': sha256_file(file),
            })
        manifest = {
            'schema_version': 'phoenix.professional-evidence-submission/1.0',
            'project_id': CONFIG['project_id'],
            'requirement_id': requirement_id,
            'submission_id': f'{requirement_id}-PROF-2026-001',
            'issue_date': '2026-07-28',
            'supersedes_simulated_evidence': True,
            'scope_statement': f'Project-specific professional scope for {requirement_id}.',
            'basis_of_design': 'Measured, calculated and professionally reviewed project evidence.',
            'limitations': 'No limitations affecting the submitted conclusions.',
            'professional': {
                'name': 'Qualified Adviser',
                'organization': 'Independent Engineering Office',
                'discipline': rule['discipline'],
                'registration_number': 'REG-2026-001',
                'registration_authority': 'Competent professional authority',
                'signed_declaration': True,
                'declaration_text': 'I accept professional responsibility for this submission.',
            },
            'basis_fields': rule['required_basis_fields'],
            'documents': documents,
        }
        manifest_path = req / 'submission_manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        decision = {
            'schema_version': 'phoenix.project-leader-evidence-decision/1.0',
            'project_id': CONFIG['project_id'],
            'requirement_id': requirement_id,
            'decision': 'ACCEPTED',
            'approved': True,
            'decision_date': '2026-07-28',
            'approved_by_name': 'Project Leader',
            'approved_by_role': 'Projectleider',
            'critical_findings_open': 0,
            'reviewed_manifest_sha256': sha256_file(manifest_path),
            'decision_note': 'Evidence accepted after validation.',
        }
        (req / 'project_leader_decision.json').write_text(json.dumps(decision, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        return req

    def test_empty_intake_is_operational(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertTrue(report['intake_gate_operational'])

    def test_empty_intake_accepts_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertEqual(0, report['evidence_accepted_count'])

    def test_empty_intake_has_six_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertEqual(6, report['evidence_open_count'])

    def test_req107_remains_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertEqual('CLOSED', report['req107_status'])
        self.assertEqual('HBM-OCC-2026-001', report['req107_programme_id'])

    def test_empty_intake_gate_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertFalse(report['professional_evidence_closure_gate_passed'])

    def test_all_final_release_gates_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertFalse(report['permit_ready_release_allowed'])
        self.assertFalse(report['tender_ready_release_allowed'])
        self.assertFalse(report['execution_ready_release_allowed'])
        self.assertFalse(report['bb36_production_release_allowed'])

    def test_valid_single_submission_closes_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self._valid_submission(root, 'REQ-102')
            report = self.gate.evaluate(root)
        self.assertEqual(1, report['evidence_accepted_count'])
        self.assertEqual('ACCEPTED_CLOSED', report['requirement_statuses'][0]['status'])

    def test_each_requirement_can_be_accepted(self):
        for requirement_id in CONFIG['requirements']:
            with self.subTest(requirement_id=requirement_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); self._valid_submission(root, requirement_id)
                report = self.gate.evaluate(root)
                accepted = [row['requirement_id'] for row in report['requirement_statuses'] if row['accepted']]
                self.assertEqual([requirement_id], accepted)

    def test_all_six_pass_closure_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for requirement_id in CONFIG['requirements']:
                self._valid_submission(root, requirement_id)
            report = self.gate.evaluate(root)
        self.assertEqual(6, report['evidence_accepted_count'])
        self.assertTrue(report['professional_evidence_closure_gate_passed'])

    def test_all_six_require_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for requirement_id in CONFIG['requirements']:
                self._valid_submission(root, requirement_id)
            report = self.gate.evaluate(root)
        self.assertTrue(report['technical_regeneration_required'])
        self.assertTrue(report['release_candidate_after_regeneration'])
        self.assertFalse(report['permit_ready_release_allowed'])

    def test_wrong_project_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-102')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['project_id'] = 'WRONG'; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('PROJECT_ID_MISMATCH', {row['finding_code'] for row in report['validation_findings']})

    def test_unsigned_professional_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-103')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['professional']['signed_declaration'] = False; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('PROFESSIONAL_SIGNATURE_MISSING', {row['finding_code'] for row in report['validation_findings']})

    def test_simulation_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-104')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['scope_statement'] = 'Synthetic simulation evidence'; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('FORBIDDEN_PLACEHOLDER_MARKER', {row['finding_code'] for row in report['validation_findings']})

    def test_missing_document_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-105')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['documents'] = data['documents'][:-1]; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('REQUIRED_DOCUMENT_TYPE_MISSING', {row['finding_code'] for row in report['validation_findings']})

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-106')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['documents'][0]['sha256'] = '0' * 64; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('DOCUMENT_HASH_MISMATCH', {row['finding_code'] for row in report['validation_findings']})

    def test_unsafe_relative_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-108')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['documents'][0]['relative_path'] = '../outside.pdf'; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('DOCUMENT_PATH_UNSAFE', {row['finding_code'] for row in report['validation_findings']})

    def test_wrong_parking_basis_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-106')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['basis_fields']['parking_basis_spaces'] = 300; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('BASIS_FIELD_INVALID', {row['finding_code'] for row in report['validation_findings']})

    def test_too_few_parking_count_moments_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-106')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['basis_fields']['minimum_count_moments_completed'] = 4; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('BASIS_FIELD_INVALID', {row['finding_code'] for row in report['validation_findings']})

    def test_wrong_occupancy_program_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-105')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['basis_fields']['occupancy_program_id'] = 'WRONG'; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('BASIS_FIELD_INVALID', {row['finding_code'] for row in report['validation_findings']})

    def test_missing_project_leader_decision_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-102'); (req / 'project_leader_decision.json').unlink()
            report = self.gate.evaluate(root)
        self.assertIn('PROJECT_LEADER_DECISION_MISSING', {row['finding_code'] for row in report['validation_findings']})

    def test_decision_manifest_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-103')
            path = req / 'project_leader_decision.json'; data = json.loads(path.read_text()); data['reviewed_manifest_sha256'] = '0' * 64; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('DECISION_MANIFEST_HASH_MISMATCH', {row['finding_code'] for row in report['validation_findings']})

    def test_open_critical_findings_prevent_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-104')
            path = req / 'project_leader_decision.json'; data = json.loads(path.read_text()); data['critical_findings_open'] = 1; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('CRITICAL_FINDINGS_OPEN', {row['finding_code'] for row in report['validation_findings']})

    def test_manifest_schema_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); req = self._valid_submission(root, 'REQ-108')
            path = req / 'submission_manifest.json'; data = json.loads(path.read_text()); data['schema_version'] = 'wrong'; path.write_text(json.dumps(data), encoding='utf-8')
            report = self.gate.evaluate(root)
        self.assertIn('MANIFEST_SCHEMA', {row['finding_code'] for row in report['validation_findings']})

    def test_change_impacts_created_for_accepted_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self._valid_submission(root, 'REQ-102'); report = self.gate.evaluate(root)
        self.assertEqual(4, len(report['change_impacts']))
        self.assertTrue(all(row['action'] == 'INVALIDATE_AND_REGENERATE' for row in report['change_impacts']))

    def test_accepted_snapshot_has_manifest_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self._valid_submission(root, 'REQ-103'); report = self.gate.evaluate(root)
        self.assertEqual(64, len(report['accepted_evidence_snapshot'][0]['manifest_sha256']))

    def test_export_generates_at_least_40_files(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as output:
            report = self.gate.evaluate(Path(intake)); self.exporter.export_all(report, Path(output))
            count = sum(1 for path in Path(output).rglob('*') if path.is_file())
        self.assertGreaterEqual(count, 41)

    def test_export_contains_six_template_folders(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as output:
            report = self.gate.evaluate(Path(intake)); self.exporter.export_all(report, Path(output))
            folders = sorted(path.name for path in (Path(output) / 'submission_templates').iterdir() if path.is_dir())
        self.assertEqual(sorted(CONFIG['requirements']), folders)

    def test_each_template_folder_contains_four_files(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as output:
            report = self.gate.evaluate(Path(intake)); self.exporter.export_all(report, Path(output))
            for requirement_id in CONFIG['requirements']:
                self.assertEqual(4, len(list((Path(output) / 'submission_templates' / requirement_id).iterdir())))

    def test_dashboard_contains_blocked_release_warning(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as output:
            report = self.gate.evaluate(Path(intake)); paths = self.exporter.export_all(report, Path(output)); content = paths['dashboard'].read_text()
        self.assertIn('BB36 release remain blocked', content)

    def test_issue_zip_is_canonical_stored(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as output:
            report = self.gate.evaluate(Path(intake)); paths = self.exporter.export_all(report, Path(output))
            with zipfile.ZipFile(paths['issue_package']) as archive:
                infos = archive.infolist()
        self.assertTrue(infos)
        self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED and info.create_system == 3 and info.date_time == (2020,1,1,0,0,0) for info in infos))

    def test_two_empty_exports_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            report = self.gate.evaluate(Path(intake)); self.exporter.export_all(report, Path(first)); self.exporter.export_all(report, Path(second))
            first_root = Path(first); second_root = Path(second)
            names1 = sorted(path.relative_to(first_root).as_posix() for path in first_root.rglob('*') if path.is_file())
            names2 = sorted(path.relative_to(second_root).as_posix() for path in second_root.rglob('*') if path.is_file())
            self.assertEqual(names1, names2)
            self.assertTrue(all((first_root / name).read_bytes() == (second_root / name).read_bytes() for name in names1))

    def test_gate_matrix_has_eight_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertEqual(8, len(report['gate_matrix']))

    def test_closure_register_has_six_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertEqual(6, len(report['closure_register']))

    def test_requirement_order_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.gate.evaluate(Path(tmp))
        self.assertEqual(['REQ-102','REQ-103','REQ-104','REQ-105','REQ-106','REQ-108'], [row['requirement_id'] for row in report['requirement_statuses']])

    def test_accepted_fingerprint_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self._valid_submission(root, 'REQ-102')
            first = self.gate.evaluate(root)['accepted_evidence_fingerprint_sha256']
            second = self.gate.evaluate(root)['accepted_evidence_fingerprint_sha256']
        self.assertEqual(first, second)

    def test_config_requires_all_six(self):
        self.assertTrue(CONFIG['release_policy']['professional_evidence_gate_requires_all_six_closed'])

    def test_config_forbids_simulated_closure(self):
        self.assertTrue(CONFIG['release_policy']['simulated_evidence_cannot_close_requirement'])

    def test_config_requires_post_closure_regeneration(self):
        self.assertTrue(CONFIG['release_policy']['accepted_evidence_requires_model_regeneration'])

    def test_checksum_manifest_uses_case_sensitive_relative_posix_order(self):
        with tempfile.TemporaryDirectory() as intake, tempfile.TemporaryDirectory() as output:
            report = self.gate.evaluate(Path(intake))
            paths = self.exporter.export_all(report, Path(output))
            checksum_names = [
                line.split('  ', 1)[1]
                for line in paths['checksums'].read_text(encoding='utf-8').splitlines()
                if line.strip()
            ]
            canonical_names = [
                path.relative_to(Path(output)).as_posix()
                for path in canonical_output_files(Path(output))
            ]
        self.assertEqual(sorted(checksum_names), checksum_names)
        self.assertEqual(canonical_names, checksum_names)
        self.assertNotEqual(sorted(checksum_names, key=str.casefold), checksum_names)



if __name__ == '__main__':
    unittest.main()
