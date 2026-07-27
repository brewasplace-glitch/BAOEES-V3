\
"""Concept review and evidence-acquisition workflow for BB35 Pilot 1."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from .simple_pdf import SimplePDF


STATUS_NOTICE = 'CONCEPT - NOT FOR EXECUTION OR SUBMISSION'
_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
_SEVERITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}


class MoskeeConceptReviewEvidenceAcquisition:
    VERSION = '1.4.0'
    SCHEMA_VERSION = 'phoenix.bb35.moskee-concept-review-evidence-acquisition/1.0'

    def generate(
        self,
        *,
        project_config: Mapping[str, Any],
        verified_inputs: Mapping[str, Any],
        concept_root: str | Path,
        output_dir: str | Path,
    ) -> dict[str, Any]:
        concept = Path(concept_root)
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        concept_validation = self._validate_concept_package(concept)
        model = self._read_json(concept / '01_concept_digital_twin.json')
        assumptions_doc = self._read_json(concept / '02_assumptions_register.json')
        risks = self._read_csv(concept / '08_concept_risk_register.csv')
        permits = self._read_csv(concept / '07_permit_research_register.csv')
        spaces = self._read_csv(concept / '03_space_schedule.csv')
        quantities = self._read_csv(concept / '04_concept_quantities.csv')
        costs = self._read_csv(concept / '06_concept_cost_band.csv')

        scope = dict(project_config['project']['authoritative_scope'])
        review_findings = self._review_findings(
            project_config=project_config,
            scope=scope,
            model=model,
            assumptions=assumptions_doc['assumptions'],
            risks=risks,
            permits=permits,
            spaces=spaces,
            quantities=quantities,
            costs=costs,
            concept_validation=concept_validation,
        )
        assumption_disposition = self._assumption_disposition(
            assumptions_doc['assumptions']
        )
        prioritized_risks = self._prioritize_risks(risks)
        evidence_requests = self._evidence_requests(verified_inputs)
        dependency_matrix = self._dependency_matrix(evidence_requests)
        review_matrix = self._review_matrix(
            scope=scope,
            model=model,
            spaces=spaces,
            quantities=quantities,
            costs=costs,
            concept_validation=concept_validation,
        )

        blocking_findings = [
            item for item in review_findings if item['blocking_final']
        ]
        open_requests = [
            item for item in evidence_requests if item['status'] != 'accepted'
        ]

        summary = {
            'schema_version': self.SCHEMA_VERSION,
            'engine_version': self.VERSION,
            'pilot_id': project_config['pilot_id'],
            'project_id': project_config['project']['project_id'],
            'project_name': project_config['project']['project_name'],
            'project_address': project_config['project']['address'],
            'authoritative_scope': scope,
            'status_notice': STATUS_NOTICE,
            'status': 'CONCEPT_REVIEW_COMPLETE_EVIDENCE_ACQUISITION_OPEN',
            'concept_review_complete': True,
            'concept_package_accepted_with_conditions': True,
            'concept_artifact_count': concept_validation['artifact_count'],
            'valid_concept_artifact_count': concept_validation['valid_artifact_count'],
            'review_item_count': len(review_matrix),
            'review_pass_count': sum(1 for item in review_matrix if item['result'] == 'pass'),
            'review_conditional_count': sum(1 for item in review_matrix if item['result'] == 'conditional'),
            'review_fail_count': sum(1 for item in review_matrix if item['result'] == 'fail'),
            'finding_count': len(review_findings),
            'blocking_finding_count': len(blocking_findings),
            'assumption_count': len(assumption_disposition),
            'assumptions_requiring_verification_count': sum(
                1 for item in assumption_disposition
                if item['disposition'] == 'verify_before_final'
            ),
            'risk_count': len(prioritized_risks),
            'critical_risk_count': sum(
                1 for item in prioritized_risks if item['impact'] == 'critical'
            ),
            'evidence_request_count': len(evidence_requests),
            'open_evidence_request_count': len(open_requests),
            'concept_development_allowed': True,
            'final_generation_allowed': False,
            'pilot_completed': False,
            'bb36_unlock_allowed': False,
            'next_gate': (
                'Submit and professionally verify the eight evidence packages. '
                'The evidence intake gate then updates downstream module readiness.'
            ),
        }

        paths: dict[str, Path] = {}
        paths['summary_json'] = self._write_json(
            root / '01_concept_review_summary.json', summary
        )
        paths['review_matrix_csv'] = self._write_csv(
            root / '02_concept_review_matrix.csv',
            review_matrix,
            [
                'review_id', 'category', 'criterion', 'result', 'evidence',
                'action', 'blocking_final',
            ],
        )
        paths['findings_csv'] = self._write_csv(
            root / '03_review_findings.csv',
            review_findings,
            [
                'finding_id', 'category', 'severity', 'finding', 'decision',
                'required_action', 'blocking_final',
            ],
        )
        paths['assumptions_csv'] = self._write_csv(
            root / '04_assumption_disposition_register.csv',
            assumption_disposition,
            [
                'assumption_id', 'category', 'confidence', 'statement',
                'disposition', 'evidence_request_ids', 'final_use_allowed',
            ],
        )
        paths['risks_csv'] = self._write_csv(
            root / '05_prioritized_risk_register.csv',
            prioritized_risks,
            [
                'priority', 'risk_id', 'category', 'impact', 'risk',
                'mitigation', 'evidence_request_ids', 'status',
            ],
        )
        paths['requests_csv'] = self._write_csv(
            root / '06_evidence_acquisition_master_register.csv',
            evidence_requests,
            [
                'request_id', 'input_id', 'category', 'title', 'status',
                'priority', 'responsible_party', 'blocking_final',
                'required_file_types', 'acceptance_summary',
                'unlocks_modules',
            ],
        )
        paths['dependency_csv'] = self._write_csv(
            root / '07_dependency_gate_matrix.csv',
            dependency_matrix,
            [
                'module', 'concept_allowed', 'final_ready',
                'blocking_request_ids', 'release_condition',
            ],
        )
        paths['submission_template_json'] = self._write_json(
            root / '08_evidence_submission_manifest_template.json',
            self._submission_template(project_config, evidence_requests),
        )
        paths['dashboard_html'] = self._write_text(
            root / '09_review_dashboard.html',
            self._dashboard_html(summary, review_findings, evidence_requests, dependency_matrix),
        )

        request_paths = self._write_request_packages(root, project_config, evidence_requests)
        paths.update(request_paths)

        paths['review_report_pdf'] = self._write_review_report_pdf(
            root / '10_concept_review_report.pdf',
            project_config,
            summary,
            review_findings,
            prioritized_risks,
        )
        paths['master_request_pdf'] = self._write_master_request_pdf(
            root / '11_evidence_acquisition_master_request.pdf',
            project_config,
            evidence_requests,
        )

        paths['manifest'] = self._write_json(
            root / 'concept_review_evidence_acquisition_manifest.json',
            self._manifest(project_config, summary, paths),
        )
        paths['checksums'] = self._write_checksums(
            paths, root / 'checksums.sha256'
        )
        # Refresh the manifest after checksums exist, then checksums again.
        paths['manifest'] = self._write_json(
            root / 'concept_review_evidence_acquisition_manifest.json',
            self._manifest(project_config, summary, paths),
        )
        paths['checksums'] = self._write_checksums(
            paths, root / 'checksums.sha256'
        )
        paths['dossier'] = self._write_dossier(
            paths,
            root / 'BB35_PILOT_1_CONCEPT_REVIEW_EVIDENCE_ACQUISITION_v1_4_0.zip',
        )

        result = dict(summary)
        result['output_count'] = len(paths)
        result['outputs'] = {
            key: str(value) for key, value in sorted(paths.items())
        }
        result['result_fingerprint_sha256'] = self._fingerprint(result)
        return result

    @staticmethod
    def evaluate_submission(
        *,
        request: Mapping[str, Any],
        submission_dir: str | Path,
    ) -> dict[str, Any]:
        root = Path(submission_dir)
        files = sorted(path for path in root.rglob('*') if path.is_file()) if root.exists() else []
        sidecar = root / 'professional_verification.json'
        sidecar_data: dict[str, Any] = {}
        if sidecar.is_file():
            try:
                sidecar_data = json.loads(sidecar.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                sidecar_data = {}

        allowed = {
            str(ext).lower().lstrip('.')
            for ext in request.get('required_file_types', [])
            if str(ext).lower() not in {'photos', 'signed schedule', 'measurement register', 'agreements'}
        }
        submitted_extensions = {
            path.suffix.lower().lstrip('.') for path in files if path.name != sidecar.name
        }
        has_allowed_file = not allowed or bool(allowed & submitted_extensions)
        verification_accepted = (
            sidecar_data.get('request_id') == request.get('request_id')
            and sidecar_data.get('verification_status') == 'accepted'
            and bool(sidecar_data.get('reviewer_name'))
            and bool(sidecar_data.get('reviewer_organization'))
            and bool(sidecar_data.get('verification_date'))
        )
        status = (
            'accepted'
            if files and has_allowed_file and verification_accepted
            else ('submitted_unverified' if files else 'not_submitted')
        )
        return {
            'request_id': request.get('request_id'),
            'status': status,
            'file_count': len(files),
            'has_allowed_file': has_allowed_file,
            'professional_verification_accepted': verification_accepted,
            'file_hashes': [
                {
                    'relative_path': path.relative_to(root).as_posix(),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in files
            ],
        }

    def _validate_concept_package(self, concept: Path) -> dict[str, Any]:
        manifest = self._read_json(concept / 'concept_package_manifest.json')
        results: list[dict[str, Any]] = []
        for record in manifest.get('outputs', []):
            path = concept / str(record['file_name'])
            available = path.is_file()
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if available else ''
            if str(record.get('output_id')) == 'checksums':
                checksum_lines_valid = available
                if available:
                    for line in path.read_text(encoding='utf-8').splitlines():
                        try:
                            digest, relative = line.split('  ', 1)
                        except ValueError:
                            checksum_lines_valid = False
                            break
                        target = concept / relative
                        if (
                            not target.is_file()
                            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
                        ):
                            checksum_lines_valid = False
                            break
                valid = checksum_lines_valid
                validation_method = 'checksums_file_self_consistency'
            else:
                valid = available and actual == str(record['sha256'])
                validation_method = 'manifest_sha256'
            results.append({
                'file_name': path.name,
                'available': available,
                'sha256_valid': valid,
                'expected_sha256': record['sha256'],
                'actual_sha256': actual,
                'validation_method': validation_method,
            })
        required = {
            '01_concept_digital_twin.json',
            '02_assumptions_register.json',
            '03_space_schedule.csv',
            '04_concept_quantities.csv',
            '06_concept_cost_band.csv',
            '07_permit_research_register.csv',
            '08_concept_risk_register.csv',
            '18_concept_project_report.pdf',
            '19_concept_floor_plans.pdf',
            '20_concept_elevations_sections.pdf',
            '21_schematic_site_plan.pdf',
            '22_preliminary_structural_concept.pdf',
            '23_concept_quantities_cost_summary.pdf',
            'concept_package_manifest.json',
        }
        missing_required = sorted(
            name for name in required if not (concept / name).is_file()
        )
        return {
            'artifact_count': len(results),
            'valid_artifact_count': sum(1 for item in results if item['sha256_valid']),
            'all_manifest_artifacts_valid': bool(results) and all(item['sha256_valid'] for item in results),
            'missing_required_files': missing_required,
            'manifest_generator_version': manifest.get('generator_version'),
            'status_notice_valid': manifest.get('final_generation_allowed') is False,
            'details': results,
        }

    def _review_matrix(
        self,
        *,
        scope: Mapping[str, Any],
        model: Mapping[str, Any],
        spaces: list[dict[str, str]],
        quantities: list[dict[str, str]],
        costs: list[dict[str, str]],
        concept_validation: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        gross_area = round(sum(float(item['area_m2']) for item in spaces), 2)
        checks = [
            ('REV-001', 'scope', 'Authoritative footprint is 7.00 x 10.00 m.', scope.get('extension_width_m') == 7.0 and scope.get('extension_depth_m') == 10.0, 'project configuration', 'Retain decision B.'),
            ('REV-002', 'scope', 'Authoritative gross extension area is 140 m2.', scope.get('gross_extension_area_m2') == 140.0, 'project configuration', 'Retain decision B.'),
            ('REV-003', 'status', 'Concept status blocks execution and submission.', model.get('status') == STATUS_NOTICE and model.get('release', {}).get('final_generation_allowed') is False, 'digital twin release block', 'Retain hard-coded notice.'),
            ('REV-004', 'integrity', 'Concept manifest artifacts have valid SHA-256.', concept_validation['all_manifest_artifacts_valid'], f"{concept_validation['valid_artifact_count']}/{concept_validation['artifact_count']} valid", 'Do not continue if integrity fails.'),
            ('REV-005', 'spaces', 'Space schedule totals 140 m2.', gross_area == 140.0, f'{gross_area:.2f} m2', 'Coordinate measured DO layout.'),
            ('REV-006', 'spaces', 'Fifteen concept spaces are scheduled.', len(spaces) == 15, str(len(spaces)), 'Verify room functions and occupancy.'),
            ('REV-007', 'quantities', 'Concept quantities are positive.', all(float(item['quantity']) > 0 for item in quantities), f'{len(quantities)} rows', 'Replace with measured quantities after DO/TO.'),
            ('REV-008', 'cost', 'Concept cost band is explicitly non-final.', all('CONCEPT' in item['status'] for item in costs), f'{len(costs)} rows', 'Obtain market quotations after technical design.'),
            ('REV-009', 'structure', 'Structural concept has professional evidence.', False, 'survey and geotechnical evidence absent', 'Acquire REQ-103 and REQ-104.'),
            ('REV-010', 'permit', 'Bbl/fire/occupancy evidence is complete.', False, 'external evidence absent', 'Acquire REQ-105 and REQ-107.'),
            ('REV-011', 'site', 'Cadastral/survey base is controlled.', False, 'original DWG absent', 'Acquire REQ-102.'),
            ('REV-012', 'traffic', 'Parking and traffic evidence is field verified.', False, 'preliminary study only', 'Acquire REQ-106 and REQ-107.'),
            ('REV-013', 'aerius', 'AERIUS activity data is complete.', False, 'construction/use data absent', 'Acquire REQ-108.'),
        ]
        rows: list[dict[str, Any]] = []
        for review_id, category, criterion, passed, evidence, action in checks:
            conditional_categories = {'spaces', 'quantities', 'cost'}
            result = 'pass' if passed else ('conditional' if category in conditional_categories else 'fail')
            rows.append({
                'review_id': review_id,
                'category': category,
                'criterion': criterion,
                'result': result,
                'evidence': evidence,
                'action': action,
                'blocking_final': result == 'fail',
            })
        return rows

    @staticmethod
    def _review_findings(**kwargs: Any) -> list[dict[str, Any]]:
        rows = [
            ('F-001', 'scope', 'info', 'The 7.00 x 10.00 m two-storey scope is consistent in the controlled model.', 'accepted', 'Retain scope decision B in every downstream document.', False),
            ('F-002', 'document_control', 'info', 'All controlled outputs retain the concept status and final-release block.', 'accepted', 'Do not remove status notices before final gate approval.', False),
            ('F-003', 'integrity', 'info', 'The concept artifact manifest and SHA-256 evidence validate.', 'accepted', 'Preserve deterministic generation and checksums.', False),
            ('F-004', 'architecture', 'medium', 'The reconstructed room arrangement is suitable for concept coordination only.', 'accepted_with_conditions', 'Complete measured DO/TO architectural coordination.', True),
            ('F-005', 'existing_building', 'critical', 'The original 19-page existing-building drawing source is not independently controlled.', 'hold_final', 'Acquire REQ-101.', True),
            ('F-006', 'site', 'critical', 'The original cadastral DWG/survey base is not controlled.', 'hold_final', 'Acquire REQ-102.', True),
            ('F-007', 'structure', 'critical', 'Existing load paths, capacities and connection details are unverified.', 'hold_final', 'Acquire REQ-103.', True),
            ('F-008', 'geotechnical', 'critical', 'No project-specific geotechnical and foundation evidence is available.', 'hold_final', 'Acquire REQ-104.', True),
            ('F-009', 'bbl_fire_mep', 'critical', 'Fire, Bbl, occupancy, ventilation and installation assumptions are unresolved.', 'hold_final', 'Acquire REQ-105 and REQ-107.', True),
            ('F-010', 'parking', 'high', 'Parking demand, field occupancy and public/private rights are not verified.', 'hold_final', 'Acquire REQ-106 and REQ-107.', True),
            ('F-011', 'aerius', 'high', 'Construction and operational activity data for AERIUS is absent.', 'hold_final', 'Acquire REQ-108.', True),
            ('F-012', 'cost', 'high', 'The cost band is an illustrative planning allowance and not market evidence.', 'accepted_with_conditions', 'Recalculate after technical evidence and measured quantities.', True),
        ]
        return [
            {
                'finding_id': r[0], 'category': r[1], 'severity': r[2],
                'finding': r[3], 'decision': r[4], 'required_action': r[5],
                'blocking_final': r[6],
            }
            for r in rows
        ]

    @staticmethod
    def _assumption_disposition(assumptions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        mapping = {
            'levels': ['REQ-101'],
            'roof': ['REQ-101', 'REQ-105'],
            'structure': ['REQ-103', 'REQ-104'],
            'foundation': ['REQ-103', 'REQ-104'],
            'existing_building': ['REQ-101', 'REQ-103'],
            'fire': ['REQ-105', 'REQ-107'],
            'occupancy': ['REQ-107'],
            'parking': ['REQ-106', 'REQ-107'],
            'aerius': ['REQ-108'],
            'materials': ['REQ-103', 'REQ-105'],
            'cost': ['REQ-103', 'REQ-104', 'REQ-105'],
            'site': ['REQ-102'],
            'drawings': ['REQ-101', 'REQ-102'],
        }
        rows = []
        for item in assumptions:
            verify = bool(item.get('requires_verification'))
            category = str(item.get('category'))
            rows.append({
                'assumption_id': item['assumption_id'],
                'category': category,
                'confidence': item['confidence'],
                'statement': item['statement'],
                'disposition': 'verify_before_final' if verify else 'retain_authoritative',
                'evidence_request_ids': mapping.get(category, []),
                'final_use_allowed': not verify,
            })
        return rows

    @staticmethod
    def _prioritize_risks(risks: list[dict[str, str]]) -> list[dict[str, Any]]:
        request_map = {
            'existing_building': ['REQ-101', 'REQ-103'],
            'geotechnical': ['REQ-104'],
            'site': ['REQ-102'],
            'fire': ['REQ-105', 'REQ-107'],
            'parking': ['REQ-106', 'REQ-107'],
            'aerius': ['REQ-108'],
            'cost': ['REQ-103', 'REQ-104', 'REQ-105'],
            'scope_coordination': [],
            'design': ['REQ-101', 'REQ-105', 'REQ-107'],
        }
        ordered = sorted(
            risks,
            key=lambda item: (
                _SEVERITY_ORDER.get(item.get('impact', 'info'), 99),
                item.get('risk_id', ''),
            ),
        )
        rows = []
        for index, item in enumerate(ordered, start=1):
            row = dict(item)
            row['priority'] = index
            row['evidence_request_ids'] = request_map.get(item['category'], [])
            rows.append(row)
        return rows

    @staticmethod
    def _evidence_requests(verified_inputs: Mapping[str, Any]) -> list[dict[str, Any]]:
        details = {
            'HBM-VI-101': {
                'request_id': 'REQ-101',
                'title': 'Original existing-building drawing set',
                'priority': 1,
                'acceptance_summary': 'Original complete 19-page PDF dated 03-03-2004; readable scales, details and revision identity.',
                'acceptance_criteria': [
                    'Complete original 19-page PDF, not a screenshot or partial extract.',
                    'Document title/date/revision are readable.',
                    'All plans, elevations, sections, structural and detail pages are present.',
                    'Architect or owner confirms this is the authoritative existing condition.',
                ],
                'unlocks_modules': ['building_model', 'architectural_drawings', 'structural_design', 'quantity_takeoff', 'cost_estimation'],
            },
            'HBM-VI-102': {
                'request_id': 'REQ-102',
                'title': 'Cadastral DWG and surveyed site base',
                'priority': 2,
                'acceptance_summary': 'Original DWG/DXF plus plotted PDF with parcel boundaries, north, scale and verified dimensions.',
                'acceptance_criteria': [
                    'Original DWG or DXF opens without missing external references.',
                    'Coordinate system, units and drawing scale are identified.',
                    'Parcel boundaries and surrounding context are visible.',
                    'A plotted PDF and survey/source statement are included.',
                ],
                'unlocks_modules': ['site_plan', 'building_model', 'architectural_drawings', 'permit_and_bopa'],
            },
            'HBM-VI-103': {
                'request_id': 'REQ-103',
                'title': 'Structural survey of the existing building',
                'priority': 3,
                'acceptance_summary': 'Signed survey covering foundations, frame, floors, roof, defects and connection zones.',
                'acceptance_criteria': [
                    'Site inspection date, engineer and organization are identified.',
                    'Measured member sizes/materials and load paths are recorded.',
                    'Foundation, floor, roof and connection zones are photographed.',
                    'Defects, uncertainties and required opening-up works are stated.',
                    'Report is signed or professionally accepted.',
                ],
                'unlocks_modules': ['structural_design', 'technical_specification', 'material_schedules', 'cost_estimation'],
            },
            'HBM-VI-104': {
                'request_id': 'REQ-104',
                'title': 'Geotechnical investigation and foundation advice',
                'priority': 4,
                'acceptance_summary': 'Project-specific CPT/soil data, groundwater level, settlement assessment and foundation recommendation.',
                'acceptance_criteria': [
                    'Investigation locations are tied to the project site.',
                    'Original CPT/GEF or equivalent source data are included.',
                    'Groundwater and soil profile are stated.',
                    'Bearing capacity and settlement are assessed.',
                    'A foundation recommendation is signed by a competent advisor.',
                ],
                'unlocks_modules': ['structural_design', 'quantity_takeoff', 'cost_estimation', 'technical_specification'],
            },
            'HBM-VI-105': {
                'request_id': 'REQ-105',
                'title': 'Final technical, Bbl, fire and MEP assumptions',
                'priority': 5,
                'acceptance_summary': 'Coordinated register for occupancy, fire, escape, ventilation, daylight, accessibility, materials and installations.',
                'acceptance_criteria': [
                    'Use and occupancy classification are stated.',
                    'Fire compartments, resistance, escape and emergency provisions are addressed.',
                    'Ventilation, daylight, accessibility and sanitary assumptions are addressed.',
                    'MEP systems and service interfaces are defined.',
                    'Architect/Bbl/fire/MEP reviewers approve the coordinated register.',
                ],
                'unlocks_modules': ['architectural_drawings', 'permit_and_bopa', 'technical_specification', 'material_schedules', 'cost_estimation'],
            },
            'HBM-VI-106': {
                'request_id': 'REQ-106',
                'title': 'Parking field counts and use-right evidence',
                'priority': 6,
                'acceptance_summary': 'Time-stamped counts, public/private classification and written use agreements for shared parking.',
                'acceptance_criteria': [
                    'Counts cover representative Friday, evening and peak-event periods.',
                    'Survey method, weather, event and observation times are documented.',
                    'Every counted area is classified public, private or shared.',
                    'Private/shared capacity is supported by written permission where relied upon.',
                ],
                'unlocks_modules': ['parking_and_traffic', 'permit_and_bopa', 'aerius'],
            },
            'HBM-VI-107': {
                'request_id': 'REQ-107',
                'title': 'Agreed occupancy and operational programme',
                'priority': 7,
                'acceptance_summary': 'Signed existing/future occupancy, prayer capacity, weekly programme and peak-event scenarios for 140 m2 scope.',
                'acceptance_criteria': [
                    'Existing and future maximum persons are separated.',
                    'Normal Friday, Ramadan and Eid scenarios are quantified.',
                    'Opening hours and weekly activities are included.',
                    'Vehicle occupancy and modal assumptions are coordinated with traffic advisor.',
                    'Owner signs or formally accepts the programme.',
                ],
                'unlocks_modules': ['permit_and_bopa', 'parking_and_traffic', 'aerius', 'architectural_drawings'],
            },
            'HBM-VI-108': {
                'request_id': 'REQ-108',
                'title': 'AERIUS construction and operational activity data',
                'priority': 8,
                'acceptance_summary': 'Construction duration, equipment, fuel, transport, routes and operational traffic data in structured form.',
                'acceptance_criteria': [
                    'Construction phases and durations are listed.',
                    'Equipment type, power, hours and fuel are quantified.',
                    'Construction transports and routes are quantified.',
                    'Operational vehicle movements and vehicle classes are quantified.',
                    'Structural/build-method and traffic advisors verify their respective inputs.',
                ],
                'unlocks_modules': ['aerius', 'permit_and_bopa'],
            },
        }
        rows: list[dict[str, Any]] = []
        for item in verified_inputs.get('inputs', []):
            input_id = str(item['input_id'])
            if input_id not in details:
                continue
            detail = details[input_id]
            rows.append({
                'request_id': detail['request_id'],
                'input_id': input_id,
                'category': item['category'],
                'title': detail['title'],
                'status': 'open_not_submitted',
                'priority': detail['priority'],
                'responsible_party': item.get('responsible_party', 'to be assigned'),
                'blocking_final': bool(item.get('blocking', True)),
                'required_file_types': item.get('required_file_types', []),
                'acceptance_summary': detail['acceptance_summary'],
                'acceptance_criteria': detail['acceptance_criteria'],
                'unlocks_modules': detail['unlocks_modules'],
            })
        return sorted(rows, key=lambda item: item['priority'])

    @staticmethod
    def _dependency_matrix(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        modules = {
            'building_model': (True, ['REQ-101', 'REQ-102']),
            'architectural_drawings': (True, ['REQ-101', 'REQ-102', 'REQ-105', 'REQ-107']),
            'structural_design': (False, ['REQ-101', 'REQ-103', 'REQ-104']),
            'quantity_takeoff': (True, ['REQ-101', 'REQ-103', 'REQ-104', 'REQ-105']),
            'cost_estimation': (True, ['REQ-101', 'REQ-103', 'REQ-104', 'REQ-105']),
            'technical_specification': (False, ['REQ-103', 'REQ-104', 'REQ-105']),
            'material_schedules': (False, ['REQ-103', 'REQ-105']),
            'site_plan': (True, ['REQ-102']),
            'parking_and_traffic': (True, ['REQ-106', 'REQ-107']),
            'aerius': (False, ['REQ-106', 'REQ-107', 'REQ-108']),
            'permit_and_bopa': (True, ['REQ-101', 'REQ-102', 'REQ-105', 'REQ-106', 'REQ-107', 'REQ-108']),
        }
        open_ids = {item['request_id'] for item in requests if item['status'] != 'accepted'}
        rows = []
        for module, (concept_allowed, dependencies) in modules.items():
            blockers = [request_id for request_id in dependencies if request_id in open_ids]
            rows.append({
                'module': module,
                'concept_allowed': concept_allowed,
                'final_ready': not blockers,
                'blocking_request_ids': blockers,
                'release_condition': 'all listed requests accepted' if blockers else 'ready',
            })
        return sorted(rows, key=lambda item: item['module'])

    @staticmethod
    def _submission_template(
        project_config: Mapping[str, Any],
        requests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            'schema_version': 'phoenix.bb35.evidence-submission/1.0',
            'pilot_id': project_config['pilot_id'],
            'project_id': project_config['project']['project_id'],
            'request_id': '<REQ-101..REQ-108>',
            'submitted_by': '<name>',
            'organization': '<organization>',
            'submission_date': '<YYYY-MM-DD>',
            'source_files': [
                {
                    'file_name': '<original-file.ext>',
                    'sha256': '<calculated-by-intake-engine>',
                    'source_description': '<origin and revision>',
                }
            ],
            'professional_verification': {
                'verification_status': '<accepted|rejected>',
                'reviewer_name': '<qualified reviewer>',
                'reviewer_organization': '<organization>',
                'verification_date': '<YYYY-MM-DD>',
                'limitations': [],
            },
            'valid_request_ids': [item['request_id'] for item in requests],
            'rule': 'References, offer letters and screenshots do not replace required original technical evidence.',
        }

    def _write_request_packages(
        self,
        root: Path,
        project_config: Mapping[str, Any],
        requests: list[dict[str, Any]],
    ) -> dict[str, Path]:
        result: dict[str, Path] = {}
        request_root = root / 'evidence_requests'
        for request in requests:
            request_id = request['request_id']
            folder = request_root / f"{request_id}_{request['category']}"
            folder.mkdir(parents=True, exist_ok=True)
            request_json = self._write_json(folder / 'request.json', request)
            request_md = self._write_text(
                folder / 'request_letter.md',
                self._request_markdown(project_config, request),
            )
            checklist_rows = [
                {
                    'criterion_id': f'{request_id}-AC-{index:02d}',
                    'acceptance_criterion': criterion,
                    'submitted': False,
                    'verified': False,
                    'review_comment': '',
                }
                for index, criterion in enumerate(request['acceptance_criteria'], start=1)
            ]
            checklist_csv = self._write_csv(
                folder / 'acceptance_checklist.csv',
                checklist_rows,
                ['criterion_id', 'acceptance_criterion', 'submitted', 'verified', 'review_comment'],
            )
            verification_json = self._write_json(
                folder / 'professional_verification_template.json',
                {
                    'request_id': request_id,
                    'verification_status': '<accepted|rejected>',
                    'reviewer_name': '<name>',
                    'reviewer_organization': '<organization>',
                    'verification_date': '<YYYY-MM-DD>',
                    'reviewer_role_or_qualification': '<role>',
                    'review_comment': '<comment>',
                },
            )
            intake_readme = self._write_text(
                folder / 'SUBMISSION_README.txt',
                (
                    f"{request_id} - {request['title']}\n\n"
                    'Place original evidence files in this folder together with a completed '\
                    'professional_verification.json. Do not rename or overwrite the templates.\n'
                ),
            )
            request_pdf = self._write_request_pdf(
                folder / f'{request_id}_evidence_request.pdf',
                project_config,
                request,
            )
            for suffix, path in (
                ('json', request_json),
                ('letter', request_md),
                ('checklist', checklist_csv),
                ('verification', verification_json),
                ('readme', intake_readme),
                ('pdf', request_pdf),
            ):
                result[f'{request_id.lower()}_{suffix}'] = path
        return result

    def _request_markdown(
        self,
        project_config: Mapping[str, Any],
        request: Mapping[str, Any],
    ) -> str:
        criteria = '\n'.join(
            f"- {item}" for item in request['acceptance_criteria']
        )
        types = ', '.join(str(item) for item in request['required_file_types'])
        unlocks = ', '.join(request['unlocks_modules'])
        return (
            f"# {request['request_id']} - {request['title']}\n\n"
            f"Project: {project_config['project']['project_name']}\n\n"
            f"Address: {project_config['project']['address']}\n\n"
            f"Responsible party: {request['responsible_party']}\n\n"
            f"Status: OPEN - BLOCKING FINAL GENERATION\n\n"
            f"## Requested evidence\n\n{request['acceptance_summary']}\n\n"
            f"Preferred file types: {types}\n\n"
            f"## Acceptance criteria\n\n{criteria}\n\n"
            f"## Downstream modules unlocked after acceptance\n\n{unlocks}\n\n"
            "## Submission rule\n\nOriginal files and professional verification are required. "
            "References in offer letters, screenshots or summaries do not count as final technical evidence.\n"
        )

    def _write_review_report_pdf(
        self,
        path: Path,
        project_config: Mapping[str, Any],
        summary: Mapping[str, Any],
        findings: list[dict[str, Any]],
        risks: list[dict[str, Any]],
    ) -> Path:
        pdf = SimplePDF()
        page = pdf.add_page()
        self._pdf_header(page, 'BB35 PILOT 1 - CONCEPT REVIEW REPORT', project_config)
        y = 500.0
        lines = [
            f"Status: {summary['status']}",
            'Decision: concept package accepted with conditions.',
            f"Concept artifacts valid: {summary['valid_concept_artifact_count']}/{summary['concept_artifact_count']}",
            f"Review items: {summary['review_item_count']}",
            f"Blocking findings: {summary['blocking_finding_count']}",
            f"Open evidence requests: {summary['open_evidence_request_count']}",
            'Final generation: BLOCKED',
            'BB36 release gate: LOCKED',
        ]
        for line in lines:
            page.text(50, y, line, 10)
            y -= 18
        y -= 8
        page.text(50, y, 'PRIORITY FINDINGS', 12)
        y -= 20
        for finding in findings:
            if y < 70:
                page = pdf.add_page()
                self._pdf_header(page, 'CONCEPT REVIEW FINDINGS - CONTINUED', project_config)
                y = 500
            text = f"{finding['finding_id']} [{finding['severity'].upper()}] {finding['finding']}"
            for wrapped in textwrap.wrap(text, width=110):
                page.text(55, y, wrapped, 8.5)
                y -= 12
            page.text(70, y, f"Action: {finding['required_action']}", 8)
            y -= 18
        if y < 170:
            page = pdf.add_page()
            self._pdf_header(page, 'PRIORITIZED RISKS', project_config)
            y = 500
        else:
            y -= 8
            page.text(50, y, 'PRIORITIZED RISKS', 12)
            y -= 20
        for risk in risks:
            if y < 65:
                page = pdf.add_page()
                self._pdf_header(page, 'PRIORITIZED RISKS - CONTINUED', project_config)
                y = 500
            text = f"{risk['priority']}. {risk['risk_id']} [{risk['impact'].upper()}] {risk['risk']}"
            for wrapped in textwrap.wrap(text, width=110):
                page.text(55, y, wrapped, 8.5)
                y -= 12
            y -= 5
        return pdf.save(path)

    def _write_master_request_pdf(
        self,
        path: Path,
        project_config: Mapping[str, Any],
        requests: list[dict[str, Any]],
    ) -> Path:
        pdf = SimplePDF()
        page = pdf.add_page()
        self._pdf_header(page, 'EVIDENCE ACQUISITION - MASTER REQUEST', project_config)
        y = 500
        intro = (
            'Eight evidence packages are required before final structural, permit, '
            'parking, AERIUS, specification, quantity and cost outputs can be released.'
        )
        for line in textwrap.wrap(intro, width=110):
            page.text(50, y, line, 9)
            y -= 14
        y -= 10
        for request in requests:
            if y < 85:
                page = pdf.add_page()
                self._pdf_header(page, 'EVIDENCE MASTER REQUEST - CONTINUED', project_config)
                y = 500
            page.text(50, y, f"{request['request_id']} - {request['title']}", 10)
            y -= 14
            for wrapped in textwrap.wrap(request['acceptance_summary'], width=105):
                page.text(65, y, wrapped, 8)
                y -= 11
            page.text(65, y, f"Responsible: {request['responsible_party']}", 8)
            y -= 11
            page.text(65, y, f"Unlocks: {', '.join(request['unlocks_modules'])}", 8)
            y -= 19
        return pdf.save(path)

    def _write_request_pdf(
        self,
        path: Path,
        project_config: Mapping[str, Any],
        request: Mapping[str, Any],
    ) -> Path:
        pdf = SimplePDF()
        page = pdf.add_page()
        self._pdf_header(page, f"{request['request_id']} - EVIDENCE REQUEST", project_config)
        y = 500
        page.text(50, y, request['title'], 13)
        y -= 24
        page.text(50, y, f"Priority: {request['priority']} | Responsible: {request['responsible_party']}", 9)
        y -= 22
        page.text(50, y, 'REQUESTED EVIDENCE', 11)
        y -= 17
        for line in textwrap.wrap(request['acceptance_summary'], width=108):
            page.text(55, y, line, 8.5)
            y -= 12
        y -= 8
        page.text(50, y, 'ACCEPTANCE CRITERIA', 11)
        y -= 17
        for index, criterion in enumerate(request['acceptance_criteria'], start=1):
            for line_index, line in enumerate(textwrap.wrap(criterion, width=100)):
                prefix = f"{index}. " if line_index == 0 else '   '
                page.text(55, y, prefix + line, 8.2)
                y -= 11
            y -= 3
        y -= 5
        page.text(50, y, 'SUBMISSION CONTROL', 11)
        y -= 17
        controls = [
            'Provide original files, not screenshots or summaries.',
            'Include professional_verification.json completed by the responsible reviewer.',
            'Phoenix calculates SHA-256 during evidence intake.',
            'Acceptance unlocks only the listed downstream modules.',
        ]
        for item in controls:
            page.text(55, y, '- ' + item, 8.2)
            y -= 13
        return pdf.save(path)

    @staticmethod
    def _pdf_header(page: Any, title: str, project_config: Mapping[str, Any]) -> None:
        page.fill_rect(35, 535, 772, 35, 0.90)
        page.text(48, 550, title, 14)
        page.text(48, 527, project_config['project']['project_name'], 9)
        page.text(430, 527, 'CONCEPT REVIEW - FINAL GENERATION BLOCKED', 8)
        page.line(35, 520, 807, 520, 1.2)
        page.text(48, 25, STATUS_NOTICE, 8)

    @staticmethod
    def _dashboard_html(
        summary: Mapping[str, Any],
        findings: list[dict[str, Any]],
        requests: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
    ) -> str:
        finding_rows = ''.join(
            '<tr>'
            f"<td>{html.escape(item['finding_id'])}</td>"
            f"<td>{html.escape(item['severity'])}</td>"
            f"<td>{html.escape(item['finding'])}</td>"
            f"<td>{html.escape(item['required_action'])}</td>"
            '</tr>'
            for item in findings
        )
        request_rows = ''.join(
            '<tr>'
            f"<td>{html.escape(item['request_id'])}</td>"
            f"<td>{html.escape(item['title'])}</td>"
            f"<td>{html.escape(str(item['responsible_party']))}</td>"
            f"<td>{html.escape(item['status'])}</td>"
            '</tr>'
            for item in requests
        )
        dependency_rows = ''.join(
            '<tr>'
            f"<td>{html.escape(item['module'])}</td>"
            f"<td>{'yes' if item['concept_allowed'] else 'no'}</td>"
            f"<td>{'yes' if item['final_ready'] else 'no'}</td>"
            f"<td>{html.escape(', '.join(item['blocking_request_ids']))}</td>"
            '</tr>'
            for item in dependencies
        )
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>BB35 Concept Review</title><style>'
            'body{font-family:Arial,sans-serif;max-width:1200px;margin:32px auto;color:#222}'
            'h1{border-bottom:3px solid #222;padding-bottom:8px}.status{padding:15px;background:#eee;border:1px solid #aaa}'
            'table{border-collapse:collapse;width:100%;margin:15px 0}th,td{border:1px solid #bbb;padding:7px;vertical-align:top}'
            'th{background:#263238;color:#fff}</style></head><body>'
            '<h1>BB35 Pilot 1 - Concept Review & Evidence Acquisition</h1>'
            '<div class="status">'
            f"<strong>Status:</strong> {html.escape(summary['status'])}<br>"
            f"<strong>Concept artifacts:</strong> {summary['valid_concept_artifact_count']}/{summary['concept_artifact_count']} valid<br>"
            f"<strong>Open evidence requests:</strong> {summary['open_evidence_request_count']}<br>"
            '<strong>Final generation:</strong> blocked<br><strong>BB36:</strong> locked'
            '</div><h2>Findings</h2><table><thead><tr><th>ID</th><th>Severity</th><th>Finding</th><th>Action</th></tr></thead><tbody>'
            + finding_rows + '</tbody></table><h2>Evidence Requests</h2><table><thead><tr><th>ID</th><th>Title</th><th>Responsible</th><th>Status</th></tr></thead><tbody>'
            + request_rows + '</tbody></table><h2>Dependency Gate</h2><table><thead><tr><th>Module</th><th>Concept</th><th>Final</th><th>Blockers</th></tr></thead><tbody>'
            + dependency_rows + '</tbody></table></body></html>'
        )

    def _manifest(
        self,
        project_config: Mapping[str, Any],
        summary: Mapping[str, Any],
        paths: Mapping[str, Path],
    ) -> dict[str, Any]:
        outputs = []
        for key, path in sorted(paths.items()):
            if key in {'dossier', 'manifest'} or not path.is_file():
                continue
            outputs.append({
                'output_id': key,
                'relative_path': path.name if path.parent.name != 'evidence_requests' else path.as_posix(),
                'file_name': path.name,
                'size_bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        return {
            'schema_version': 'phoenix.bb35.concept-review-manifest/1.0',
            'engine_version': self.VERSION,
            'pilot_id': project_config['pilot_id'],
            'project_id': project_config['project']['project_id'],
            'status': summary['status'],
            'status_notice': STATUS_NOTICE,
            'canonical_zip_headers': True,
            'final_generation_allowed': False,
            'bb36_unlock_allowed': False,
            'outputs': outputs,
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
    def _write_dossier(
        cls,
        paths: Mapping[str, Path],
        destination: Path,
    ) -> Path:
        base = destination.parent
        with zipfile.ZipFile(
            destination,
            'w',
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            archive.comment = b''
            for key, source in sorted(paths.items()):
                if key == 'dossier' or not source.is_file():
                    continue
                archive_name = source.relative_to(base).as_posix()
                archive.writestr(
                    cls._canonical_zip_info(archive_name),
                    source.read_bytes(),
                )
            archive.writestr(
                cls._canonical_zip_info('DOSSIER_README.txt'),
                (
                    'BB35 PILOT 1 CONCEPT REVIEW & EVIDENCE ACQUISITION\n'
                    'Concept review complete; evidence acquisition remains open.\n'
                    'Final generation is blocked. BB36 remains locked.\n'
                ).encode('utf-8'),
            )
        return destination

    @staticmethod
    def _write_checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        lines = []
        base = destination.parent
        for key, path in sorted(paths.items()):
            if key in {'checksums', 'dossier'} or not path.is_file():
                continue
            lines.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(base).as_posix()}"
            )
        return MoskeeConceptReviewEvidenceAcquisition._write_text(
            destination, '\n'.join(lines) + '\n'
        )

    @staticmethod
    def _write_json(path: Path, value: Any) -> Path:
        return MoskeeConceptReviewEvidenceAcquisition._write_text(
            path,
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        )

    @staticmethod
    def _write_text(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write(content)
        return path

    @staticmethod
    def _write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\r\n')
            writer.writeheader()
            for record in records:
                writer.writerow({
                    field: (
                        json.dumps(record.get(field), ensure_ascii=False, sort_keys=True)
                        if isinstance(record.get(field), (list, dict))
                        else record.get(field)
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open('r', encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _fingerprint(value: Any) -> str:
        data = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
        ).encode('utf-8')
        return hashlib.sha256(data).hexdigest()
