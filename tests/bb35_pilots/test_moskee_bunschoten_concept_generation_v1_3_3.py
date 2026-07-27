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

from phoenix.bb35_pilots.moskee_bunschoten.concept_generation import (
    MoskeeBunschotenConceptGenerator,
    STATUS_NOTICE,
)

ROOT = Path(__file__).resolve().parents[2]


class ConceptGenerationV133Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((ROOT / 'configs/projects/moskee_bunschoten_bb35_pilot_1.json').read_text(encoding='utf-8'))
        self.verified = json.loads((ROOT / 'inputs/pilots/moskee_bunschoten/verified_inputs_register_v1_2_0.json').read_text(encoding='utf-8'))
        self.tmp = tempfile.TemporaryDirectory()
        self.output = Path(self.tmp.name)
        self.result = MoskeeBunschotenConceptGenerator().generate(config=self.config, verified_inputs=self.verified, output_dir=self.output)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_scope_option_b(self):
        self.assertEqual('B', self.result['scope']['selected_option'])

    def test_scope_dimensions(self):
        self.assertEqual(7.0, self.result['scope']['extension_width_m'])
        self.assertEqual(10.0, self.result['scope']['extension_depth_m'])

    def test_two_storeys(self):
        self.assertEqual(2, self.result['scope']['number_of_extension_storeys'])

    def test_gross_area_140(self):
        self.assertEqual(140.0, self.result['gross_area_m2'])

    def test_fifteen_spaces(self):
        self.assertEqual(15, self.result['space_count'])

    def test_ground_floor_area_is_70(self):
        model = json.loads((self.output / '01_concept_digital_twin.json').read_text(encoding='utf-8'))
        self.assertAlmostEqual(70.0, sum(s['area_m2'] for s in model['spaces'] if s['level'] == 'ground_floor'))

    def test_upper_floor_area_is_70(self):
        model = json.loads((self.output / '01_concept_digital_twin.json').read_text(encoding='utf-8'))
        self.assertAlmostEqual(70.0, sum(s['area_m2'] for s in model['spaces'] if s['level'] == 'upper_floor'))

    def test_status_notice_is_hard_coded(self):
        self.assertEqual(STATUS_NOTICE, self.result['status_notice'])

    def test_final_generation_is_blocked(self):
        self.assertFalse(self.result['final_generation_allowed'])

    def test_bb36_is_locked(self):
        self.assertFalse(self.result['bb36_unlock_allowed'])

    def test_nine_structural_columns(self):
        model = json.loads((self.output / '01_concept_digital_twin.json').read_text(encoding='utf-8'))
        self.assertEqual(9, len(model['structural_concept']['columns']))

    def test_quantities_are_positive(self):
        with (self.output / '04_concept_quantities.csv').open(encoding='utf-8-sig') as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(all(float(row['quantity']) > 0 for row in rows))

    def test_cost_band_is_ordered(self):
        with (self.output / '06_concept_cost_band.csv').open(encoding='utf-8-sig') as handle:
            rows = list(csv.DictReader(handle))
        total = next(row for row in rows if row['cost_id'] == 'C-004')
        self.assertLess(float(total['amount_min_eur']), float(total['amount_max_eur']))

    def test_cost_is_marked_concept(self):
        text = (self.output / '06_concept_cost_band.csv').read_text(encoding='utf-8-sig')
        self.assertIn(STATUS_NOTICE, text)

    def test_all_six_pdfs_are_valid_headers(self):
        pdfs = sorted(self.output.glob('*.pdf'))
        self.assertEqual(6, len(pdfs))
        self.assertTrue(all(path.read_bytes().startswith(b'%PDF-1.4') for path in pdfs))

    def test_all_pdfs_contain_concept_notice(self):
        for path in self.output.glob('*.pdf'):
            self.assertIn(b'CONCEPT - NOT FOR EXECUTION OR SUBMISSION', path.read_bytes())

    def test_six_svg_drawings_exist(self):
        self.assertEqual(6, len(list(self.output.glob('*.svg'))))

    def test_obj_mass_model_has_eight_vertices(self):
        lines = (self.output / '15_concept_mass_model.obj').read_text(encoding='utf-8').splitlines()
        self.assertEqual(8, sum(1 for line in lines if line.startswith('v ')))

    def test_manifest_marks_final_blocked(self):
        manifest = json.loads((self.output / 'concept_package_manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['final_generation_allowed'])
        self.assertFalse(manifest['bb36_unlock_allowed'])

    def test_checksums_are_valid(self):
        for line in (self.output / 'checksums.sha256').read_text(encoding='utf-8').splitlines():
            digest, name = line.split('  ', 1)
            self.assertEqual(digest, hashlib.sha256((self.output / name).read_bytes()).hexdigest())

    def test_dossier_contains_core_outputs(self):
        with zipfile.ZipFile(self.output / 'BB35_PILOT_1_CONCEPT_PACKAGE_v1_3_3.zip') as archive:
            names = set(archive.namelist())
        self.assertIn('01_concept_digital_twin.json', names)
        self.assertIn('19_concept_floor_plans.pdf', names)
        self.assertIn('16_concept_technical_specification.md', names)
        self.assertIn('CONCEPT_README.txt', names)

    def test_dossier_uses_only_canonical_zip_stored_members(self):
        dossier = self.output / 'BB35_PILOT_1_CONCEPT_PACKAGE_v1_3_3.zip'
        with zipfile.ZipFile(dossier) as archive:
            infos = archive.infolist()
        self.assertGreater(len(infos), 20)
        self.assertTrue(
            all(info.compress_type == zipfile.ZIP_STORED for info in infos)
        )
        self.assertTrue(all(info.create_system == 3 for info in infos))
        self.assertTrue(all(info.create_version == 20 for info in infos))
        self.assertTrue(all(info.extract_version == 20 for info in infos))
        self.assertTrue(all(info.flag_bits == 0 for info in infos))
        self.assertTrue(all(info.extra == b'' for info in infos))
        self.assertTrue(all(info.comment == b'' for info in infos))

    def test_windows_default_zipinfo_simulation_is_byte_identical(self):
        original_zip_info = zipfile.ZipInfo

        class WindowsDefaultZipInfo(original_zip_info):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.create_system = 0

        with tempfile.TemporaryDirectory() as tmp:
            normal_root = Path(tmp) / 'normal'
            windows_root = Path(tmp) / 'windows_simulated'
            normal = MoskeeBunschotenConceptGenerator().generate(
                config=self.config,
                verified_inputs=self.verified,
                output_dir=normal_root,
            )
            with unittest.mock.patch(
                'phoenix.bb35_pilots.moskee_bunschoten.'
                'concept_generation.zipfile.ZipInfo',
                WindowsDefaultZipInfo,
            ):
                windows = MoskeeBunschotenConceptGenerator().generate(
                    config=self.config,
                    verified_inputs=self.verified,
                    output_dir=windows_root,
                )
            self.assertEqual(
                normal['generator_version'],
                windows['generator_version'],
            )
            self.assertEqual(
                (normal_root / 'BB35_PILOT_1_CONCEPT_PACKAGE_v1_3_3.zip').read_bytes(),
                (windows_root / 'BB35_PILOT_1_CONCEPT_PACKAGE_v1_3_3.zip').read_bytes(),
            )

    def test_output_count_at_least_25(self):
        self.assertGreaterEqual(self.result['output_count'], 25)

    def test_generator_version_is_1_3_3(self):
        self.assertEqual('1.3.3', self.result['generator_version'])

    def test_lf_controlled_text_outputs_have_no_crlf(self):
        controlled_suffixes = {'.json', '.svg', '.obj', '.md', '.html', '.sha256'}
        controlled_names = {'checksums.sha256'}
        for path in self.output.iterdir():
            if path.suffix in controlled_suffixes or path.name in controlled_names:
                self.assertNotIn(b'\r\n', path.read_bytes(), path.name)

    def test_two_independent_generations_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as other_tmp:
            other = Path(other_tmp)
            MoskeeBunschotenConceptGenerator().generate(
                config=self.config, verified_inputs=self.verified, output_dir=other
            )
            first = {
                p.relative_to(self.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.output.rglob('*') if p.is_file()
            }
            second = {
                p.relative_to(other).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in other.rglob('*') if p.is_file()
            }
            self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
