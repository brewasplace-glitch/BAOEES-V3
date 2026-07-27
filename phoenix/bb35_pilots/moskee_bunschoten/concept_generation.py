\
"""Dependency-free concept package generator for BB35 Pilot 1."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from .simple_pdf import SimplePDF


STATUS_NOTICE = 'CONCEPT - NOT FOR EXECUTION OR SUBMISSION'
_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class MoskeeBunschotenConceptGenerator:
    VERSION = '1.3.3'
    SCHEMA_VERSION = 'phoenix.bb35.moskee-concept-package/1.0'

    def generate(
        self,
        *,
        config: Mapping[str, Any],
        verified_inputs: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Any]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        scope = dict(config['project']['authoritative_scope'])
        self._validate_scope(scope)
        assumptions = self._assumptions()
        spaces = self._spaces()
        structural = self._structural_concept(scope)
        quantities = self._quantities(scope, spaces, structural)
        cost = self._cost_band(scope)
        materials = self._materials()
        permits = self._permit_register()
        risks = self._risks()
        model = self._digital_twin(
            config=config,
            scope=scope,
            assumptions=assumptions,
            spaces=spaces,
            structural=structural,
            quantities=quantities,
            cost=cost,
            materials=materials,
            permits=permits,
            risks=risks,
        )

        paths: dict[str, Path] = {}
        paths['model_json'] = self._write_json(root / '01_concept_digital_twin.json', model)
        paths['assumptions_json'] = self._write_json(
            root / '02_assumptions_register.json',
            {'status_notice': STATUS_NOTICE, 'assumptions': assumptions},
        )
        paths['spaces_csv'] = self._write_csv(
            root / '03_space_schedule.csv',
            spaces,
            ['space_id', 'level', 'name', 'x_m', 'y_m', 'width_m', 'depth_m', 'area_m2', 'status'],
        )
        paths['quantities_csv'] = self._write_csv(
            root / '04_concept_quantities.csv',
            quantities,
            ['item_id', 'category', 'description', 'unit', 'quantity', 'basis', 'status'],
        )
        paths['materials_csv'] = self._write_csv(
            root / '05_concept_material_schedule.csv',
            materials,
            ['material_id', 'category', 'concept_material', 'scope', 'verification_required', 'status'],
        )
        paths['cost_csv'] = self._write_csv(
            root / '06_concept_cost_band.csv',
            cost['rows'],
            ['cost_id', 'description', 'amount_min_eur', 'amount_max_eur', 'basis', 'status'],
        )
        paths['permit_csv'] = self._write_csv(
            root / '07_permit_research_register.csv',
            permits,
            ['item_id', 'discipline', 'requirement', 'current_status', 'blocking_final', 'responsible_party'],
        )
        paths['risk_csv'] = self._write_csv(
            root / '08_concept_risk_register.csv',
            risks,
            ['risk_id', 'category', 'risk', 'impact', 'mitigation', 'status'],
        )

        svg_files = self._write_svgs(root, scope, spaces, structural)
        paths.update(svg_files)
        paths['obj_model'] = self._write_obj(root / '15_concept_mass_model.obj', scope)
        paths['bestek_md'] = self._write_text(root / '16_concept_technical_specification.md', self._specification_md(config, assumptions, materials))
        paths['report_html'] = self._write_text(root / '17_concept_package_report.html', self._report_html(config, scope, cost, risks, permits))

        pdf_files = self._write_pdfs(root, config, scope, spaces, structural, quantities, cost, assumptions, risks, permits)
        paths.update(pdf_files)

        paths['checksums'] = self._write_checksums(paths, root / 'checksums.sha256')
        manifest = self._manifest(config, paths)
        paths['manifest'] = self._write_json(root / 'concept_package_manifest.json', manifest)
        # Refresh checksums to include manifest.
        paths['checksums'] = self._write_checksums(paths, root / 'checksums.sha256')
        paths['dossier'] = self._write_dossier(paths, root / 'BB35_PILOT_1_CONCEPT_PACKAGE_v1_3_3.zip')

        return {
            'schema_version': self.SCHEMA_VERSION,
            'generator_version': self.VERSION,
            'pilot_id': config['pilot_id'],
            'project_id': config['project']['project_id'],
            'status': 'CONCEPT_PACKAGE_READY_PENDING_EXTERNAL_TECHNICAL_EVIDENCE',
            'status_notice': STATUS_NOTICE,
            'scope': scope,
            'space_count': len(spaces),
            'gross_area_m2': round(sum(float(item['area_m2']) for item in spaces), 2),
            'assumption_count': len(assumptions),
            'risk_count': len(risks),
            'permit_item_count': len(permits),
            'output_count': len(paths),
            'final_generation_allowed': False,
            'bb36_unlock_allowed': False,
            'outputs': {key: str(value) for key, value in sorted(paths.items())},
        }

    @staticmethod
    def _validate_scope(scope: Mapping[str, Any]) -> None:
        expected = {
            'selected_option': 'B',
            'extension_width_m': 7.0,
            'extension_depth_m': 10.0,
            'extension_footprint_m2': 70.0,
            'number_of_extension_storeys': 2,
            'gross_extension_area_m2': 140.0,
        }
        mismatches = [key for key, value in expected.items() if scope.get(key) != value]
        if mismatches:
            raise ValueError('Authoritative scope mismatch: ' + ', '.join(mismatches))

    @staticmethod
    def _assumptions() -> list[dict[str, Any]]:
        return [
            {'assumption_id': 'A-001', 'category': 'status', 'statement': STATUS_NOTICE, 'confidence': 'authoritative', 'requires_verification': False},
            {'assumption_id': 'A-002', 'category': 'geometry', 'statement': 'Extension footprint is 7.00 x 10.00 m.', 'confidence': 'authoritative', 'requires_verification': False},
            {'assumption_id': 'A-003', 'category': 'geometry', 'statement': 'Two extension storeys provide approximately 140 m2 gross floor area.', 'confidence': 'authoritative', 'requires_verification': False},
            {'assumption_id': 'A-004', 'category': 'levels', 'statement': 'Concept floor-to-floor height is 3.30 m.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-005', 'category': 'roof', 'statement': 'Concept roof is a low-slope roof behind a 0.60 m parapet.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-006', 'category': 'structure', 'statement': 'Preliminary structural option is a steel frame on a 3 x 3 column grid.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-007', 'category': 'structure', 'statement': 'Floor system is provisionally a lightweight composite or precast floor.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-008', 'category': 'foundation', 'statement': 'Foundation type is unresolved pending structural survey and geotechnical evidence.', 'confidence': 'unknown', 'requires_verification': True},
            {'assumption_id': 'A-009', 'category': 'existing_building', 'statement': 'No load is transferred to the existing building until the connection is professionally verified.', 'confidence': 'safety_rule', 'requires_verification': True},
            {'assumption_id': 'A-010', 'category': 'fire', 'statement': 'Fire resistance, compartmentation and escape routes require Bbl/fire-safety assessment.', 'confidence': 'unknown', 'requires_verification': True},
            {'assumption_id': 'A-011', 'category': 'occupancy', 'statement': 'Occupancy and prayer-place capacity remain external verified inputs.', 'confidence': 'unknown', 'requires_verification': True},
            {'assumption_id': 'A-012', 'category': 'parking', 'statement': 'Available parking information is preliminary and not field-verified.', 'confidence': 'preliminary', 'requires_verification': True},
            {'assumption_id': 'A-013', 'category': 'aerius', 'statement': 'No final AERIUS result is generated without verified activity and traffic data.', 'confidence': 'safety_rule', 'requires_verification': True},
            {'assumption_id': 'A-014', 'category': 'materials', 'statement': 'Material selections are concept placeholders and may not be procured.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-015', 'category': 'cost', 'statement': 'Cost band uses illustrative planning allowances, not market-verified quotations.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-016', 'category': 'site', 'statement': 'Site plan is schematic until the original cadastral DWG or survey base is supplied.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-017', 'category': 'drawings', 'statement': 'Room boundaries are reconstructed conceptually from available overview plans.', 'confidence': 'concept', 'requires_verification': True},
            {'assumption_id': 'A-018', 'category': 'quality', 'statement': 'Every output must retain the concept status notice.', 'confidence': 'authoritative', 'requires_verification': False},
        ]

    @staticmethod
    def _spaces() -> list[dict[str, Any]]:
        rows = [
            ('GF-01', 'ground_floor', 'Prayer / meeting room', 0.0, 0.0, 4.8, 7.0),
            ('GF-02', 'ground_floor', 'Conference room', 4.8, 0.0, 2.2, 4.8),
            ('GF-03', 'ground_floor', 'Main entrance', 4.8, 4.8, 2.2, 1.6),
            ('GF-04', 'ground_floor', 'Ablution room', 4.8, 6.4, 2.2, 2.1),
            ('GF-05', 'ground_floor', 'Toilets', 4.8, 8.5, 2.2, 1.5),
            ('GF-06', 'ground_floor', 'Connection / circulation', 0.0, 7.0, 4.8, 3.0),
            ('UF-01', 'upper_floor', 'Ladies prayer room', 0.0, 0.0, 4.8, 5.5),
            ('UF-02', 'upper_floor', 'Classroom 1', 4.8, 0.0, 2.2, 2.7),
            ('UF-03', 'upper_floor', 'Classroom 2', 4.8, 2.7, 2.2, 2.8),
            ('UF-04', 'upper_floor', 'Void', 0.0, 5.5, 2.4, 2.5),
            ('UF-05', 'upper_floor', 'Landing / circulation', 2.4, 5.5, 2.4, 2.5),
            ('UF-06', 'upper_floor', 'Ablution room', 4.8, 5.5, 2.2, 2.5),
            ('UF-07', 'upper_floor', 'Storage', 0.0, 8.0, 2.4, 2.0),
            ('UF-08', 'upper_floor', 'Upper circulation', 2.4, 8.0, 2.4, 2.0),
            ('UF-09', 'upper_floor', 'Toilet', 4.8, 8.0, 2.2, 2.0),
        ]
        return [
            {
                'space_id': item[0], 'level': item[1], 'name': item[2],
                'x_m': item[3], 'y_m': item[4], 'width_m': item[5], 'depth_m': item[6],
                'area_m2': round(item[5] * item[6], 2), 'status': STATUS_NOTICE,
            }
            for item in rows
        ]

    @staticmethod
    def _structural_concept(scope: Mapping[str, Any]) -> dict[str, Any]:
        x_grid = [0.0, 3.5, 7.0]
        y_grid = [0.0, 5.0, 10.0]
        columns = [
            {'column_id': f'C-{ix+1}{iy+1}', 'x_m': x, 'y_m': y, 'height_m': 6.6}
            for ix, x in enumerate(x_grid)
            for iy, y in enumerate(y_grid)
        ]
        return {
            'status': STATUS_NOTICE,
            'option_id': 'S1',
            'system': 'Preliminary independent steel frame',
            'steel_grade_assumption': 'S355 concept only',
            'floor_system_assumption': 'Composite or precast floor - unresolved',
            'roof_system_assumption': 'Lightweight low-slope roof - unresolved',
            'foundation_assumption': 'Pad/strip or alternative subject to geotechnical design',
            'connection_rule': 'No verified load transfer to existing building',
            'grid_x_m': x_grid,
            'grid_y_m': y_grid,
            'columns': columns,
            'storey_heights_m': [3.3, 3.3],
            'gross_area_m2': scope['gross_extension_area_m2'],
        }

    @staticmethod
    def _quantities(scope: Mapping[str, Any], spaces: list[dict[str, Any]], structural: Mapping[str, Any]) -> list[dict[str, Any]]:
        width = float(scope['extension_width_m'])
        depth = float(scope['extension_depth_m'])
        storeys = int(scope['number_of_extension_storeys'])
        height = sum(float(value) for value in structural['storey_heights_m'])
        perimeter = 2.0 * (width + depth)
        gross_wall = perimeter * height
        opening_ratio = 0.18
        rows = [
            ('Q-001', 'area', 'Gross extension floor area', 'm2', width * depth * storeys, '7 x 10 x 2'),
            ('Q-002', 'area', 'Roof area', 'm2', width * depth, '7 x 10'),
            ('Q-003', 'envelope', 'Gross external wall area', 'm2', gross_wall, 'perimeter x 6.60'),
            ('Q-004', 'envelope', 'Concept net opaque facade area', 'm2', gross_wall * (1.0 - opening_ratio), 'gross facade less 18% openings'),
            ('Q-005', 'envelope', 'Concept external openings', 'm2', gross_wall * opening_ratio, '18% opening allowance'),
            ('Q-006', 'structure', 'Concept steel columns', 'm', len(structural['columns']) * height, '9 columns x 6.60'),
            ('Q-007', 'structure', 'Concept beam grid length', 'm', 102.0, '51 m per level x 2'),
            ('Q-008', 'foundation', 'Concept foundation positions', 'nr', len(structural['columns']), 'one position per grid column'),
            ('Q-009', 'foundation', 'Concept ground-beam grid', 'm', 51.0, '3 x 10 m plus 3 x 7 m'),
            ('Q-010', 'partitions', 'Concept internal partition allowance', 'm2', 110.0, 'reconstructed room layout allowance'),
            ('Q-011', 'finishes', 'Floor finish area', 'm2', width * depth * storeys, 'gross floor area'),
            ('Q-012', 'ceilings', 'Ceiling finish area', 'm2', width * depth * storeys, 'gross floor area'),
        ]
        return [
            {
                'item_id': row[0], 'category': row[1], 'description': row[2],
                'unit': row[3], 'quantity': round(float(row[4]), 2), 'basis': row[5],
                'status': STATUS_NOTICE,
            }
            for row in rows
        ]

    @staticmethod
    def _cost_band(scope: Mapping[str, Any]) -> dict[str, Any]:
        area = float(scope['gross_extension_area_m2'])
        base_min_rate = 2200.0
        base_max_rate = 3400.0
        base_min = area * base_min_rate
        base_max = area * base_max_rate
        design_allowance_min = base_min * 0.12
        design_allowance_max = base_max * 0.18
        risk_min = base_min * 0.15
        risk_max = base_max * 0.25
        total_min = base_min + design_allowance_min + risk_min
        total_max = base_max + design_allowance_max + risk_max
        rows = [
            {'cost_id': 'C-001', 'description': 'Illustrative construction allowance', 'amount_min_eur': round(base_min, 2), 'amount_max_eur': round(base_max, 2), 'basis': '140 m2 x EUR 2,200-3,400/m2 illustrative only', 'status': STATUS_NOTICE},
            {'cost_id': 'C-002', 'description': 'Design, engineering and permit allowance', 'amount_min_eur': round(design_allowance_min, 2), 'amount_max_eur': round(design_allowance_max, 2), 'basis': '12%-18% planning allowance', 'status': STATUS_NOTICE},
            {'cost_id': 'C-003', 'description': 'Risk and unknown-input allowance', 'amount_min_eur': round(risk_min, 2), 'amount_max_eur': round(risk_max, 2), 'basis': '15%-25% due to unresolved evidence', 'status': STATUS_NOTICE},
            {'cost_id': 'C-004', 'description': 'Total concept planning band', 'amount_min_eur': round(total_min, 2), 'amount_max_eur': round(total_max, 2), 'basis': 'not market verified; replace after technical design and quotations', 'status': STATUS_NOTICE},
        ]
        return {'rows': rows, 'total_min_eur': round(total_min, 2), 'total_max_eur': round(total_max, 2)}

    @staticmethod
    def _materials() -> list[dict[str, Any]]:
        rows = [
            ('M-001', 'primary_structure', 'Steel frame - grade/profile unresolved', 'columns and beams', True),
            ('M-002', 'floor', 'Composite or precast floor - unresolved', 'upper floor', True),
            ('M-003', 'roof', 'Lightweight insulated low-slope roof', 'roof', True),
            ('M-004', 'facade', 'Insulated masonry or rainscreen concept', 'external walls', True),
            ('M-005', 'glazing', 'Thermally insulated glazing concept', 'windows and entrance', True),
            ('M-006', 'internal_walls', 'Lightweight partitions / masonry mix', 'room separation', True),
            ('M-007', 'wet_rooms', 'Water-resistant finishes and drainage', 'ablution and toilets', True),
            ('M-008', 'fire', 'Fire-rated materials subject to fire strategy', 'escape and compartmentation', True),
            ('M-009', 'foundation', 'Reinforced concrete concept only', 'foundations and ground beams', True),
        ]
        return [
            {'material_id': r[0], 'category': r[1], 'concept_material': r[2], 'scope': r[3], 'verification_required': r[4], 'status': STATUS_NOTICE}
            for r in rows
        ]

    @staticmethod
    def _permit_register() -> list[dict[str, Any]]:
        rows = [
            ('P-001', 'planning', 'BOPA/ETFAL and Omgevingsplan assessment for 140 m2 scope', 'brief available; report pending', True, 'spatial-planning consultant'),
            ('P-002', 'building_code', 'Bbl assessment: use, occupancy, escape, fire, daylight, ventilation, accessibility', 'brief available; assessment pending', True, 'Bbl/fire advisor'),
            ('P-003', 'structure', 'Structural calculations and report', 'blocked by survey and geotechnical inputs', True, 'structural engineer'),
            ('P-004', 'traffic', 'Parking, traffic generation and participation', 'preliminary only; field evidence pending', True, 'traffic consultant'),
            ('P-005', 'nitrogen', 'AERIUS construction and operation phases', 'activity data pending', True, 'AERIUS/spatial consultant'),
            ('P-006', 'site', 'Definitive site plan and parcel boundaries', 'original cadastral DWG pending', True, 'architect/surveyor'),
            ('P-007', 'coordination', 'Complete Omgevingsloket submission dossier', 'not ready', True, 'permit coordinator'),
        ]
        return [
            {'item_id': r[0], 'discipline': r[1], 'requirement': r[2], 'current_status': r[3], 'blocking_final': r[4], 'responsible_party': r[5]}
            for r in rows
        ]

    @staticmethod
    def _risks() -> list[dict[str, Any]]:
        rows = [
            ('R-001', 'existing_building', 'Unknown existing load path and connection capacity', 'critical', 'Complete structural survey before final design'),
            ('R-002', 'geotechnical', 'Unknown soil and settlement behaviour', 'critical', 'Obtain project-specific ground investigation'),
            ('R-003', 'site', 'No original cadastral/survey base in controlled evidence', 'high', 'Supply DWG/DXF and survey verification'),
            ('R-004', 'fire', 'Occupancy and fire strategy not agreed', 'critical', 'Complete Bbl/fire assessment'),
            ('R-005', 'parking', 'Parking capacity and public/private rights are not field verified', 'high', 'Perform counts and secure written use agreements where needed'),
            ('R-006', 'aerius', 'Construction and operational activity data unavailable', 'high', 'Prepare verified activity schedule'),
            ('R-007', 'cost', 'Concept rates are not market quotations', 'high', 'Replace with measured quantities and supplier/contractor pricing'),
            ('R-008', 'scope_coordination', 'Legacy 20 m2 references may remain outside controlled records', 'high', 'Use only the authoritative 140 m2 scope register'),
            ('R-009', 'design', 'Room layout reconstructed from overview drawings', 'medium', 'Complete measured DO/TO architectural design'),
        ]
        return [
            {'risk_id': r[0], 'category': r[1], 'risk': r[2], 'impact': r[3], 'mitigation': r[4], 'status': 'open - ' + STATUS_NOTICE}
            for r in rows
        ]

    def _digital_twin(self, **kwargs: Any) -> dict[str, Any]:
        config = kwargs['config']
        return {
            'schema_version': self.SCHEMA_VERSION,
            'generator_version': self.VERSION,
            'status': STATUS_NOTICE,
            'project': config['project'],
            'levels': [
                {'level_id': 'GF', 'name': 'Ground floor', 'elevation_m': 0.0, 'height_m': 3.3},
                {'level_id': 'UF', 'name': 'Upper floor', 'elevation_m': 3.3, 'height_m': 3.3},
                {'level_id': 'RF', 'name': 'Roof', 'elevation_m': 6.6, 'height_m': 0.6},
            ],
            'spaces': kwargs['spaces'],
            'structural_concept': kwargs['structural'],
            'assumptions': kwargs['assumptions'],
            'quantities': kwargs['quantities'],
            'cost_band': kwargs['cost'],
            'materials': kwargs['materials'],
            'permit_register': kwargs['permits'],
            'risk_register': kwargs['risks'],
            'release': {'final_generation_allowed': False, 'bb36_unlock_allowed': False},
        }

    def _write_svgs(self, root: Path, scope: Mapping[str, Any], spaces: list[dict[str, Any]], structural: Mapping[str, Any]) -> dict[str, Path]:
        paths = {
            'svg_ground': root / '09_ground_floor_concept.svg',
            'svg_upper': root / '10_upper_floor_concept.svg',
            'svg_site': root / '11_schematic_site_plan.svg',
            'svg_elevations': root / '12_elevations_and_section.svg',
            'svg_structure': root / '13_structural_grid_concept.svg',
            'svg_3d': root / '14_axonometric_concept.svg',
        }
        self._floor_svg(paths['svg_ground'], [s for s in spaces if s['level'] == 'ground_floor'], 'GROUND FLOOR CONCEPT')
        self._floor_svg(paths['svg_upper'], [s for s in spaces if s['level'] == 'upper_floor'], 'UPPER FLOOR CONCEPT')
        self._site_svg(paths['svg_site'])
        self._elevation_svg(paths['svg_elevations'])
        self._structural_svg(paths['svg_structure'], structural)
        self._axonometric_svg(paths['svg_3d'])
        return paths

    @staticmethod
    def _svg_header(width: int = 1200, height: int = 800) -> str:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'

    def _floor_svg(self, path: Path, spaces: list[dict[str, Any]], title: str) -> None:
        scale = 60.0
        ox, oy = 120.0, 100.0
        parts = [self._svg_header(), '<rect width="100%" height="100%" fill="white"/>', f'<text x="40" y="45" font-family="Arial" font-size="28" font-weight="bold">{html.escape(title)}</text>', f'<text x="40" y="75" font-family="Arial" font-size="16">{STATUS_NOTICE}</text>']
        parts.append(f'<rect x="{ox}" y="{oy}" width="{7*scale}" height="{10*scale}" fill="none" stroke="black" stroke-width="4"/>')
        for index, space in enumerate(spaces):
            x = ox + float(space['x_m']) * scale
            y = oy + float(space['y_m']) * scale
            w = float(space['width_m']) * scale
            h = float(space['depth_m']) * scale
            fill = '#f2f2f2' if index % 2 == 0 else '#ffffff'
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="black" stroke-width="2"/>')
            label = html.escape(str(space['name']))
            parts.append(f'<text x="{x+8}" y="{y+22}" font-family="Arial" font-size="14">{label}</text>')
            parts.append(f'<text x="{x+8}" y="{y+42}" font-family="Arial" font-size="12">{space["area_m2"]:.2f} m2</text>')
        parts.extend([
            f'<line x1="{ox}" y1="{oy+10*scale+35}" x2="{ox+7*scale}" y2="{oy+10*scale+35}" stroke="black"/>',
            f'<text x="{ox+3.1*scale}" y="{oy+10*scale+60}" font-family="Arial" font-size="14">7.00 m</text>',
            f'<line x1="{ox+7*scale+35}" y1="{oy}" x2="{ox+7*scale+35}" y2="{oy+10*scale}" stroke="black"/>',
            f'<text x="{ox+7*scale+45}" y="{oy+5*scale}" font-family="Arial" font-size="14">10.00 m</text>',
            '</svg>',
        ])
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(parts))

    def _site_svg(self, path: Path) -> None:
        parts = [self._svg_header(), '<rect width="100%" height="100%" fill="white"/>', '<text x="40" y="45" font-family="Arial" font-size="28" font-weight="bold">SCHEMATIC SITE PLAN</text>', f'<text x="40" y="75" font-family="Arial" font-size="16">{STATUS_NOTICE} - cadastral DWG pending</text>', '<rect x="140" y="120" width="760" height="520" fill="none" stroke="black" stroke-width="3" stroke-dasharray="12 8"/>', '<text x="150" y="145" font-family="Arial" font-size="15">Indicative project area - not a cadastral boundary</text>', '<rect x="310" y="260" width="360" height="210" fill="#e8e8e8" stroke="black" stroke-width="3"/>', '<text x="390" y="365" font-family="Arial" font-size="18">EXISTING MOSQUE MASS</text>', '<rect x="670" y="330" width="140" height="200" fill="#d6e4ff" stroke="black" stroke-width="3"/>', '<text x="690" y="430" font-family="Arial" font-size="16" transform="rotate(90 690 430)">7 x 10 m EXTENSION</text>', '<line x1="1040" y1="180" x2="1040" y2="100" stroke="black" stroke-width="4"/>', '<polygon points="1040,75 1025,105 1055,105" fill="black"/>', '<text x="1032" y="60" font-family="Arial" font-size="18">N</text>', '<text x="40" y="745" font-family="Arial" font-size="14">Required next: original cadastral DWG or surveyed site base, parcel dimensions, setbacks and utilities.</text>', '</svg>']
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(parts))

    def _elevation_svg(self, path: Path) -> None:
        parts = [self._svg_header(), '<rect width="100%" height="100%" fill="white"/>', '<text x="40" y="45" font-family="Arial" font-size="28" font-weight="bold">CONCEPT ELEVATIONS AND SECTION</text>', f'<text x="40" y="75" font-family="Arial" font-size="16">{STATUS_NOTICE}</text>']
        for i, (x, label, width) in enumerate([(70, 'FRONT 7.00 m', 300), (450, 'SIDE 10.00 m', 430)]):
            parts.append(f'<rect x="{x}" y="170" width="{width}" height="300" fill="none" stroke="black" stroke-width="3"/>')
            parts.append(f'<line x1="{x}" y1="320" x2="{x+width}" y2="320" stroke="black" stroke-width="2"/>')
            parts.append(f'<rect x="{x+35}" y="210" width="70" height="90" fill="none" stroke="black"/>')
            parts.append(f'<rect x="{x+width-105}" y="210" width="70" height="90" fill="none" stroke="black"/>')
            parts.append(f'<rect x="{x+35}" y="355" width="70" height="80" fill="none" stroke="black"/>')
            parts.append(f'<rect x="{x+width-105}" y="355" width="70" height="80" fill="none" stroke="black"/>')
            parts.append(f'<text x="{x}" y="505" font-family="Arial" font-size="16">{label}</text>')
        parts.extend(['<text x="70" y="560" font-family="Arial" font-size="14">Level 0.00</text>', '<text x="70" y="585" font-family="Arial" font-size="14">Upper floor +3.30 m</text>', '<text x="70" y="610" font-family="Arial" font-size="14">Roof +6.60 m; concept parapet +0.60 m</text>', '<text x="70" y="670" font-family="Arial" font-size="14">Facade composition, openings and connection to existing building require DO/TO verification.</text>', '</svg>'])
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(parts))

    def _structural_svg(self, path: Path, structural: Mapping[str, Any]) -> None:
        scale = 55.0
        ox, oy = 130.0, 110.0
        parts = [self._svg_header(), '<rect width="100%" height="100%" fill="white"/>', '<text x="40" y="45" font-family="Arial" font-size="28" font-weight="bold">PRELIMINARY STRUCTURAL GRID S1</text>', f'<text x="40" y="75" font-family="Arial" font-size="16">{STATUS_NOTICE}</text>']
        for x in structural['grid_x_m']:
            sx = ox + float(x) * scale
            parts.append(f'<line x1="{sx}" y1="{oy}" x2="{sx}" y2="{oy+10*scale}" stroke="black" stroke-width="2"/>')
        for y in structural['grid_y_m']:
            sy = oy + float(y) * scale
            parts.append(f'<line x1="{ox}" y1="{sy}" x2="{ox+7*scale}" y2="{sy}" stroke="black" stroke-width="2"/>')
        for column in structural['columns']:
            cx = ox + float(column['x_m']) * scale
            cy = oy + float(column['y_m']) * scale
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="black"/>')
            parts.append(f'<text x="{cx+10}" y="{cy-10}" font-family="Arial" font-size="12">{column["column_id"]}</text>')
        parts.extend(['<text x="620" y="180" font-family="Arial" font-size="16">Concept system:</text>', '<text x="620" y="215" font-family="Arial" font-size="14">Independent steel frame</text>', '<text x="620" y="245" font-family="Arial" font-size="14">3 x 3 column grid</text>', '<text x="620" y="275" font-family="Arial" font-size="14">Floor/roof systems unresolved</text>', '<text x="620" y="305" font-family="Arial" font-size="14">Foundation unresolved</text>', '<text x="620" y="350" font-family="Arial" font-size="14">No final member sizes.</text>', '<text x="620" y="380" font-family="Arial" font-size="14">No verified load transfer</text>', '<text x="620" y="405" font-family="Arial" font-size="14">to existing building.</text>', '</svg>'])
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(parts))

    def _axonometric_svg(self, path: Path) -> None:
        parts = [self._svg_header(), '<rect width="100%" height="100%" fill="white"/>', '<text x="40" y="45" font-family="Arial" font-size="28" font-weight="bold">CONCEPT 3D MASSING - 7 x 10 m / TWO STOREYS</text>', f'<text x="40" y="75" font-family="Arial" font-size="16">{STATUS_NOTICE}</text>', '<polygon points="300,520 650,620 880,490 530,390" fill="#e8e8e8" stroke="black" stroke-width="3"/>', '<polygon points="300,260 650,360 650,620 300,520" fill="#dce6f2" stroke="black" stroke-width="3"/>', '<polygon points="650,360 880,230 880,490 650,620" fill="#cfd9e6" stroke="black" stroke-width="3"/>', '<polygon points="300,260 530,130 880,230 650,360" fill="#f1f1f1" stroke="black" stroke-width="3"/>', '<line x1="300" y1="390" x2="650" y2="490" stroke="black" stroke-width="2"/>', '<line x1="650" y1="490" x2="880" y2="360" stroke="black" stroke-width="2"/>', '<text x="320" y="680" font-family="Arial" font-size="16">Massing only - facade, roof, structure and existing-building connection require verification.</text>', '</svg>']
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(parts))

    @staticmethod
    def _write_obj(path: Path, scope: Mapping[str, Any]) -> Path:
        w = float(scope['extension_width_m'])
        d = float(scope['extension_depth_m'])
        h = 6.6
        vertices = [(0,0,0),(w,0,0),(w,d,0),(0,d,0),(0,0,h),(w,0,h),(w,d,h),(0,d,h)]
        faces = [(1,2,3,4),(5,8,7,6),(1,5,6,2),(2,6,7,3),(3,7,8,4),(4,8,5,1)]
        lines = [f'# {STATUS_NOTICE}', '# PROJECT-PHOENIX BB35 Pilot 1 concept mass model']
        lines.extend(f'v {x:.3f} {y:.3f} {z:.3f}' for x,y,z in vertices)
        lines.extend('f ' + ' '.join(str(index) for index in face) for face in faces)
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(lines) + '\n')
        return path

    def _write_pdfs(self, root: Path, config: Mapping[str, Any], scope: Mapping[str, Any], spaces: list[dict[str, Any]], structural: Mapping[str, Any], quantities: list[dict[str, Any]], cost: Mapping[str, Any], assumptions: list[dict[str, Any]], risks: list[dict[str, Any]], permits: list[dict[str, Any]]) -> dict[str, Path]:
        paths = {
            'pdf_report': root / '18_concept_project_report.pdf',
            'pdf_plans': root / '19_concept_floor_plans.pdf',
            'pdf_elevations': root / '20_concept_elevations_sections.pdf',
            'pdf_site': root / '21_schematic_site_plan.pdf',
            'pdf_structure': root / '22_preliminary_structural_concept.pdf',
            'pdf_cost': root / '23_concept_quantities_cost_summary.pdf',
        }
        self._pdf_report(paths['pdf_report'], config, scope, assumptions, risks, permits)
        self._pdf_plans(paths['pdf_plans'], spaces)
        self._pdf_elevations(paths['pdf_elevations'])
        self._pdf_site(paths['pdf_site'])
        self._pdf_structure(paths['pdf_structure'], structural)
        self._pdf_cost(paths['pdf_cost'], quantities, cost)
        return paths

    @staticmethod
    def _title(page: Any, title: str, subtitle: str = '') -> None:
        page.text(36, page.height - 36, title, 18)
        page.text(36, page.height - 60, STATUS_NOTICE, 10)
        if subtitle:
            page.text(36, page.height - 78, subtitle, 9)
        page.line(36, page.height - 88, page.width - 36, page.height - 88, 1.0)

    @staticmethod
    def _wrapped(page: Any, x: float, y: float, text: str, width_chars: int = 95, size: float = 9.0, leading: float = 13.0) -> float:
        for line in textwrap.wrap(text, width=width_chars) or ['']:
            page.text(x, y, line, size)
            y -= leading
        return y

    def _pdf_report(self, path: Path, config: Mapping[str, Any], scope: Mapping[str, Any], assumptions: list[dict[str, Any]], risks: list[dict[str, Any]], permits: list[dict[str, Any]]) -> None:
        pdf = SimplePDF()
        page = pdf.add_page()
        self._title(page, 'BB35 PILOT 1 - MOSKEE BUNSCHOTEN CONCEPT REPORT', 'Bikkersweg 88 - authoritative 7.00 x 10.00 m two-storey extension')
        y = 480
        page.text(45, y, 'Project basis', 13); y -= 22
        for line in [
            f"Project: {config['project']['project_name']}",
            f"Address: {config['project']['address']}",
            f"Footprint: {scope['extension_footprint_m2']:.2f} m2",
            f"Storeys: {scope['number_of_extension_storeys']}",
            f"Gross extension: {scope['gross_extension_area_m2']:.2f} m2",
        ]:
            page.text(55, y, line, 10); y -= 17
        y -= 8
        page.text(45, y, 'Release statement', 13); y -= 22
        y = self._wrapped(page, 55, y, 'This package is a coordinated concept evidence set. It is not a structural design, permit submission, tender package or construction document. Final outputs remain blocked by external technical evidence.', 100, 10, 14)
        y -= 8
        page.text(45, y, 'Key unresolved evidence', 13); y -= 20
        for risk in risks[:6]:
            y = self._wrapped(page, 55, y, f"- {risk['risk']}", 100, 9, 12)
        page2 = pdf.add_page()
        self._title(page2, 'ASSUMPTIONS AND PERMIT GATES')
        y = 480
        for item in assumptions[:12]:
            y = self._wrapped(page2, 45, y, f"{item['assumption_id']}: {item['statement']}", 105, 8.5, 11)
        page3 = pdf.add_page()
        self._title(page3, 'PERMIT AND RESEARCH REGISTER')
        y = 480
        for item in permits:
            y = self._wrapped(page3, 45, y, f"{item['item_id']} - {item['discipline']}: {item['requirement']} | {item['current_status']}", 105, 8.5, 12)
        pdf.save(path)

    def _pdf_plans(self, path: Path, spaces: list[dict[str, Any]]) -> None:
        pdf = SimplePDF()
        for level, title in [('ground_floor', 'GROUND FLOOR CONCEPT PLAN'), ('upper_floor', 'UPPER FLOOR CONCEPT PLAN')]:
            page = pdf.add_page()
            self._title(page, title, 'Scale schematic - authoritative outer dimensions 7.00 x 10.00 m')
            ox, oy, scale = 110.0, 80.0, 38.0
            page.rect(ox, oy, 7*scale, 10*scale, 1.8)
            for index, space in enumerate([s for s in spaces if s['level'] == level]):
                x = ox + float(space['x_m']) * scale
                y = oy + float(space['y_m']) * scale
                w = float(space['width_m']) * scale
                h = float(space['depth_m']) * scale
                if index % 2 == 0:
                    page.fill_rect(x, y, w, h, 0.94)
                page.rect(x, y, w, h, 0.8)
                page.text(x+5, y+h-16, space['name'], 7.5)
                page.text(x+5, y+h-30, f"{space['area_m2']:.2f} m2", 7.0)
            page.line(ox, oy-28, ox+7*scale, oy-28)
            page.text(ox+125, oy-45, '7.00 m', 9)
            page.line(ox+7*scale+28, oy, ox+7*scale+28, oy+10*scale)
            page.text(ox+7*scale+38, oy+200, '10.00 m', 9)
            page.text(500, 420, 'Notes:', 11)
            page.text(500, 395, '- Room arrangement reconstructed conceptually.', 8)
            page.text(500, 377, '- Doors, stairs, structure and services unresolved.', 8)
            page.text(500, 359, '- Complete measured DO/TO design is required.', 8)
        pdf.save(path)

    def _pdf_elevations(self, path: Path) -> None:
        pdf = SimplePDF(); page = pdf.add_page(); self._title(page, 'CONCEPT ELEVATIONS AND SECTION')
        for x, width, label in [(70, 250, 'FRONT - 7.00 m'), (430, 330, 'SIDE - 10.00 m')]:
            page.rect(x, 170, width, 260, 1.4)
            page.line(x, 300, x+width, 300)
            for wx in (x+30, x+width-85):
                page.rect(wx, 195, 55, 75)
                page.rect(wx, 330, 55, 65)
            page.text(x, 450, label, 10)
        page.text(70, 125, 'Concept levels: GF 0.00 m | UF +3.30 m | roof +6.60 m | parapet +0.60 m', 9)
        page.text(70, 105, 'Openings, materials, fire separation and existing-building connection require verification.', 9)
        pdf.save(path)

    def _pdf_site(self, path: Path) -> None:
        pdf = SimplePDF(); page = pdf.add_page(); self._title(page, 'SCHEMATIC SITE PLAN', 'Original cadastral DWG / survey base is still required')
        page.rect(120, 110, 600, 380, 1.2)
        page.text(130, 470, 'Indicative project area - not a cadastral boundary', 9)
        page.fill_rect(250, 210, 280, 170, 0.92); page.rect(250, 210, 280, 170, 1.3)
        page.text(315, 295, 'EXISTING MOSQUE MASS', 12)
        page.fill_rect(530, 250, 100, 180, 0.85); page.rect(530, 250, 100, 180, 1.5)
        page.text(545, 330, '7 x 10 m', 10); page.text(545, 312, 'EXTENSION', 10)
        page.line(760, 420, 760, 500, 1.5); page.polyline([(750,485),(760,510),(770,485)], True, 1.2); page.text(753, 525, 'N', 12)
        page.text(120, 80, 'No parcel setbacks, utilities, parking rights or exact building position are certified in this concept.', 9)
        pdf.save(path)

    def _pdf_structure(self, path: Path, structural: Mapping[str, Any]) -> None:
        pdf = SimplePDF(); page = pdf.add_page(); self._title(page, 'PRELIMINARY STRUCTURAL CONCEPT S1')
        ox, oy, scale = 110.0, 80.0, 38.0
        for x in structural['grid_x_m']:
            sx = ox + float(x)*scale; page.line(sx, oy, sx, oy+10*scale, 1.0)
        for y in structural['grid_y_m']:
            sy = oy + float(y)*scale; page.line(ox, sy, ox+7*scale, sy, 1.0)
        for column in structural['columns']:
            cx = ox + float(column['x_m'])*scale; cy = oy + float(column['y_m'])*scale
            page.fill_rect(cx-4, cy-4, 8, 8, 0.0); page.text(cx+8, cy+8, column['column_id'], 7)
        page.text(500, 430, 'Selected concept option S1', 11)
        for idx, line in enumerate([
            'Independent steel frame',
            '3 x 3 column grid',
            'No member sizes released',
            'Floor and roof unresolved',
            'Foundation unresolved',
            'No verified load transfer to existing building',
            'Structural survey and geotechnical evidence required',
        ]):
            page.text(500, 400-idx*22, '- ' + line, 8.5)
        pdf.save(path)

    def _pdf_cost(self, path: Path, quantities: list[dict[str, Any]], cost: Mapping[str, Any]) -> None:
        pdf = SimplePDF(); page = pdf.add_page(); self._title(page, 'CONCEPT QUANTITY AND COST SUMMARY')
        y = 480
        page.text(45, y, 'Selected concept quantities', 12); y -= 24
        for item in quantities[:10]:
            page.text(55, y, f"{item['description']}: {item['quantity']:.2f} {item['unit']}", 8.5); y -= 16
        y -= 12; page.text(45, y, 'Illustrative cost band', 12); y -= 24
        for row in cost['rows']:
            page.text(55, y, f"{row['description']}: EUR {row['amount_min_eur']:,.0f} - EUR {row['amount_max_eur']:,.0f}", 8.5); y -= 18
        y -= 12
        page.text(45, y, 'These amounts are planning allowances only and are not market-verified quotations.', 9)
        page.text(45, y-20, 'Replace after measured design, professional engineering and contractor/supplier pricing.', 9)
        pdf.save(path)

    @staticmethod
    def _specification_md(config: Mapping[str, Any], assumptions: list[dict[str, Any]], materials: list[dict[str, Any]]) -> str:
        lines = [
            '# Concept Technical Specification', '', f'**{STATUS_NOTICE}**', '',
            f"Project: {config['project']['project_name']}",
            f"Address: {config['project']['address']}", '',
            '## 1. Scope',
            'Two-storey extension measuring 7.00 x 10.00 m with approximately 140 m2 gross floor area.', '',
            '## 2. General quality rule',
            'No part of this concept may be used for construction, procurement, permit submission or structural sizing.', '',
            '## 3. Concept materials',
        ]
        for item in materials:
            lines.append(f"- {item['category']}: {item['concept_material']} ({item['scope']}).")
        lines.extend(['', '## 4. Required professional verification'])
        for item in assumptions:
            if item['requires_verification']:
                lines.append(f"- {item['statement']}")
        lines.extend(['', '## 5. Execution hold point', 'Release for execution requires a signed technical design, calculations, specifications, drawings, permit evidence and an approved BB35 pilot acceptance record.', ''])
        return '\n'.join(lines)

    @staticmethod
    def _report_html(config: Mapping[str, Any], scope: Mapping[str, Any], cost: Mapping[str, Any], risks: list[dict[str, Any]], permits: list[dict[str, Any]]) -> str:
        risk_rows = ''.join(f"<tr><td>{html.escape(r['risk_id'])}</td><td>{html.escape(r['risk'])}</td><td>{html.escape(r['impact'])}</td></tr>" for r in risks)
        permit_rows = ''.join(f"<tr><td>{html.escape(p['discipline'])}</td><td>{html.escape(p['requirement'])}</td><td>{html.escape(p['current_status'])}</td></tr>" for p in permits)
        return (
            '<!doctype html><html lang="nl"><head><meta charset="utf-8">'
            '<title>BB35 Concept Package</title><style>'
            'body{font-family:Arial,sans-serif;max-width:1100px;margin:36px auto;color:#222}'
            'h1{border-bottom:3px solid #222}.notice{padding:14px;border:2px solid #8b0000;'
            'background:#fff4f4;font-weight:bold}table{border-collapse:collapse;width:100%;margin:18px 0}'
            'th,td{border:1px solid #aaa;padding:7px;text-align:left;vertical-align:top}'
            'th{background:#263238;color:white}</style></head><body>'
            f'<h1>{html.escape(config["project"]["project_name"])}</h1>'
            f'<div class="notice">{STATUS_NOTICE}</div>'
            f'<p><strong>Scope:</strong> 7.00 x 10.00 m, two storeys, {scope["gross_extension_area_m2"]:.0f} m2 gross.</p>'
            f'<p><strong>Concept planning band:</strong> EUR {cost["total_min_eur"]:,.0f} - EUR {cost["total_max_eur"]:,.0f}. This is not market verified.</p>'
            '<h2>Open risks</h2><table><thead><tr><th>ID</th><th>Risk</th><th>Impact</th></tr></thead><tbody>'
            + risk_rows
            + '</tbody></table><h2>Permit and research register</h2><table><thead><tr><th>Discipline</th><th>Requirement</th><th>Status</th></tr></thead><tbody>'
            + permit_rows
            + '</tbody></table><p>BB36 remains locked.</p></body></html>'
        )

    @staticmethod
    def _write_json(path: Path, value: Any) -> Path:
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
        return path

    @staticmethod
    def _write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> Path:
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\r\n')
            writer.writeheader(); writer.writerows(records)
        return path

    @staticmethod
    def _write_text(path: Path, value: str) -> Path:
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write(value)
        return path

    @staticmethod
    def _write_checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        lines = []
        for key, source in sorted(paths.items()):
            if key in {'checksums', 'dossier'} or source == destination:
                continue
            lines.append(f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}")
        with destination.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(lines) + '\n')
        return destination

    @staticmethod
    def _manifest(config: Mapping[str, Any], paths: Mapping[str, Path]) -> dict[str, Any]:
        records = []
        for key, path in sorted(paths.items()):
            if key in {'manifest', 'dossier'}:
                continue
            records.append({'output_id': key, 'file_name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size_bytes': path.stat().st_size})
        return {
            'schema_version': 'phoenix.bb35.concept-output-manifest/1.0',
            'pilot_id': config['pilot_id'],
            'project_id': config['project']['project_id'],
            'generator_version': '1.3.3',
            'status': STATUS_NOTICE,
            'final_generation_allowed': False,
            'bb36_unlock_allowed': False,
            'deterministic_text_newline': 'LF',
            'cross_platform_regression_fix': '1.3.3',
            'deterministic_dossier_zip_method': 'ZIP_STORED_CANONICAL_HEADERS',
            'outputs': records,
        }

    @staticmethod
    def _canonical_zip_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = 20
        info.reserved = 0
        info.flag_bits = 0
        info.volume = 0
        info.internal_attr = 0
        info.external_attr = 0o100644 << 16
        info.extra = b''
        info.comment = b''
        return info

    @classmethod
    def _write_dossier(cls, paths: Mapping[str, Path], destination: Path) -> Path:
        with zipfile.ZipFile(
            destination,
            'w',
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            archive.comment = b''
            for key, source in sorted(paths.items()):
                if key == 'dossier':
                    continue
                archive.writestr(
                    cls._canonical_zip_info(source.name),
                    source.read_bytes(),
                )
            archive.writestr(
                cls._canonical_zip_info('CONCEPT_README.txt'),
                (STATUS_NOTICE + '\nBB36 remains locked.\n').encode('utf-8'),
            )
        return destination
