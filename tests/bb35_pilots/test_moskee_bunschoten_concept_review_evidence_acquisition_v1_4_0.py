\
from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.concept_review_evidence_acquisition import (
    MoskeeConceptReviewEvidenceAcquisition,
)


ROOT = Path(__file__).resolve().parents[2]
CONCEPT = (
    ROOT
    / 'artifacts/bb35/pilot_1_moskee_bunschoten/'
    'concept_generation_v1_3_3'
)


class ConceptReviewEvidenceAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(
            (ROOT / 'configs/projects/moskee_bunschoten_bb35_pilot_1.json').read_text(encoding='utf-8')
        )
        self.verified = json.loads(
            (ROOT / 'inputs/pilots/moskee_bunschoten/verified_inputs_register_v1_2_0.json').read_text(encoding='utf-8')
        )
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.engine = MoskeeConceptReviewEvidenceAcquisition()
        self.result = self.engine.generate(
            project_config=self.config,
            verified_inputs=self.verified,
            concept_root=CONCEPT,
            output_dir=self.output,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read_json(self, relative: str):
        return json.loads((self.output / relative).read_text(encoding='utf-8'))

    def read_csv(self, relative: str):
        with (self.output / relative).open('r', encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))

    def test_engine_version(self):
        self.assertEqual('1.4.0', self.result['engine_version'])

    def test_status_is_review_complete_evidence_open(self):
        self.assertEqual('CONCEPT_REVIEW_COMPLETE_EVIDENCE_ACQUISITION_OPEN', self.result['status'])

    def test_concept_review_is_complete(self):
        self.assertTrue(self.result['concept_review_complete'])

    def test_concept_is_accepted_with_conditions(self):
        self.assertTrue(self.result['concept_package_accepted_with_conditions'])

    def test_all_concept_manifest_artifacts_validate(self):
        self.assertEqual(self.result['concept_artifact_count'], self.result['valid_concept_artifact_count'])
        self.assertGreaterEqual(self.result['concept_artifact_count'], 20)

    def test_scope_remains_140_square_metres(self):
        self.assertEqual(140.0, self.result['authoritative_scope']['gross_extension_area_m2'])

    def test_thirteen_review_items_exist(self):
        self.assertEqual(13, self.result['review_item_count'])

    def test_twelve_findings_exist(self):
        self.assertEqual(12, self.result['finding_count'])

    def test_eighteen_assumptions_are_dispositioned(self):
        self.assertEqual(18, self.result['assumption_count'])

    def test_nine_risks_are_prioritized(self):
        self.assertEqual(9, self.result['risk_count'])

    def test_eight_evidence_requests_are_open(self):
        self.assertEqual(8, self.result['open_evidence_request_count'])

    def test_request_ids_are_req_101_to_108(self):
        rows = self.read_csv('06_evidence_acquisition_master_register.csv')
        self.assertEqual([f'REQ-{number}' for number in range(101, 109)], [row['request_id'] for row in rows])

    def test_every_request_has_six_package_files(self):
        request_root = self.output / 'evidence_requests'
        folders = sorted(path for path in request_root.iterdir() if path.is_dir())
        self.assertEqual(8, len(folders))
        for folder in folders:
            self.assertEqual(6, len([path for path in folder.iterdir() if path.is_file()]))

    def test_every_request_has_pdf(self):
        self.assertEqual(8, len(list((self.output / 'evidence_requests').rglob('*_evidence_request.pdf'))))

    def test_total_pdf_count_is_ten(self):
        self.assertEqual(10, len(list(self.output.rglob('*.pdf'))))

    def test_final_generation_is_blocked(self):
        self.assertFalse(self.result['final_generation_allowed'])

    def test_bb36_is_locked(self):
        self.assertFalse(self.result['bb36_unlock_allowed'])

    def test_concept_development_remains_allowed(self):
        self.assertTrue(self.result['concept_development_allowed'])

    def test_submission_without_files_is_not_submitted(self):
        request = self.engine._evidence_requests(self.verified)[0]
        with tempfile.TemporaryDirectory() as tmp:
            assessment = self.engine.evaluate_submission(request=request, submission_dir=tmp)
        self.assertEqual('not_submitted', assessment['status'])

    def test_submission_without_professional_acceptance_is_unverified(self):
        request = self.engine._evidence_requests(self.verified)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'drawing.pdf').write_bytes(b'%PDF-test')
            assessment = self.engine.evaluate_submission(request=request, submission_dir=root)
        self.assertEqual('submitted_unverified', assessment['status'])

    def test_submission_with_professional_acceptance_is_accepted(self):
        request = self.engine._evidence_requests(self.verified)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'drawing.pdf').write_bytes(b'%PDF-test')
            (root / 'professional_verification.json').write_text(json.dumps({
                'request_id': request['request_id'],
                'verification_status': 'accepted',
                'reviewer_name': 'Reviewer',
                'reviewer_organization': 'Engineering Office',
                'verification_date': '2026-07-27',
            }), encoding='utf-8')
            assessment = self.engine.evaluate_submission(request=request, submission_dir=root)
        self.assertEqual('accepted', assessment['status'])

    def test_checksums_are_valid(self):
        for line in (self.output / 'checksums.sha256').read_text(encoding='utf-8').splitlines():
            digest, relative = line.split('  ', 1)
            self.assertEqual(digest, hashlib.sha256((self.output / relative).read_bytes()).hexdigest())

    def test_dossier_uses_canonical_stored_headers(self):
        dossier = self.output / 'BB35_PILOT_1_CONCEPT_REVIEW_EVIDENCE_ACQUISITION_v1_4_0.zip'
        with zipfile.ZipFile(dossier) as archive:
            infos = archive.infolist()
            self.assertIsNone(archive.testzip())
        self.assertTrue(infos)
        self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED for info in infos))
        self.assertTrue(all(info.create_system == 3 for info in infos))
        self.assertTrue(all(info.flag_bits == 0 for info in infos))

    def test_two_independent_generations_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            self.engine.generate(project_config=self.config, verified_inputs=self.verified, concept_root=CONCEPT, output_dir=one)
            self.engine.generate(project_config=self.config, verified_inputs=self.verified, concept_root=CONCEPT, output_dir=two)
            first = {p.relative_to(one).as_posix(): p.read_bytes() for p in Path(one).rglob('*') if p.is_file()}
            second = {p.relative_to(two).as_posix(): p.read_bytes() for p in Path(two).rglob('*') if p.is_file()}
        self.assertEqual(first, second)

    def test_windows_zipinfo_simulation_is_byte_identical(self):
        original = zipfile.ZipInfo

        class WindowsZipInfo(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.create_system = 0

        with tempfile.TemporaryDirectory() as normal, tempfile.TemporaryDirectory() as simulated:
            self.engine.generate(project_config=self.config, verified_inputs=self.verified, concept_root=CONCEPT, output_dir=normal)
            with unittest.mock.patch(
                'phoenix.bb35_pilots.moskee_bunschoten.concept_review_evidence_acquisition.zipfile.ZipInfo',
                WindowsZipInfo,
            ):
                self.engine.generate(project_config=self.config, verified_inputs=self.verified, concept_root=CONCEPT, output_dir=simulated)
            name = 'BB35_PILOT_1_CONCEPT_REVIEW_EVIDENCE_ACQUISITION_v1_4_0.zip'
            self.assertEqual((Path(normal) / name).read_bytes(), (Path(simulated) / name).read_bytes())

    def test_manifest_blocks_final_and_bb36(self):
        manifest = self.read_json('concept_review_evidence_acquisition_manifest.json')
        self.assertFalse(manifest['final_generation_allowed'])
        self.assertFalse(manifest['bb36_unlock_allowed'])


if __name__ == '__main__':
    unittest.main()
