"""Professional evidence intake, validation and closure gate for BB35 Pilot 1.

This module never creates professional approval. It validates submitted evidence,
professional declarations, document hashes and project-leader acceptance records.
Final permit/tender/execution release remains blocked until accepted evidence has
been regenerated through the coordinated Phoenix production chain.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Mapping


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8'))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import io
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, '') for key in fieldnames})
    path.write_bytes(buffer.getvalue().encode('utf-8'))


def canonical_output_files(root: Path) -> list[Path]:
    """Return output files in OS-independent, case-sensitive POSIX-path order."""
    return sorted(
        (
            path
            for path in root.rglob('*')
            if path.is_file() and path.name != 'checksums.sha256'
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def canonical_zip(destination: Path, root: Path, names: list[str]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(names):
            source = root / name
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


class ProfessionalEvidenceIntakeClosureGate:
    VERSION = '2.3.1'

    def __init__(self, config: Mapping[str, Any]):
        self.config = json.loads(json.dumps(config))
        self.requirements = self.config['requirements']
        self.accepted_extensions = set(self.config['accepted_extensions'])
        self.forbidden_markers = tuple(value.lower() for value in self.config['forbidden_markers'])

    @staticmethod
    def _safe_relative_path(value: str) -> bool:
        path = Path(value)
        return bool(value) and not path.is_absolute() and '..' not in path.parts

    @staticmethod
    def _valid_date(value: Any) -> bool:
        return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value or '')))

    def _contains_forbidden_marker(self, *values: Any) -> str | None:
        combined = ' '.join(str(value) for value in values if value is not None).lower()
        return next((marker for marker in self.forbidden_markers if marker in combined), None)

    def _validate_manifest(
        self,
        requirement_id: str,
        rule: Mapping[str, Any],
        submission_dir: Path,
        manifest_path: Path,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
        findings: list[dict[str, Any]] = []
        inventory: list[dict[str, Any]] = []
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            findings.append(self._finding(requirement_id, 'MANIFEST_INVALID_JSON', 'CRITICAL', str(error)))
            return None, findings, inventory

        def require(condition: bool, code: str, message: str, severity: str = 'CRITICAL') -> None:
            if not condition:
                findings.append(self._finding(requirement_id, code, severity, message))

        require(manifest.get('schema_version') == 'phoenix.professional-evidence-submission/1.0', 'MANIFEST_SCHEMA', 'Unexpected or missing submission schema.')
        require(manifest.get('project_id') == self.config['project_id'], 'PROJECT_ID_MISMATCH', 'Manifest project_id does not match the pilot project.')
        require(manifest.get('requirement_id') == requirement_id, 'REQUIREMENT_ID_MISMATCH', 'Manifest requirement_id does not match the intake folder.')
        require(bool(manifest.get('submission_id')), 'SUBMISSION_ID_MISSING', 'submission_id is required.')
        require(self._valid_date(manifest.get('issue_date')), 'ISSUE_DATE_INVALID', 'issue_date must use YYYY-MM-DD.')
        require(manifest.get('supersedes_simulated_evidence') is True, 'SIMULATION_NOT_SUPERSEDED', 'Submission must explicitly supersede simulated evidence.')
        require(bool(manifest.get('scope_statement')), 'SCOPE_STATEMENT_MISSING', 'A project-specific scope statement is required.')
        require(bool(manifest.get('basis_of_design')), 'BASIS_OF_DESIGN_MISSING', 'The professional basis of design is required.')
        require('limitations' in manifest, 'LIMITATIONS_MISSING', 'Professional limitations must be stated, including an explicit none statement.')

        marker = self._contains_forbidden_marker(
            manifest.get('submission_id'),
            manifest.get('scope_statement'),
            manifest.get('basis_of_design'),
        )
        require(marker is None, 'FORBIDDEN_PLACEHOLDER_MARKER', f'Submission contains forbidden marker: {marker!r}.')

        professional = manifest.get('professional') or {}
        for field in ('name', 'organization', 'discipline', 'registration_number', 'registration_authority'):
            require(bool(professional.get(field)), f'PROFESSIONAL_{field.upper()}_MISSING', f'Professional field {field} is required.')
        require(professional.get('signed_declaration') is True, 'PROFESSIONAL_SIGNATURE_MISSING', 'signed_declaration must be true.')
        require(bool(professional.get('declaration_text')), 'PROFESSIONAL_DECLARATION_MISSING', 'A professional declaration text is required.')

        basis_fields = manifest.get('basis_fields') or {}
        for field, expected in rule['required_basis_fields'].items():
            actual = basis_fields.get(field)
            if field == 'minimum_count_moments_completed':
                require(isinstance(actual, (int, float)) and actual >= expected, 'BASIS_FIELD_INVALID', f'{field} must be at least {expected}.')
            else:
                require(actual == expected, 'BASIS_FIELD_INVALID', f'{field} must equal {expected!r}; received {actual!r}.')

        documents = manifest.get('documents')
        require(isinstance(documents, list) and bool(documents), 'DOCUMENT_REGISTER_MISSING', 'documents must be a non-empty list.')
        if not isinstance(documents, list):
            documents = []

        present_types: set[str] = set()
        seen_paths: set[str] = set()
        for index, document in enumerate(documents, start=1):
            document_type = str(document.get('document_type') or '')
            relative_path = str(document.get('relative_path') or '')
            title = str(document.get('title') or '')
            revision = str(document.get('revision') or '')
            declared_hash = str(document.get('sha256') or '').lower()
            present_types.add(document_type)

            require(bool(document_type), 'DOCUMENT_TYPE_MISSING', f'Document #{index} has no document_type.')
            require(self._safe_relative_path(relative_path), 'DOCUMENT_PATH_UNSAFE', f'Document #{index} has an unsafe relative path: {relative_path!r}.')
            require(relative_path not in seen_paths, 'DOCUMENT_PATH_DUPLICATE', f'Document path is duplicated: {relative_path!r}.')
            seen_paths.add(relative_path)
            require(bool(title), 'DOCUMENT_TITLE_MISSING', f'Document #{index} has no title.')
            require(bool(revision), 'DOCUMENT_REVISION_MISSING', f'Document #{index} has no revision.')
            require(self._valid_date(document.get('issue_date')), 'DOCUMENT_DATE_INVALID', f'Document #{index} issue_date must use YYYY-MM-DD.')
            require(bool(re.fullmatch(r'[0-9a-fA-F]{64}', declared_hash)), 'DOCUMENT_HASH_INVALID', f'Document #{index} requires a SHA-256 hash.')

            forbidden = self._contains_forbidden_marker(document_type, relative_path, title, revision)
            require(forbidden is None, 'DOCUMENT_FORBIDDEN_MARKER', f'Document #{index} contains forbidden marker: {forbidden!r}.')

            target = submission_dir / relative_path if self._safe_relative_path(relative_path) else submission_dir / '__invalid__'
            exists = target.is_file()
            actual_hash = sha256_file(target) if exists else ''
            extension = target.suffix.lower()
            require(exists, 'DOCUMENT_FILE_MISSING', f'Document file is missing: {relative_path!r}.')
            require(extension in self.accepted_extensions, 'DOCUMENT_EXTENSION_REJECTED', f'Unsupported document extension: {extension!r}.')
            require(not exists or target.stat().st_size > 0, 'DOCUMENT_EMPTY', f'Document is empty: {relative_path!r}.')
            require(not exists or actual_hash == declared_hash, 'DOCUMENT_HASH_MISMATCH', f'Document hash does not match: {relative_path!r}.')

            inventory.append({
                'requirement_id': requirement_id,
                'document_type': document_type,
                'relative_path': relative_path,
                'title': title,
                'revision': revision,
                'issue_date': document.get('issue_date', ''),
                'extension': extension,
                'size_bytes': target.stat().st_size if exists else 0,
                'declared_sha256': declared_hash,
                'actual_sha256': actual_hash,
                'hash_match': bool(exists and actual_hash == declared_hash),
            })

        for required_type in rule['required_document_types']:
            require(required_type in present_types, 'REQUIRED_DOCUMENT_TYPE_MISSING', f'Required document type is missing: {required_type}.')

        return manifest, findings, inventory

    def _validate_decision(
        self,
        requirement_id: str,
        manifest_path: Path,
        decision_path: Path,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        findings: list[dict[str, Any]] = []
        if not decision_path.is_file():
            findings.append(self._finding(requirement_id, 'PROJECT_LEADER_DECISION_MISSING', 'CRITICAL', 'project_leader_decision.json is required before closure.'))
            return None, findings
        try:
            decision = json.loads(decision_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            findings.append(self._finding(requirement_id, 'PROJECT_LEADER_DECISION_INVALID_JSON', 'CRITICAL', str(error)))
            return None, findings

        def require(condition: bool, code: str, message: str) -> None:
            if not condition:
                findings.append(self._finding(requirement_id, code, 'CRITICAL', message))

        require(decision.get('schema_version') == 'phoenix.project-leader-evidence-decision/1.0', 'DECISION_SCHEMA', 'Unexpected or missing decision schema.')
        require(decision.get('project_id') == self.config['project_id'], 'DECISION_PROJECT_ID_MISMATCH', 'Decision project_id mismatch.')
        require(decision.get('requirement_id') == requirement_id, 'DECISION_REQUIREMENT_ID_MISMATCH', 'Decision requirement_id mismatch.')
        require(decision.get('decision') == 'ACCEPTED', 'DECISION_NOT_ACCEPTED', 'Decision must equal ACCEPTED.')
        require(decision.get('approved') is True, 'DECISION_NOT_APPROVED', 'approved must be true.')
        require(self._valid_date(decision.get('decision_date')), 'DECISION_DATE_INVALID', 'decision_date must use YYYY-MM-DD.')
        require(bool(decision.get('approved_by_name')), 'DECISION_APPROVER_MISSING', 'approved_by_name is required.')
        require(bool(decision.get('approved_by_role')), 'DECISION_APPROVER_ROLE_MISSING', 'approved_by_role is required.')
        require(decision.get('critical_findings_open') == 0, 'CRITICAL_FINDINGS_OPEN', 'critical_findings_open must equal 0.')
        expected_hash = sha256_file(manifest_path)
        require(decision.get('reviewed_manifest_sha256') == expected_hash, 'DECISION_MANIFEST_HASH_MISMATCH', 'Decision must reference the exact submitted manifest hash.')
        return decision, findings

    @staticmethod
    def _finding(requirement_id: str, code: str, severity: str, message: str) -> dict[str, Any]:
        return {
            'requirement_id': requirement_id,
            'finding_code': code,
            'severity': severity,
            'message': message,
            'status': 'OPEN',
        }

    def evaluate(self, intake_root: Path) -> dict[str, Any]:
        intake_root = Path(intake_root)
        statuses: list[dict[str, Any]] = []
        inventory: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        closure_register: list[dict[str, Any]] = []
        impacts: list[dict[str, Any]] = []
        accepted_snapshot: list[dict[str, Any]] = []

        for requirement_id, rule in self.requirements.items():
            submission_dir = intake_root / requirement_id
            manifest_path = submission_dir / 'submission_manifest.json'
            decision_path = submission_dir / 'project_leader_decision.json'
            req_findings: list[dict[str, Any]] = []
            req_inventory: list[dict[str, Any]] = []
            manifest = None
            decision = None

            if not manifest_path.is_file():
                status = 'AWAITING_SUBMISSION'
                req_findings.append(self._finding(requirement_id, 'SUBMISSION_MANIFEST_MISSING', 'BLOCKING', 'No submission_manifest.json has been received.'))
            else:
                manifest, manifest_findings, req_inventory = self._validate_manifest(requirement_id, rule, submission_dir, manifest_path)
                req_findings.extend(manifest_findings)
                decision, decision_findings = self._validate_decision(requirement_id, manifest_path, decision_path)
                req_findings.extend(decision_findings)
                status = 'ACCEPTED_CLOSED' if not req_findings else 'REJECTED_REMEDIATION_REQUIRED'

            accepted = status == 'ACCEPTED_CLOSED'
            statuses.append({
                'requirement_id': requirement_id,
                'title': rule['title'],
                'discipline': rule['discipline'],
                'status': status,
                'accepted': accepted,
                'submission_id': manifest.get('submission_id', '') if manifest else '',
                'professional_name': (manifest.get('professional') or {}).get('name', '') if manifest else '',
                'professional_organization': (manifest.get('professional') or {}).get('organization', '') if manifest else '',
                'document_count': len(req_inventory),
                'finding_count': len(req_findings),
                'critical_or_blocking_finding_count': sum(item['severity'] in {'CRITICAL', 'BLOCKING'} for item in req_findings),
            })
            inventory.extend(req_inventory)
            findings.extend(req_findings)
            if decision:
                decisions.append({
                    'requirement_id': requirement_id,
                    'decision': decision.get('decision', ''),
                    'approved': decision.get('approved', False),
                    'decision_date': decision.get('decision_date', ''),
                    'approved_by_name': decision.get('approved_by_name', ''),
                    'approved_by_role': decision.get('approved_by_role', ''),
                    'critical_findings_open': decision.get('critical_findings_open', ''),
                    'reviewed_manifest_sha256': decision.get('reviewed_manifest_sha256', ''),
                })
            closure_register.append({
                'requirement_id': requirement_id,
                'closure_status': 'CLOSED_BY_ACCEPTED_PROFESSIONAL_EVIDENCE' if accepted else 'OPEN',
                'closure_authority': 'PROJECT_LEADER_ON_PROFESSIONAL_EVIDENCE',
                'accepted_submission_id': manifest.get('submission_id', '') if accepted and manifest else '',
                'professional_registration': (manifest.get('professional') or {}).get('registration_number', '') if accepted and manifest else '',
                'decision_date': decision.get('decision_date', '') if accepted and decision else '',
            })
            if accepted and manifest:
                document_snapshot = [
                    {
                        'document_type': row['document_type'],
                        'relative_path': row['relative_path'],
                        'sha256': row['actual_sha256'],
                        'revision': row['revision'],
                        'issue_date': row['issue_date'],
                    }
                    for row in req_inventory
                ]
                accepted_snapshot.append({
                    'requirement_id': requirement_id,
                    'submission_id': manifest['submission_id'],
                    'manifest_sha256': sha256_file(manifest_path),
                    'professional': manifest['professional'],
                    'documents': document_snapshot,
                })
                for target in rule['change_impacts']:
                    impacts.append({
                        'requirement_id': requirement_id,
                        'affected_target': target,
                        'action': 'INVALIDATE_AND_REGENERATE',
                        'reason': 'Accepted professional evidence supersedes concept/simulation assumptions.',
                    })

        accepted_count = sum(item['accepted'] for item in statuses)
        closure_gate_passed = accepted_count == len(self.requirements)
        accepted_fingerprint = hashlib.sha256(canonical_json_bytes(accepted_snapshot)).hexdigest()
        req107 = self.config['closed_requirement']
        release_candidate = closure_gate_passed and req107['status'] == 'CLOSED'
        current_status = (
            'PROFESSIONAL_EVIDENCE_CLOSURE_GATE_PASSED_REGENERATION_REQUIRED'
            if closure_gate_passed
            else 'PROFESSIONAL_EVIDENCE_INTAKE_GATE_OPERATIONAL_AWAITING_ACCEPTANCE'
        )
        gate_matrix = [
            {'gate_id': 'GATE-INTAKE-OPERATIONAL', 'status': 'PASSED', 'allowed': True, 'basis': 'Six controlled intake channels and validation rules are active.'},
            {'gate_id': 'GATE-REQ-107-PRESERVED', 'status': 'PASSED', 'allowed': True, 'basis': f"{req107['requirement_id']} remains {req107['status']} under {req107['programme_id']}."},
            {'gate_id': 'GATE-PROFESSIONAL-EVIDENCE-6-OF-6', 'status': 'PASSED' if closure_gate_passed else 'BLOCKED', 'allowed': closure_gate_passed, 'basis': f'{accepted_count} of {len(self.requirements)} evidence packages accepted.'},
            {'gate_id': 'GATE-POST-CLOSURE-REGENERATION', 'status': 'REQUIRED' if closure_gate_passed else 'NOT_AVAILABLE', 'allowed': False, 'basis': 'Accepted evidence must be consumed by the model/drawing/report/calculation orchestrator.'},
            {'gate_id': 'GATE-PERMIT-READY', 'status': 'BLOCKED', 'allowed': False, 'basis': 'Requires closure plus coordinated regeneration and final review.'},
            {'gate_id': 'GATE-TENDER-READY', 'status': 'BLOCKED', 'allowed': False, 'basis': 'Requires closure plus coordinated regeneration and final review.'},
            {'gate_id': 'GATE-EXECUTION-READY', 'status': 'BLOCKED', 'allowed': False, 'basis': 'Requires closure plus coordinated regeneration and final review.'},
            {'gate_id': 'GATE-BB36-PRODUCTION-RELEASE', 'status': 'LOCKED', 'allowed': False, 'basis': 'Requires final coordinated professional issue and explicit release approval.'},
        ]
        next_gate = (
            'Run the unified production orchestrator against the accepted evidence snapshot, regenerate all impacted products and issue the coordinated professional revision.'
            if closure_gate_passed
            else 'Receive, validate and project-leader-accept the remaining professional evidence packages for REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 and REQ-108.'
        )
        return {
            'schema_version': 'phoenix.bb35.professional-evidence-intake-closure-result/1.0',
            'engine_version': self.VERSION,
            'project_id': self.config['project_id'],
            'pilot_id': self.config['pilot_id'],
            'project_name': self.config['project_name'],
            'evaluation_revision': self.config['evaluation_revision'],
            'evaluation_date': self.config['deterministic_evaluation_date'],
            'status': current_status,
            'intake_gate_operational': True,
            'requirement_count': len(self.requirements),
            'evidence_accepted_count': accepted_count,
            'evidence_open_count': len(self.requirements) - accepted_count,
            'professional_evidence_closure_gate_passed': closure_gate_passed,
            'req107_status': req107['status'],
            'req107_programme_id': req107['programme_id'],
            'accepted_evidence_fingerprint_sha256': accepted_fingerprint,
            'release_candidate_after_regeneration': release_candidate,
            'technical_regeneration_required': closure_gate_passed,
            'permit_ready_release_allowed': False,
            'tender_ready_release_allowed': False,
            'execution_ready_release_allowed': False,
            'bb36_production_release_allowed': False,
            'requirement_statuses': statuses,
            'submission_inventory': inventory,
            'validation_findings': findings,
            'acceptance_decisions': decisions,
            'closure_register': closure_register,
            'change_impacts': impacts,
            'accepted_evidence_snapshot': accepted_snapshot,
            'gate_matrix': gate_matrix,
            'next_gate': next_gate,
        }


class ProfessionalEvidenceIntakeClosureExporter:
    CORE_FILES = [
        '01_intake_gate_summary.json',
        '02_requirement_status_register.csv',
        '03_submission_inventory.csv',
        '04_validation_findings.csv',
        '05_acceptance_decisions.csv',
        '06_closure_register.csv',
        '07_gate_matrix.csv',
        '08_change_impact_register.csv',
        '09_professional_evidence_intake_dashboard.html',
        '10_evidence_intake_instructions.md',
        '11_accepted_evidence_snapshot.json',
        '12_professional_evidence_closure_report.md',
        '13_professional_evidence_closure_gate_status.json',
        '14_rejected_submission_remediation_register.csv',
        '15_requirement_traceability.csv',
    ]

    def __init__(self, config: Mapping[str, Any]):
        self.config = json.loads(json.dumps(config))

    def export_all(self, report: Mapping[str, Any], output_dir: Path) -> dict[str, Path]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        summary = {key: value for key, value in report.items() if key not in {
            'requirement_statuses', 'submission_inventory', 'validation_findings',
            'acceptance_decisions', 'closure_register', 'change_impacts',
            'accepted_evidence_snapshot', 'gate_matrix',
        }}
        paths['summary'] = output / '01_intake_gate_summary.json'; write_json(paths['summary'], summary)
        paths['statuses'] = output / '02_requirement_status_register.csv'; write_csv(paths['statuses'], [
            'requirement_id','title','discipline','status','accepted','submission_id','professional_name','professional_organization','document_count','finding_count','critical_or_blocking_finding_count'
        ], list(report['requirement_statuses']))
        paths['inventory'] = output / '03_submission_inventory.csv'; write_csv(paths['inventory'], [
            'requirement_id','document_type','relative_path','title','revision','issue_date','extension','size_bytes','declared_sha256','actual_sha256','hash_match'
        ], list(report['submission_inventory']))
        paths['findings'] = output / '04_validation_findings.csv'; write_csv(paths['findings'], [
            'requirement_id','finding_code','severity','message','status'
        ], list(report['validation_findings']))
        paths['decisions'] = output / '05_acceptance_decisions.csv'; write_csv(paths['decisions'], [
            'requirement_id','decision','approved','decision_date','approved_by_name','approved_by_role','critical_findings_open','reviewed_manifest_sha256'
        ], list(report['acceptance_decisions']))
        paths['closure'] = output / '06_closure_register.csv'; write_csv(paths['closure'], [
            'requirement_id','closure_status','closure_authority','accepted_submission_id','professional_registration','decision_date'
        ], list(report['closure_register']))
        paths['gates'] = output / '07_gate_matrix.csv'; write_csv(paths['gates'], [
            'gate_id','status','allowed','basis'
        ], list(report['gate_matrix']))
        paths['impacts'] = output / '08_change_impact_register.csv'; write_csv(paths['impacts'], [
            'requirement_id','affected_target','action','reason'
        ], list(report['change_impacts']))
        paths['dashboard'] = output / '09_professional_evidence_intake_dashboard.html'; write_text(paths['dashboard'], self._dashboard(report))
        paths['instructions'] = output / '10_evidence_intake_instructions.md'; write_text(paths['instructions'], self._instructions(report))
        paths['snapshot'] = output / '11_accepted_evidence_snapshot.json'; write_json(paths['snapshot'], {
            'schema_version': 'phoenix.accepted-professional-evidence-snapshot/1.0',
            'project_id': report['project_id'],
            'evaluation_revision': report['evaluation_revision'],
            'accepted_count': report['evidence_accepted_count'],
            'fingerprint_sha256': report['accepted_evidence_fingerprint_sha256'],
            'requirements': report['accepted_evidence_snapshot'],
        })
        paths['report'] = output / '12_professional_evidence_closure_report.md'; write_text(paths['report'], self._closure_report(report))
        paths['gate_status'] = output / '13_professional_evidence_closure_gate_status.json'; write_json(paths['gate_status'], {
            'schema_version': 'phoenix.professional-evidence-closure-gate-status/1.0',
            'project_id': report['project_id'],
            'status': report['status'],
            'intake_gate_operational': report['intake_gate_operational'],
            'evidence_accepted_count': report['evidence_accepted_count'],
            'evidence_required_count': report['requirement_count'],
            'professional_evidence_closure_gate_passed': report['professional_evidence_closure_gate_passed'],
            'req107_status': report['req107_status'],
            'technical_regeneration_required': report['technical_regeneration_required'],
            'permit_ready_release_allowed': False,
            'tender_ready_release_allowed': False,
            'execution_ready_release_allowed': False,
            'bb36_production_release_allowed': False,
            'next_gate': report['next_gate'],
        })
        remediation = [dict(row, remediation_action=self._remediation(row)) for row in report['validation_findings']]
        paths['remediation'] = output / '14_rejected_submission_remediation_register.csv'; write_csv(paths['remediation'], [
            'requirement_id','finding_code','severity','message','status','remediation_action'
        ], remediation)
        traceability = []
        for status in report['requirement_statuses']:
            traceability.append({
                'requirement_id': status['requirement_id'],
                'professional_evidence_status': status['status'],
                'req107_dependency': 'HBM-OCC-2026-001' if status['requirement_id'] in {'REQ-105','REQ-106','REQ-108'} else 'NOT_DIRECT',
                'technical_design_revision': 'C02',
                'post_closure_action': 'REGENERATE_IMPACTED_PRODUCTS' if status['accepted'] else 'AWAIT_ACCEPTED_EVIDENCE',
                'final_release_status': 'BLOCKED',
            })
        paths['traceability'] = output / '15_requirement_traceability.csv'; write_csv(paths['traceability'], [
            'requirement_id','professional_evidence_status','req107_dependency','technical_design_revision','post_closure_action','final_release_status'
        ], traceability)

        self._export_templates(output)
        issue_members = [
            path.relative_to(output).as_posix()
            for path in output.rglob('*')
            if path.is_file() and path.name not in {'checksums.sha256'} and not path.name.endswith('.zip')
        ]
        paths['issue_package'] = output / 'BB35_PILOT_1_PROFESSIONAL_EVIDENCE_INTAKE_CLOSURE_GATE_E01.zip'
        canonical_zip(paths['issue_package'], output, issue_members)
        checksum_rows = []
        for path in canonical_output_files(output):
            checksum_rows.append(f"{sha256_file(path)}  {path.relative_to(output).as_posix()}")
        paths['checksums'] = output / 'checksums.sha256'; write_text(paths['checksums'], '\n'.join(checksum_rows) + '\n')
        return paths

    def _export_templates(self, output: Path) -> None:
        templates = output / 'submission_templates'
        for requirement_id, rule in self.config['requirements'].items():
            root = templates / requirement_id
            manifest = self._manifest_template(requirement_id, rule)
            write_json(root / 'submission_manifest_template.json', manifest)
            write_json(root / 'project_leader_decision_template.json', self._decision_template(requirement_id))
            write_json(root / 'acceptance_rules.json', rule)
            write_text(root / 'SUBMISSION_README.md', self._submission_readme(requirement_id, rule))

    def _manifest_template(self, requirement_id: str, rule: Mapping[str, Any]) -> dict[str, Any]:
        documents = []
        for index, document_type in enumerate(rule['required_document_types'], start=1):
            documents.append({
                'document_type': document_type,
                'relative_path': f'evidence/REPLACE_WITH_FILE_{index}.pdf',
                'title': 'REPLACE WITH PROFESSIONAL DOCUMENT TITLE',
                'revision': 'REPLACE',
                'issue_date': 'YYYY-MM-DD',
                'sha256': 'REPLACE_WITH_64_CHARACTER_SHA256',
            })
        return {
            'schema_version': 'phoenix.professional-evidence-submission/1.0',
            'project_id': self.config['project_id'],
            'requirement_id': requirement_id,
            'submission_id': f'{requirement_id}-PROF-YYYY-NNN',
            'issue_date': 'YYYY-MM-DD',
            'supersedes_simulated_evidence': True,
            'scope_statement': 'REPLACE WITH PROJECT-SPECIFIC SCOPE',
            'basis_of_design': 'REPLACE WITH PROFESSIONAL BASIS',
            'limitations': 'REPLACE WITH LIMITATIONS OR STATE NONE',
            'professional': {
                'name': 'REPLACE',
                'organization': 'REPLACE',
                'discipline': rule['discipline'],
                'registration_number': 'REPLACE',
                'registration_authority': 'REPLACE',
                'signed_declaration': True,
                'declaration_text': 'I accept professional responsibility for the submitted scope and conclusions.',
            },
            'basis_fields': rule['required_basis_fields'],
            'documents': documents,
        }

    def _decision_template(self, requirement_id: str) -> dict[str, Any]:
        return {
            'schema_version': 'phoenix.project-leader-evidence-decision/1.0',
            'project_id': self.config['project_id'],
            'requirement_id': requirement_id,
            'decision': 'ACCEPTED',
            'approved': True,
            'decision_date': 'YYYY-MM-DD',
            'approved_by_name': 'REPLACE',
            'approved_by_role': 'Projectleider',
            'critical_findings_open': 0,
            'reviewed_manifest_sha256': 'REPLACE_WITH_SHA256_OF_submission_manifest.json',
            'decision_note': 'REPLACE WITH DECISION BASIS',
        }

    def _submission_readme(self, requirement_id: str, rule: Mapping[str, Any]) -> str:
        types = '\n'.join(f'- `{value}`' for value in rule['required_document_types'])
        return f"""# {requirement_id} professional evidence submission\n\nDiscipline: {rule['discipline']}\n\nRequired document types:\n{types}\n\nProcedure:\n1. Put signed professional files in the `evidence` subfolder.\n2. Copy `submission_manifest_template.json` to `submission_manifest.json`.\n3. Enter the exact SHA-256 of every evidence file.\n4. Run the validation gate.\n5. Resolve every critical finding.\n6. After review, create `project_leader_decision.json` from the decision template.\n7. Run the validation gate again.\n\nTemplates, examples, simulations and unsigned documents can never close the requirement.\n"""

    @staticmethod
    def _remediation(finding: Mapping[str, Any]) -> str:
        code = finding['finding_code']
        if 'HASH' in code:
            return 'Recalculate the SHA-256 from the exact submitted file and update the manifest or decision.'
        if 'MISSING' in code:
            return 'Supply the missing project-specific field, document or decision record.'
        if 'FORBIDDEN' in code or 'SIMULATION' in code:
            return 'Replace template/simulation material with signed project-specific professional evidence.'
        if 'DECISION' in code:
            return 'Complete project-leader review after all professional evidence findings are resolved.'
        return 'Correct the submission and rerun the validation gate.'

    def _dashboard(self, report: Mapping[str, Any]) -> str:
        rows = ''.join(
            '<tr>'
            f"<td>{html.escape(row['requirement_id'])}</td>"
            f"<td>{html.escape(row['title'])}</td>"
            f"<td>{html.escape(row['status'])}</td>"
            f"<td>{row['document_count']}</td>"
            f"<td>{row['finding_count']}</td>"
            '</tr>'
            for row in report['requirement_statuses']
        )
        gate_rows = ''.join(
            '<tr>'
            f"<td>{html.escape(row['gate_id'])}</td>"
            f"<td>{html.escape(row['status'])}</td>"
            f"<td>{html.escape(row['basis'])}</td>"
            '</tr>'
            for row in report['gate_matrix']
        )
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Phoenix professional evidence closure gate</title><style>body{{font-family:Arial,sans-serif;margin:32px;color:#172033}}h1{{margin-bottom:4px}}.banner{{padding:18px;border:1px solid #94a3b8;border-radius:10px;background:#f8fafc}}.metric{{display:inline-block;margin:12px 20px 12px 0;font-size:20px}}table{{border-collapse:collapse;width:100%;margin:22px 0}}th,td{{border:1px solid #cbd5e1;padding:9px;text-align:left}}th{{background:#e2e8f0}}.blocked{{color:#991b1b;font-weight:bold}}.passed{{color:#166534;font-weight:bold}}</style></head><body><h1>BB35 Pilot 1 — Professional Evidence Intake and Closure Gate</h1><p>Revision {html.escape(report['evaluation_revision'])} · Project {html.escape(report['project_id'])}</p><div class="banner"><div class="metric">Accepted: <strong>{report['evidence_accepted_count']} / {report['requirement_count']}</strong></div><div class="metric">REQ-107: <strong>{html.escape(report['req107_status'])}</strong></div><div class="metric">Closure gate: <strong class="{'passed' if report['professional_evidence_closure_gate_passed'] else 'blocked'}">{'PASSED' if report['professional_evidence_closure_gate_passed'] else 'BLOCKED'}</strong></div><p>{html.escape(report['next_gate'])}</p></div><h2>Requirement status</h2><table><thead><tr><th>REQ</th><th>Evidence scope</th><th>Status</th><th>Documents</th><th>Findings</th></tr></thead><tbody>{rows}</tbody></table><h2>Release gates</h2><table><thead><tr><th>Gate</th><th>Status</th><th>Basis</th></tr></thead><tbody>{gate_rows}</tbody></table><p><strong>Permit-, tender-, execution- and BB36 release remain blocked until accepted evidence is regenerated into a coordinated final issue.</strong></p></body></html>"""

    def _instructions(self, report: Mapping[str, Any]) -> str:
        root = self.config['intake_root']
        return f"""# Professional evidence intake instructions\n\nCurrent accepted evidence: **{report['evidence_accepted_count']} of {report['requirement_count']}**.\n\n## Intake location\n\n`{root}`\n\nEach requirement has its own controlled folder. Copy the templates, add signed evidence files under `evidence/`, calculate SHA-256 hashes and run the closure gate.\n\n## Mandatory sequence\n\n1. Professional adviser submits project-specific signed evidence.\n2. Phoenix validates schema, scope fields, document types, file existence, file hashes, registration data and forbidden simulation markers.\n3. Critical findings are corrected.\n4. Project leader reviews the exact manifest and records an `ACCEPTED` decision referencing its SHA-256.\n5. Phoenix closes only that requirement.\n6. When all six requirements are closed, Phoenix emits an accepted-evidence snapshot and change-impact register.\n7. The unified production orchestrator must then regenerate model, drawings, reports and calculations before any final issue can be released.\n\nREQ-107 remains closed under programme `HBM-OCC-2026-001` and is not reopened by this gate.\n"""

    def _closure_report(self, report: Mapping[str, Any]) -> str:
        lines = [
            '# BB35 Pilot 1 Professional Evidence Closure Report',
            '',
            f"- Project: {report['project_name']}",
            f"- Project ID: {report['project_id']}",
            f"- Revision: {report['evaluation_revision']}",
            f"- Status: {report['status']}",
            f"- Accepted: {report['evidence_accepted_count']} of {report['requirement_count']}",
            f"- REQ-107: {report['req107_status']} ({report['req107_programme_id']})",
            '',
            '## Requirement decisions',
            '',
        ]
        for row in report['requirement_statuses']:
            lines.append(f"- **{row['requirement_id']}** — {row['status']} — {row['document_count']} documents — {row['finding_count']} findings")
        lines += [
            '',
            '## Release conclusion',
            '',
            'The professional-evidence closure gate may pass only after all six requirements are accepted. Passing this gate does not itself authorize permit, tender or execution release. Accepted evidence must first be incorporated into a coordinated regenerated issue and reviewed under the Phoenix release gates.',
            '',
            f"Next gate: {report['next_gate']}",
            '',
        ]
        return '\n'.join(lines)
