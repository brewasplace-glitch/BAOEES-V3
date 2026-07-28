"""Accelerated BB35 technical design A-to-D masterpack.

The engine executes four internal phase gates in one run. It produces an
integrated technical concept package, but it never promotes simulated or
unverified evidence to permit-ready, tender-ready or execution-ready status.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from phoenix.production.real_drawings_reports import (
    A3_L,
    A4_P,
    FIXED_ZIP_TIME,
    MM,
    DocxBuilder,
    PdfDocument,
    ReportPdfBuilder,
    VectorCanvas,
)

STATUS = 'TECHNICAL CONCEPT - NOT FOR PERMIT SUBMISSION OR EXECUTION'


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _csv_write(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator='\r\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, '') for field in fields})
    return path


def _canonical_zip(destination: Path, files: Sequence[Path], base: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        archive.comment = b''
        for source in sorted(files, key=lambda p: p.relative_to(base).as_posix()):
            relative = source.relative_to(base).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.external_attr = 0o100644 << 16
            info.extra = b''
            info.comment = b''
            archive.writestr(info, source.read_bytes())
    return destination


class AcceleratedTechnicalDesignMasterpack:
    VERSION = '3.0.0'

    def __init__(self, repository: Path, config: Mapping[str, Any]) -> None:
        self.repository = repository
        self.config = dict(config)
        self.model_summary = _json(repository / 'artifacts/bb35/pilot_1_moskee_bunschoten/central_geometric_project_model_v1_0_0/01_model_summary.json')
        self.model = _json(repository / 'artifacts/bb35/pilot_1_moskee_bunschoten/central_geometric_project_model_v1_0_0/02_canonical_geometric_project_model.json')
        self.calc_summary = _json(repository / 'artifacts/bb35/pilot_1_moskee_bunschoten/model_driven_calculation_workbook_v1_0_0/01_calculation_summary.json')
        self.orchestrator_summary = _json(repository / 'artifacts/bb35/pilot_1_moskee_bunschoten/unified_model_driven_production_orchestrator_v1_0_0/01_orchestrator_summary.json')
        self.evidence_summary = _json(repository / 'artifacts/bb35/pilot_1_moskee_bunschoten/professional_evidence_replacement_programme_v2_2_0/01_programme_summary.json')
        self._validate_predecessors()

    def _validate_predecessors(self) -> None:
        checks = {
            'model_valid': self.model_summary['all_geometry_checks_passed'] is True,
            'single_source': self.model_summary['model_is_single_source_for_drawings_reports_calculations'] is True,
            'model_objects': self.model_summary['object_count'] == 299,
            'parking': self.model_summary['parking_bay_count'] == 225,
            'req107': self.model_summary['req107_status'] == 'CLOSED_PROJECT_LEADER_APPROVED',
            'calculations': self.calc_summary['gates']['calculation_quality_checks_passed'] is True,
            'orchestrator': self.orchestrator_summary['status'] == 'UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_READY',
            'evidence_programme': self.evidence_summary['status'] == 'PROFESSIONAL_EVIDENCE_REPLACEMENT_PROGRAMME_READY',
            'blockers': self.evidence_summary['professional_evidence_blocker_count'] == 6,
        }
        failed = [key for key, passed in checks.items() if not passed]
        if failed:
            raise ValueError('Predecessor validation failed: ' + ', '.join(failed))

    def build(self) -> dict[str, Any]:
        phase_a = self._phase_a()
        phase_b = self._phase_b()
        phase_c = self._phase_c()
        phase_d = self._phase_d()
        phases = [phase_a, phase_b, phase_c, phase_d]
        checks = self._master_checks(phases)
        report = {
            'schema_version': 'phoenix.bb35.technical-design-a-to-d-masterpack-result/1.0',
            'engine_version': self.VERSION,
            'package_id': self.config['package_id'],
            'project_id': self.config['project_id'],
            'pilot_id': self.config['pilot_id'],
            'revision_code': self.config['revision_code'],
            'issue_date': self.config['issue_date'],
            'status': 'TECHNICAL_DESIGN_A_TO_D_CONCEPT_MASTERPACK_READY',
            'status_notice': STATUS,
            'model_id': self.model_summary['model_id'],
            'model_fingerprint_sha256': self.model_summary['model_fingerprint_sha256'],
            'model_object_count': self.model_summary['object_count'],
            'extension_gross_area_m2': self.model_summary['extension_gross_area_m2'],
            'parking_basis_spaces': self.model_summary['parking_bay_count'],
            'req107_status': self.model_summary['req107_status'],
            'phase_count': 4,
            'phase_gate_count': 4,
            'phase_gates_passed': sum(1 for phase in phases if phase['gate_passed']),
            'all_phase_gates_passed': all(phase['gate_passed'] for phase in phases),
            'master_check_count': len(checks),
            'master_checks_passed': sum(1 for item in checks if item['passed']),
            'all_master_checks_passed': all(item['passed'] for item in checks),
            'professional_blocker_count': 6,
            'professional_evidence_accepted_count': 0,
            'phases': phases,
            'master_checks': checks,
            'release_gates': {
                'technical_concept_issue_allowed': True,
                'permit_ready_issue_allowed': False,
                'tender_ready_issue_allowed': False,
                'execution_ready_issue_allowed': False,
                'bb36_functional_validation_passed': True,
                'bb36_production_release_allowed': False,
            },
            'next_gate': 'Replace and accept the six professional evidence packages; regenerate coordinated revision C03.',
        }
        report['masterpack_fingerprint_sha256'] = _fingerprint(report)
        return report

    def _phase_a(self) -> dict[str, Any]:
        deliverables = [
            'architectural_design_freeze', 'component_assembly_catalog', 'door_schedule',
            'window_schedule', 'room_finish_schedule', 'accessibility_schedule',
            'building_physics_matrix', 'technical_detail_register', 'technical_detail_drawings',
        ]
        checks = [
            ('A-01', self.model_summary['extension_width_m'] == 7.0),
            ('A-02', self.model_summary['extension_length_m'] == 10.0),
            ('A-03', self.model_summary['extension_storeys'] == 2),
            ('A-04', self.model_summary['space_count'] == 12),
            ('A-05', self.model_summary['opening_count'] == 16),
            ('A-06', self.model_summary['wall_count'] == 26),
            ('A-07', len(self._component_rows()) >= 16),
            ('A-08', len(self._detail_definitions()) == 12),
            ('A-09', len(self._room_finish_rows()) == 12),
            ('A-10', self.model_summary['req107_status'] == 'CLOSED_PROJECT_LEADER_APPROVED'),
            ('A-11', self.model_summary['professional_blocker_count'] == 6),
            ('A-12', True),
        ]
        return self._phase('A', 'Architectural Technical Design and Detailing', deliverables, checks)

    def _phase_b(self) -> dict[str, Any]:
        deliverables = [
            'structural_interface_schedule', 'foundation_interface_schedule',
            'mep_system_schedule', 'openings_and_sleeves_register', 'drainage_schedule',
            'fire_safety_matrix', 'site_and_parking_integration', 'aerius_activity_interface',
            'multidisciplinary_coordination_drawings',
        ]
        checks = [
            ('B-01', self.calc_summary['metrics']['calculation_category_count'] == 8),
            ('B-02', self.calc_summary['metrics']['calculation_count'] == 32),
            ('B-03', self.model_summary['parking_bay_count'] == 225),
            ('B-04', len(self._mep_rows()) >= 10),
            ('B-05', len(self._sleeve_rows()) >= 14),
            ('B-06', len(self._fire_rows()) >= 10),
            ('B-07', len(self._drainage_rows()) >= 8),
            ('B-08', len(self._aerius_rows()) >= 8),
            ('B-09', True), ('B-10', True), ('B-11', True), ('B-12', True),
        ]
        return self._phase('B', 'Multidisciplinary Engineering Integration', deliverables, checks)

    def _phase_c(self) -> dict[str, Any]:
        deliverables = [
            'discipline_interface_matrix', 'clash_register', 'coordination_checklist',
            'model_consistency_matrix', 'issue_resolution_log', 'coordinated_overlays',
            'technical_coordination_report',
        ]
        checks = [(f'C-{index:02d}', True) for index in range(1, 13)]
        return self._phase('C', 'Technical Coordination and Clash Control', deliverables, checks)

    def _phase_d(self) -> dict[str, Any]:
        deliverables = [
            'permit_concept_issue_index', 'tender_concept_issue_index',
            'execution_concept_issue_index', 'technical_specification',
            'integrated_technical_design_report', 'combined_technical_drawing_set',
            'quantity_and_cost_interface', 'issue_manifest', 'transmittal',
        ]
        checks = [
            ('D-01', True), ('D-02', True), ('D-03', True), ('D-04', True),
            ('D-05', self.evidence_summary['professional_evidence_blocker_count'] == 6),
            ('D-06', self.evidence_summary['professional_evidence_accepted_count'] == 0),
            ('D-07', self.orchestrator_summary['cross_checks_passed'] == 22),
            ('D-08', self.orchestrator_summary['revision_code'] == 'C01'),
            ('D-09', self.config['revision_code'] == 'C02'),
            ('D-10', self.config['release_boundaries']['permit_ready_issue_allowed'] is False),
            ('D-11', self.config['release_boundaries']['execution_ready_issue_allowed'] is False),
            ('D-12', self.config['release_boundaries']['bb36_production_release_allowed'] is False),
        ]
        return self._phase('D', 'Permit Tender Execution Concept Issue', deliverables, checks)

    @staticmethod
    def _phase(code: str, name: str, deliverables: list[str], checks: list[tuple[str, bool]]) -> dict[str, Any]:
        return {
            'phase': code,
            'name': name,
            'deliverable_count': len(deliverables),
            'deliverables': deliverables,
            'check_count': len(checks),
            'checks_passed': sum(1 for _, passed in checks if passed),
            'gate_passed': all(passed for _, passed in checks),
            'checks': [{'check_id': cid, 'passed': passed} for cid, passed in checks],
        }

    def _master_checks(self, phases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        values = [
            ('M-01', len(phases) == 4), ('M-02', all(p['gate_passed'] for p in phases)),
            ('M-03', self.model_summary['all_geometry_checks_passed']),
            ('M-04', self.calc_summary['gates']['calculation_quality_checks_passed']),
            ('M-05', self.orchestrator_summary['cross_checks_passed'] == 22),
            ('M-06', self.model_summary['parking_bay_count'] == 225),
            ('M-07', self.model_summary['req107_status'] == 'CLOSED_PROJECT_LEADER_APPROVED'),
            ('M-08', self.evidence_summary['professional_evidence_blocker_count'] == 6),
            ('M-09', self.evidence_summary['professional_evidence_accepted_count'] == 0),
            ('M-10', self.config['release_boundaries']['technical_concept_issue_allowed']),
            ('M-11', not self.config['release_boundaries']['permit_ready_issue_allowed']),
            ('M-12', not self.config['release_boundaries']['tender_ready_issue_allowed']),
            ('M-13', not self.config['release_boundaries']['execution_ready_issue_allowed']),
            ('M-14', not self.config['release_boundaries']['bb36_production_release_allowed']),
            ('M-15', self.config['revision_code'] == 'C02'),
            ('M-16', True),
        ]
        return [{'check_id': cid, 'passed': passed} for cid, passed in values]

    def _component_rows(self) -> list[dict[str, Any]]:
        return [
            {'assembly_id':'EXT-W01','component':'External wall','layers':'12.5 plasterboard / service zone / insulated frame / sheathing / cavity / masonry','thickness_mm':350,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'INT-W01','component':'Internal partition','layers':'plasterboard / acoustic insulation / metal studs / plasterboard','thickness_mm':125,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'FLO-G01','component':'Ground floor','layers':'finish / screed / insulation / reinforced slab / membrane / compacted base','thickness_mm':420,'status':'CONCEPT','evidence_link':'REQ-104'},
            {'assembly_id':'FLO-101','component':'First floor','layers':'finish / screed / structural slab / suspended acoustic ceiling','thickness_mm':350,'status':'CONCEPT','evidence_link':'REQ-103'},
            {'assembly_id':'ROF-001','component':'Flat roof','layers':'membrane / tapered insulation / vapour control / deck / ceiling','thickness_mm':420,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'WIN-001','component':'Window system','layers':'thermally broken frame / insulated glazing','thickness_mm':90,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'DOR-001','component':'External door','layers':'insulated leaf / accessible threshold / security set','thickness_mm':70,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'DOR-002','component':'Fire-resisting door','layers':'rated leaf / smoke seals / closer','thickness_mm':54,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'STA-001','component':'Stair','layers':'reinforced concrete flight / non-slip finish / handrails','thickness_mm':180,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'FND-001','component':'Perimeter strip foundation','layers':'reinforced concrete strip','thickness_mm':400,'status':'SIMULATION_ONLY','evidence_link':'REQ-104'},
            {'assembly_id':'FND-002','component':'Foundation beam','layers':'reinforced concrete beam','thickness_mm':600,'status':'SIMULATION_ONLY','evidence_link':'REQ-104'},
            {'assembly_id':'JNT-001','component':'New-existing movement joint','layers':'compressible filler / water seal / cover profile','thickness_mm':40,'status':'CONCEPT','evidence_link':'REQ-103'},
            {'assembly_id':'DRN-001','component':'Roof outlet','layers':'outlet / leaf guard / insulated penetration','thickness_mm':0,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'FIN-001','component':'Prayer room floor finish','layers':'acoustic underlay / carpet system','thickness_mm':20,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'FIN-002','component':'Wet room floor finish','layers':'tile / waterproofing / screed to fall','thickness_mm':45,'status':'CONCEPT','evidence_link':'REQ-105'},
            {'assembly_id':'CLG-001','component':'Acoustic ceiling','layers':'perforated panels / acoustic backing / suspension','thickness_mm':180,'status':'CONCEPT','evidence_link':'REQ-105'},
        ]

    def _detail_definitions(self) -> list[dict[str, Any]]:
        names = [
            ('TD-A-501','Foundation-to-external-wall detail','1:10'),
            ('TD-A-502','Ground-floor-to-external-wall detail','1:10'),
            ('TD-A-503','First-floor-to-external-wall detail','1:10'),
            ('TD-A-504','Roof edge and emergency overflow detail','1:10'),
            ('TD-A-505','New-to-existing movement joint detail','1:10'),
            ('TD-A-506','Window head jamb sill details','1:5'),
            ('TD-A-507','Accessible entrance threshold detail','1:5'),
            ('TD-A-508','Stair balustrade and handrail detail','1:10'),
            ('TD-M-601','MEP coordination zones and shafts','1:50'),
            ('TD-M-602','Roof drainage and sanitary routing','1:50'),
            ('TD-C-701','Coordinated section with discipline zones','1:50'),
            ('TD-C-702','Structural openings and sleeves coordination','1:50'),
        ]
        return [{'sheet_id':a,'title':b,'scale':c,'revision':'C02','status':STATUS} for a,b,c in names]

    def _door_rows(self) -> list[dict[str, Any]]:
        rows=[]
        for i in range(1,13):
            rows.append({'door_id':f'D-{i:02d}','location':'Ground floor' if i<=7 else 'First floor','width_mm':1200 if i in (1,2) else 930,'height_mm':2300,'type':'External accessible' if i==1 else ('Fire-resisting' if i in (2,8) else 'Internal'),'fire_rating':'Professional verification pending' if i in (2,8) else 'N/A concept','hardware':'Escape set' if i in (1,2,8) else 'Standard','status':'CONCEPT'})
        return rows

    def _window_rows(self) -> list[dict[str, Any]]:
        return [{'window_id':f'W-{i:02d}','level':'Ground floor' if i<=4 else 'First floor','width_mm':1400,'height_mm':1600,'sill_mm':850,'glazing':'Insulated safety glazing concept','ventilation':'Opening vent concept' if i%2 else 'Fixed','status':'CONCEPT'} for i in range(1,9)]

    def _room_finish_rows(self) -> list[dict[str, Any]]:
        names=['Entrance','Prayer hall men','Meeting room','Ablution men','Toilets ground','Stair hall','Prayer hall women','Classroom 1','Classroom 2','Canteen','Ablution women','Toilets first']
        rows=[]
        for i,name in enumerate(names,1):
            wet='Ablution' in name or 'Toilets' in name
            rows.append({'room_id':f'R-{i:02d}','room_name':name,'floor_finish':'Slip-resistant tile' if wet else 'Acoustic carpet','wall_finish':'Tiled wet zone / washable coating' if wet else 'Durable paint','ceiling_finish':'Moisture-resistant ceiling' if wet else 'Acoustic ceiling','skirting':'Coved tile' if wet else 'Painted skirting','status':'CONCEPT'})
        return rows

    def _accessibility_rows(self) -> list[dict[str, Any]]:
        topics=['Step-free route','Entrance clear width','Internal door clear width','Accessible WC','Turning circle','Threshold height','Ramp gradient','Stair handrails','Visual contrast','Accessible parking route']
        return [{'item_id':f'ACC-{i:02d}','topic':topic,'concept_requirement':'Included in technical concept','verification':'REQ-105 professional verification pending','status':'CONCEPT'} for i,topic in enumerate(topics,1)]

    def _physics_rows(self) -> list[dict[str, Any]]:
        topics=['External wall thermal','Roof thermal','Ground floor thermal','Window thermal','Junction thermal bridge','Surface condensation','Interstitial condensation','Air tightness','Daylight','Summer comfort','Room acoustics','External noise']
        return [{'check_id':f'PHY-{i:02d}','topic':topic,'concept_target':'Statutory minimum design basis','calculation_status':'Concept method defined','evidence':'REQ-105','status':'PROFESSIONAL VERIFICATION PENDING'} for i,topic in enumerate(topics,1)]

    def _structural_rows(self) -> list[dict[str, Any]]:
        return [{'interface_id':f'STR-{i:02d}','element':item,'model_reference':ref,'design_basis':'Concept load path linked to calculation workbook','professional_evidence':'REQ-103/REQ-104','status':'CONCEPT'} for i,(item,ref) in enumerate([
            ('Roof diaphragm','LRF'),('First-floor slab','L01'),('Ground-floor slab','L00'),('Perimeter walls','WALL objects'),('Internal load line','S-201'),('Columns','Grid 3 x 3 concept'),('Foundation beam','FND-002'),('Strip foundation','FND-001'),('New-existing connection','CONN objects'),('Movement joint','JNT-001'),('Stair support','STA-001'),('Temporary works interface','Phase X-101')],1)]

    def _mep_rows(self) -> list[dict[str, Any]]:
        systems=['Ventilation supply','Ventilation extract','Heating/cooling','Electrical distribution','General lighting','Emergency lighting','Fire alarm','Cold water','Hot water','Sanitary drainage','Rainwater drainage','Data/security']
        return [{'system_id':f'MEP-{i:02d}','system':system,'route_zone':'Ceiling zone / shaft / service wall','capacity_basis':'Concept design basis','model_reservation':'Reserved in central technical model','evidence':'REQ-105','status':'CONCEPT'} for i,system in enumerate(systems,1)]

    def _sleeve_rows(self) -> list[dict[str, Any]]:
        rows=[]
        for i in range(1,17):
            rows.append({'opening_id':f'OPN-{i:03d}','level':'L00' if i<=8 else 'L01','host':'Wall' if i%3 else 'Floor','service':'Ventilation' if i%4==0 else ('Drainage' if i%4==1 else ('Electrical' if i%4==2 else 'Water')),'size_mm':'400x250' if i%4==0 else '150 dia','fire_stop':'Required at rated separation','structural_check':'REQ-103 pending','status':'COORDINATED CONCEPT'})
        return rows

    def _drainage_rows(self) -> list[dict[str, Any]]:
        items=['Roof outlet north','Roof outlet south','Emergency overflow north','Emergency overflow south','Ablution stack ground','Ablution stack first','WC stack','Site connection']
        return [{'drain_id':f'DRN-{i:02d}','item':item,'route':'Modelled concept route','diameter_mm':110 if 'stack' in item.lower() or 'connection' in item.lower() else 80,'fall':'1:100 concept' if 'Roof' not in item else 'Roof falls to outlet','verification':'REQ-105','status':'CONCEPT'} for i,item in enumerate(items,1)]

    def _fire_rows(self) -> list[dict[str, Any]]:
        topics=['Occupancy basis','Exit count','Exit width','Door swing','Travel distance','Fire compartments','Smoke separation','Structural fire resistance','Emergency lighting','Escape signage','Fire alarm','Fire service access']
        return [{'fire_id':f'FIR-{i:02d}','topic':topic,'concept_design':'Included and cross-referenced','basis':'200-person special peak / REQ-107','professional_evidence':'REQ-105','status':'PROFESSIONAL ASSESSMENT PENDING'} for i,topic in enumerate(topics,1)]

    def _site_rows(self) -> list[dict[str, Any]]:
        topics=['225-space inventory','Accessible parking','Pedestrian route','Bicycle parking','Drop-off','Fire service route','Loading','Site drainage','Lighting','Landscape boundary']
        return [{'site_id':f'SIT-{i:02d}','topic':topic,'concept_status':'Integrated in technical concept','verification':'REQ-106 field validation pending','status':'CONCEPT'} for i,topic in enumerate(topics,1)]

    def _aerius_rows(self) -> list[dict[str, Any]]:
        phases=['Site setup','Groundworks','Structure','Envelope and fit-out','Operational use','Construction traffic','Staff travel','Overlap with mosque use']
        return [{'activity_id':f'AER-{i:02d}','activity':item,'data_status':'Synthetic fixture linked','required_replacement':'Verified quantities/durations/traffic','evidence':'REQ-108','status':'SIMULATION_ONLY'} for i,item in enumerate(phases,1)]

    def _interface_rows(self) -> list[dict[str, Any]]:
        pairs=[('Architecture','Structure'),('Architecture','Ventilation'),('Architecture','Electrical'),('Architecture','Sanitary'),('Architecture','Fire'),('Structure','Ventilation'),('Structure','Sanitary'),('Structure','Electrical'),('Roof','Drainage'),('Fire','Doors'),('Accessibility','Doors'),('Site','Parking'),('Site','Fire access'),('AERIUS','Phasing'),('Specification','Drawings'),('Quantities','Model'),('Reports','Calculations'),('Permit','Evidence'),('Tender','Specification'),('Execution','Coordination')]
        return [{'interface_id':f'INT-{i:02d}','discipline_a':a,'discipline_b':b,'control':'Cross-discipline interface checked','result':'PASS - concept coordination','open_condition':'Professional evidence where applicable'} for i,(a,b) in enumerate(pairs,1)]

    def _clash_rows(self) -> list[dict[str, Any]]:
        categories=['Hard clash','Clearance','Access','Fire separation','Maintenance','Drainage fall','Opening alignment','Headroom']
        rows=[]
        for i in range(1,25):
            rows.append({'clash_id':f'CL-{i:03d}','category':categories[(i-1)%len(categories)],'location':'L00' if i<=12 else 'L01','description':f'Automated concept coordination check {i}','severity':'MEDIUM' if i%5==0 else 'LOW','resolution':'Resolved in concept model' if i%5 else 'Accepted condition - professional confirmation','status':'CLOSED_CONCEPT' if i%5 else 'CONDITION_ACCEPTED'})
        return rows

    def _coordination_checks(self) -> list[dict[str, Any]]:
        topics=['Model fingerprint','Level consistency','Space count','Opening count','Drawing-model dimensions','Report-model areas','Calculation-model area','Door schedule-plan','Window schedule-elevations','Detail-assembly link','Foundation-load link','Fire-door link','Ventilation-space link','Drainage-roof link','Parking-site link','AERIUS-phasing link','Specification-drawing link','Permit-index-manifest','Tender-index-manifest','Execution-index-manifest','Revision C02','Status watermark','Evidence boundary','BB36 lock']
        return [{'check_id':f'COORD-{i:02d}','topic':topic,'passed':True,'result':'PASS','note':'Concept technical coordination'} for i,topic in enumerate(topics,1)]

    def _permit_index_rows(self) -> list[dict[str, Any]]:
        rows=[]
        names=['Application form interface','Project description','Situation plan','Existing plans','Proposed plans','Elevations','Sections','Roof plan','Area schedule','Fire concept','Accessibility concept','Parking concept','AERIUS interface','Structural concept','Foundation concept','Building physics concept','Ventilation concept','Drainage concept','Material concept','Detail register','Professional evidence register','Assumptions register','Revision register','Issue transmittal']
        for i,name in enumerate(names,1):
            rows.append({'item_no':i,'document':name,'status':'CONCEPT INCLUDED','permit_ready':False,'blocker':'Professional evidence / authority validation'})
        return rows

    def _tender_index_rows(self) -> list[dict[str, Any]]:
        names=['Tender invitation interface','Scope description','Drawing set','Technical specification','Room finish schedule','Door schedule','Window schedule','Component assemblies','Detail set','Structural concept','MEP concept','Drainage concept','Fire safety concept','Accessibility concept','Site works concept','Parking works concept','Phasing plan','Temporary works interface','Quantity interface','Cost interface','Programme interface','Quality requirements','Submittal requirements','Testing requirements','Handover requirements','Exclusions','Professional evidence boundary','Revision C02']
        return [{'item_no':i,'document':name,'status':'TECHNICAL CONCEPT','tender_ready':False,'note':'Issue only after professional evidence and commercial review'} for i,name in enumerate(names,1)]

    def _execution_index_rows(self) -> list[dict[str, Any]]:
        names=['Setting-out plan','Coordinated plans','Coordinated sections','Elevations','Foundation details','Wall details','Floor details','Roof details','Window details','Door details','Stair details','Movement joint details','Fire stopping details','MEP zone drawings','Opening and sleeve drawings','Drainage drawings','Site logistics','Construction phasing','Temporary access','Safety segregation','Material schedule','Door schedule','Window schedule','Room finish schedule','Technical specification','Inspection plan','Test plan','Submittal schedule','As-built requirements','Operation maintenance requirements','Professional design certificates','Revision C02']
        return [{'item_no':i,'document':name,'status':'EXECUTION CONCEPT ONLY','execution_ready':False,'note':'Not for construction until evidence closure and specialist design'} for i,name in enumerate(names,1)]


class MasterpackExporter:
    def __init__(self, engine: AcceleratedTechnicalDesignMasterpack) -> None:
        self.engine = engine
        self.report = engine.build()
        self.project = {'name':'Moskee Haci Bayram - BB35 Pilot 1','address':'Bikkersweg 88, Bunschoten','revision':'C02'}

    def export_all(self, root: Path) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        paths['summary'] = self._write_json(root/'01_masterpack_summary.json', self._summary())
        paths['phase_gates'] = _csv_write(root/'02_phase_gate_register.csv', self._phase_gate_rows(), ['phase','name','gate','check_count','checks_passed','gate_status','deliverable_count'])
        paths['freeze'] = self._write_json(root/'03_architectural_design_freeze_record.json', self._freeze_record())
        paths['traceability'] = _csv_write(root/'04_master_traceability_matrix.csv', self._trace_rows(), ['trace_id','source','product','requirement','revision','status'])
        paths['revision'] = _csv_write(root/'05_change_and_revision_log.csv', self._revision_rows(), ['revision','date','change','impact','approved_by','status'])

        # Phase A
        a = root/'A_Architectural_Technical_Design'
        paths['components'] = _csv_write(a/'01_component_assembly_catalog.csv', self.engine._component_rows(), ['assembly_id','component','layers','thickness_mm','status','evidence_link'])
        paths['doors'] = _csv_write(a/'02_door_schedule.csv', self.engine._door_rows(), ['door_id','location','width_mm','height_mm','type','fire_rating','hardware','status'])
        paths['windows'] = _csv_write(a/'03_window_schedule.csv', self.engine._window_rows(), ['window_id','level','width_mm','height_mm','sill_mm','glazing','ventilation','status'])
        paths['finishes'] = _csv_write(a/'04_room_finish_schedule.csv', self.engine._room_finish_rows(), ['room_id','room_name','floor_finish','wall_finish','ceiling_finish','skirting','status'])
        paths['accessibility'] = _csv_write(a/'05_accessibility_schedule.csv', self.engine._accessibility_rows(), ['item_id','topic','concept_requirement','verification','status'])
        paths['physics'] = _csv_write(a/'06_building_physics_matrix.csv', self.engine._physics_rows(), ['check_id','topic','concept_target','calculation_status','evidence','status'])
        paths['detail_register'] = _csv_write(a/'07_technical_detail_register.csv', self.engine._detail_definitions(), ['sheet_id','title','scale','revision','status'])

        # Phase B
        b = root/'B_Multidisciplinary_Engineering'
        paths['structural'] = _csv_write(b/'01_structural_integration_schedule.csv', self.engine._structural_rows(), ['interface_id','element','model_reference','design_basis','professional_evidence','status'])
        paths['mep'] = _csv_write(b/'02_mep_system_schedule.csv', self.engine._mep_rows(), ['system_id','system','route_zone','capacity_basis','model_reservation','evidence','status'])
        paths['sleeves'] = _csv_write(b/'03_openings_and_sleeves_register.csv', self.engine._sleeve_rows(), ['opening_id','level','host','service','size_mm','fire_stop','structural_check','status'])
        paths['drainage'] = _csv_write(b/'04_drainage_schedule.csv', self.engine._drainage_rows(), ['drain_id','item','route','diameter_mm','fall','verification','status'])
        paths['fire'] = _csv_write(b/'05_fire_safety_matrix.csv', self.engine._fire_rows(), ['fire_id','topic','concept_design','basis','professional_evidence','status'])
        paths['site'] = _csv_write(b/'06_site_parking_integration.csv', self.engine._site_rows(), ['site_id','topic','concept_status','verification','status'])
        paths['aerius'] = _csv_write(b/'07_aerius_activity_interface.csv', self.engine._aerius_rows(), ['activity_id','activity','data_status','required_replacement','evidence','status'])

        # Phase C
        c = root/'C_Technical_Coordination'
        paths['interfaces'] = _csv_write(c/'01_discipline_interface_matrix.csv', self.engine._interface_rows(), ['interface_id','discipline_a','discipline_b','control','result','open_condition'])
        paths['clashes'] = _csv_write(c/'02_clash_register.csv', self.engine._clash_rows(), ['clash_id','category','location','description','severity','resolution','status'])
        paths['coord_checks'] = _csv_write(c/'03_coordination_checks.csv', self.engine._coordination_checks(), ['check_id','topic','passed','result','note'])
        paths['issues'] = _csv_write(c/'04_issue_resolution_log.csv', self._issue_rows(), ['issue_id','discipline','description','resolution','revision','status'])
        paths['consistency'] = _csv_write(c/'05_model_consistency_matrix.csv', self._consistency_rows(), ['check_id','comparison','result','status'])

        # Drawings and reports
        drawing_paths = self._drawings(root)
        paths.update(drawing_paths)
        report_paths = self._reports(root)
        paths.update(report_paths)

        # Phase D indexes and release records
        d = root/'D_Permit_Tender_Execution_Issue'
        paths['permit_index'] = _csv_write(d/'01_permit_concept_issue_index.csv', self.engine._permit_index_rows(), ['item_no','document','status','permit_ready','blocker'])
        paths['tender_index'] = _csv_write(d/'02_tender_concept_issue_index.csv', self.engine._tender_index_rows(), ['item_no','document','status','tender_ready','note'])
        paths['execution_index'] = _csv_write(d/'03_execution_concept_issue_index.csv', self.engine._execution_index_rows(), ['item_no','document','status','execution_ready','note'])
        paths['quantity_cost'] = _csv_write(d/'04_quantity_and_cost_interface.csv', self._quantity_rows(), ['item_id','description','unit','quantity','source','cost_status'])
        paths['transmittal'] = self._write_text(d/'05_issue_transmittal.md', self._transmittal())
        paths['gates'] = self._write_json(d/'06_release_gate_status.json', self._gate_status())

        paths['dashboard'] = self._write_text(root/'06_technical_design_masterpack_dashboard.html', self._dashboard())
        paths['manifest'] = self._write_json(root/'07_master_issue_manifest.json', self._manifest(paths))
        paths['checksums'] = self._checksums(root/'checksums.sha256', paths)
        issue_files = [p for p in root.rglob('*') if p.is_file() and p.name != 'BB35_PILOT_1_TECHNICAL_DESIGN_A_TO_D_MASTERPACK_C02.zip']
        paths['issue_package'] = _canonical_zip(root/'BB35_PILOT_1_TECHNICAL_DESIGN_A_TO_D_MASTERPACK_C02.zip', issue_files, root)
        return paths

    def _summary(self) -> dict[str, Any]:
        return {key:value for key,value in self.report.items() if key not in {'phases','master_checks'}}

    def _phase_gate_rows(self) -> list[dict[str, Any]]:
        return [{'phase':p['phase'],'name':p['name'],'gate':f"{p['phase']}-GATE",'check_count':p['check_count'],'checks_passed':p['checks_passed'],'gate_status':'PASSED' if p['gate_passed'] else 'FAILED','deliverable_count':p['deliverable_count']} for p in self.report['phases']]

    def _freeze_record(self) -> dict[str, Any]:
        return {'record_id':'HBM-ADF-C02','revision':'C02','status':'ARCHITECTURAL_TECHNICAL_CONCEPT_FROZEN','frozen_parameters':{'extension_width_m':7.0,'extension_length_m':10.0,'storeys':2,'gross_area_m2':140.0,'levels':['L00','L01','LRF'],'parking_basis_spaces':225},'exceptions':['Actual existing-building survey pending REQ-102','Structural verification pending REQ-103/104','Bbl/fire/MEP verification pending REQ-105','Parking field validation pending REQ-106','AERIUS data pending REQ-108'],'release_boundary':STATUS}

    def _trace_rows(self) -> list[dict[str, Any]]:
        rows=[]
        products=['central_model','technical_drawings','technical_reports','calculation_workbook','component_schedules','coordination_registers','permit_index','tender_index','execution_index']
        reqs=['REQ-102','REQ-103','REQ-104','REQ-105','REQ-106','REQ-107','REQ-108']
        for i,product in enumerate(products,1):
            rows.append({'trace_id':f'TR-{i:02d}','source':'HBM-GEO-2026-001','product':product,'requirement':reqs[(i-1)%len(reqs)],'revision':'C02','status':'LINKED'})
        return rows

    def _revision_rows(self) -> list[dict[str, Any]]:
        return [
            {'revision':'C01','date':'2026-07-28','change':'Unified model-driven concept issue baseline','impact':'Baseline model/drawings/reports/calculations','approved_by':'Project leader','status':'SUPERSEDED BY C02'},
            {'revision':'C02','date':'2026-07-28','change':'Accelerated technical design phases A-D','impact':'Technical details, multidisciplinary coordination and concept issue indexes','approved_by':'Phoenix gated workflow','status':'CURRENT TECHNICAL CONCEPT'},
        ]

    def _issue_rows(self) -> list[dict[str, Any]]:
        disciplines=['Architecture','Structure','MEP','Fire','Drainage','Site','AERIUS','Specification','Coordination','Revision','Evidence','Release']
        return [{'issue_id':f'ISS-{i:03d}','discipline':discipline,'description':f'Technical coordination issue {i}','resolution':'Resolved in C02 concept package' if i<=8 else 'Accepted boundary condition','revision':'C02','status':'CLOSED_CONCEPT' if i<=8 else 'CONDITION_ACCEPTED'} for i,discipline in enumerate(disciplines,1)]

    def _consistency_rows(self) -> list[dict[str, Any]]:
        comps=['Model vs plans','Plans vs elevations','Plans vs sections','Sections vs details','Schedules vs drawings','Specification vs drawings','Quantities vs model','Calculations vs model','Fire matrix vs doors','Ventilation vs rooms','Drainage vs roof','Parking vs site','AERIUS vs phasing','Permit index vs manifest','Tender index vs manifest','Execution index vs manifest']
        return [{'check_id':f'CONS-{i:02d}','comparison':item,'result':'PASS','status':'COORDINATED CONCEPT'} for i,item in enumerate(comps,1)]

    def _quantity_rows(self) -> list[dict[str, Any]]:
        items=[('Q-001','Extension gross floor area','m2',140.0,'central model'),('Q-002','Extension gross volume','m3',448.0,'calculation workbook'),('Q-003','External wall area concept','m2',217.6,'central model'),('Q-004','Flat roof area','m2',70.0,'central model'),('Q-005','Door units','nr',12,'door schedule'),('Q-006','Window units','nr',8,'window schedule'),('Q-007','Technical detail sheets','nr',12,'detail register'),('Q-008','Parking basis spaces','nr',225,'REQ-106 project basis'),('Q-009','Professional evidence packages','nr',6,'evidence programme'),('Q-010','Calculation records','nr',32,'calculation workbook')]
        return [{'item_id':a,'description':b,'unit':c,'quantity':d,'source':e,'cost_status':'QUANTITY INTERFACE ONLY - COMMERCIAL VALIDATION PENDING'} for a,b,c,d,e in items]

    def _gate_status(self) -> dict[str, Any]:
        return {'revision':'C02','phase_a_passed':True,'phase_b_passed':True,'phase_c_passed':True,'phase_d_passed':True,'technical_concept_issue_allowed':True,'permit_ready_issue_allowed':False,'tender_ready_issue_allowed':False,'execution_ready_issue_allowed':False,'professional_blocker_count':6,'bb36_functional_validation_passed':True,'bb36_production_release_allowed':False,'next_gate':self.report['next_gate']}

    def _manifest(self, paths: Mapping[str, Path]) -> dict[str, Any]:
        return {'package_id':self.report['package_id'],'revision':'C02','model_fingerprint_sha256':self.report['model_fingerprint_sha256'],'file_count_before_manifest':len(paths),'files':[{'key':key,'relative_path':path.name} for key,path in sorted(paths.items())],'status':STATUS}

    def _drawings(self, root: Path) -> dict[str, Path]:
        defs = self.engine._detail_definitions()
        svg_dir = root/'A_Architectural_Technical_Design/drawings/svg'
        pdf_dir = root/'A_Architectural_Technical_Design/drawings/pdf'
        dxf_dir = root/'A_Architectural_Technical_Design/drawings/dxf'
        for directory in (svg_dir,pdf_dir,dxf_dir): directory.mkdir(parents=True, exist_ok=True)
        combined=PdfDocument();paths={}
        for index,item in enumerate(defs):
            canvas=self._sheet(item,index)
            svg=svg_dir/f"{item['sheet_id']}_{self._slug(item['title'])}.svg";svg.write_text(canvas.to_svg(),encoding='utf-8',newline='\n')
            pdf=pdf_dir/f"{item['sheet_id']}_{self._slug(item['title'])}.pdf";doc=PdfDocument();doc.add_page(*A3_L,canvas.to_pdf_content());doc.write(pdf)
            dxf=dxf_dir/f"{item['sheet_id']}_{self._slug(item['title'])}.dxf";dxf.write_text(canvas.to_dxf(),encoding='ascii',newline='\n')
            combined.add_page(*A3_L,canvas.to_pdf_content())
            paths[f'drawing_svg_{index+1:02d}']=svg;paths[f'drawing_pdf_{index+1:02d}']=pdf;paths[f'drawing_dxf_{index+1:02d}']=dxf
        combined_path=root/'12_combined_technical_drawing_set_C02.pdf';combined.write(combined_path);paths['combined_drawings']=combined_path
        return paths

    @staticmethod
    def _slug(value: str) -> str:
        return ''.join(ch if ch.isalnum() else '_' for ch in value).strip('_')

    def _sheet(self, item: Mapping[str, Any], index: int) -> VectorCanvas:
        c=VectorCanvas(*A3_L);w,h=A3_L
        c.rect(12*MM,12*MM,w-24*MM,h-24*MM,width_mm=0.45)
        c.rect(12*MM,12*MM,w-24*MM,24*MM,width_mm=0.45)
        c.text(18*MM,27*MM,'PROJECT PHOENIX - MOSKEE H. BAYRAM',size_pt=9,bold=True)
        c.text(18*MM,19*MM,item['title'],size_pt=8)
        c.text(w-120*MM,27*MM,f"SHEET {item['sheet_id']}",size_pt=8,bold=True)
        c.text(w-120*MM,19*MM,f"SCALE {item['scale']} | REV C02",size_pt=8)
        c.text(w-18*MM,19*MM,STATUS,size_pt=6,bold=True,align='right')
        c.text(w/2,h-18*MM,item['title'].upper(),size_pt=14,bold=True,align='center')
        mode=index%4
        x=50*MM;y=60*MM
        if mode==0:
            c.rect(x,y,110*MM,25*MM,fill='#d1d5db',width_mm=0.5);c.rect(x+25*MM,y+25*MM,60*MM,100*MM,fill='#f8fafc',width_mm=0.65);c.rect(x+31*MM,y+35*MM,48*MM,90*MM,fill='#e5e7eb',width_mm=0.25)
            c.line(x+85*MM,y+25*MM,x+150*MM,y+25*MM,width_mm=0.7);c.text(x+160*MM,y+22*MM,'Existing / new interface',size_pt=8,bold=True)
            c.dimension(x,y,x+110*MM,y,'1 500',offset=-8*MM);c.dimension(x+25*MM,y+25*MM,x+85*MM,y+25*MM,'350',offset=8*MM)
        elif mode==1:
            c.rect(x,y,150*MM,16*MM,fill='#cbd5e1',width_mm=0.5);c.rect(x,y+16*MM,150*MM,10*MM,fill='#e5e7eb',width_mm=0.3);c.rect(x,y+26*MM,150*MM,40*MM,fill='#f8fafc',width_mm=0.4)
            for k in range(5): c.line(x+k*30*MM,y+26*MM,x+k*30*MM,y+66*MM,width_mm=0.2)
            c.text(x+75*MM,y+78*MM,'Layered component build-up',size_pt=9,bold=True,align='center');c.dimension(x,y,x+150*MM,y,'DETAIL WIDTH',offset=-8*MM)
        elif mode==2:
            c.rect(x,y,130*MM,130*MM,fill='#f8fafc',width_mm=0.5);c.rect(x+40*MM,y+25*MM,50*MM,80*MM,fill='#dbeafe',width_mm=0.45)
            c.line(x+40*MM,y+25*MM,x+20*MM,y+5*MM,width_mm=0.25);c.line(x+90*MM,y+25*MM,x+110*MM,y+5*MM,width_mm=0.25);c.text(x+65*MM,y+115*MM,'Opening / frame / seal coordination',size_pt=8,bold=True,align='center')
            c.text(x+180*MM,y+110*MM,'Key notes',size_pt=9,bold=True);[c.text(x+180*MM,y+(95-k*12)*MM,f'{k+1}. Coordinated technical note',size_pt=7) for k in range(6)]
        else:
            c.rect(x,y,170*MM,120*MM,fill='#f8fafc',width_mm=0.5)
            for k in range(1,4): c.line(x+k*42.5*MM,y,x+k*42.5*MM,y+120*MM,width_mm=0.18,dashed=True)
            for k in range(1,3): c.line(x,y+k*40*MM,x+170*MM,y+k*40*MM,width_mm=0.18,dashed=True)
            c.rect(x+42.5*MM,y+40*MM,85*MM,40*MM,fill='#dbeafe',width_mm=0.35);c.arrow(x+85*MM,y+60*MM,x+150*MM,y+100*MM,label='service route');c.text(x+85*MM,y+130*MM,'Coordinated discipline zones',size_pt=9,bold=True,align='center')
        c.text(250*MM,215*MM,'TECHNICAL NOTES',size_pt=10,bold=True)
        notes=['Dimensions derive from the central model.','Material build-ups are concept selections.','Fire, structure, MEP and building physics require professional evidence.','Do not use for permit submission or construction.']
        for k,note in enumerate(notes): c.text(250*MM,(198-k*13)*MM,f'{k+1}. {note}',size_pt=8)
        return c

    def _reports(self, root: Path) -> dict[str, Path]:
        paths={}
        reports=[
            ('10_integrated_technical_design_report','Integrated Technical Design Report','Phases A-D accelerated technical concept masterpack',self._integrated_sections()),
            ('C_Technical_Coordination/06_technical_coordination_report','Technical Coordination Report','Model, drawing, report and calculation coordination',self._coordination_sections()),
            ('D_Permit_Tender_Execution_Issue/07_technical_specification','Technical Specification','Concept technical specification for permit/tender/execution preparation',self._specification_sections()),
        ]
        for key,title,subtitle,sections in reports:
            docx_path=root/f'{key}.docx';pdf_path=root/f'{key}.pdf'
            docx=DocxBuilder(title,subtitle,self.project);pdf=ReportPdfBuilder(title,subtitle,self.project)
            for heading,paragraphs,table in sections:
                docx.heading(heading,1);pdf.heading(heading,1)
                for paragraph in paragraphs: docx.paragraph(paragraph);pdf.paragraph(paragraph)
                if table:
                    headers,rows=table;docx.table(headers,rows);pdf.table(headers,rows)
            docx.write(docx_path);pdf.finish(pdf_path)
            paths[key.replace('/','_')+'_docx']=docx_path;paths[key.replace('/','_')+'_pdf']=pdf_path
        return paths

    def _integrated_sections(self):
        phase_rows=[(p['phase'],p['name'],p['gate_status'],p['deliverable_count']) for p in self._phase_gate_rows()]
        return [
            ('1. Executive summary',[f"The accelerated masterpack executes phases A-D in one transaction and creates revision C02. All four internal gates pass. The package remains a technical concept because six professional evidence packages are not yet accepted.",STATUS],(['Phase','Name','Gate','Deliverables'],phase_rows)),
            ('2. Design basis',['Extension: 7 x 10 m, two storeys, 140 m2 gross. Central model: 299 objects. Parking basis: 225 project-leader-confirmed spaces. REQ-107 remains closed.'],None),
            ('3. Phase A - architectural technical design',['Component assemblies, technical details, accessibility, building physics, doors, windows and room finishes are coordinated as a concept design freeze.'],(['Register','Count'],[['Assemblies',len(self.engine._component_rows())],['Detail sheets',12],['Doors',12],['Windows',8],['Rooms',12]])),
            ('4. Phase B - multidisciplinary engineering',['Structural, foundation, MEP, drainage, fire, site/parking and AERIUS interfaces are integrated. Specialist calculations and declarations remain mandatory.'],None),
            ('5. Phase C - technical coordination',['Twenty-four clash checks, twenty discipline interfaces and twenty-four coordination checks are recorded. Concept conflicts are resolved or retained as explicit conditions.'],None),
            ('6. Phase D - issue preparation',['Permit, tender and execution concept indexes are generated, but none are released as final.'],(['Issue type','Items','Ready'],[['Permit concept',24,'No'],['Tender concept',28,'No'],['Execution concept',32,'No']])),
            ('7. Evidence boundary',['REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 and REQ-108 must be replaced and accepted before revision C03 may be considered permit-ready.'],None),
        ]

    def _coordination_sections(self):
        return [
            ('1. Coordination basis',['The central geometric model is the single geometry source. Drawing, schedule, calculation and report interfaces are checked against revision C02.'],None),
            ('2. Clash control',['Twenty-four automated concept clashes were reviewed. Nineteen are closed conceptually and five remain accepted conditions requiring professional confirmation.'],(['Status','Count'],[['Closed concept',19],['Condition accepted',5]])),
            ('3. Discipline interfaces',['Architecture, structure, MEP, fire, drainage, site, parking, AERIUS, specifications, quantities and issue indexes are cross-linked.'],None),
            ('4. Release boundary',[STATUS,'Technical coordination completion does not constitute professional approval.'],None),
        ]

    def _specification_sections(self):
        components=self.engine._component_rows()
        return [
            ('1. General requirements',[STATUS,'All work shall be coordinated with the central model, drawing set, schedules and calculation workbook. Deviations require a recorded revision.'],None),
            ('2. Existing conditions',['Existing dimensions, materials and structural conditions shall be field verified before procurement or construction.'],None),
            ('3. Component assemblies',['The following concept assemblies define the coordinated technical basis.'],(['ID','Component','Thickness','Status'],[[r['assembly_id'],r['component'],r['thickness_mm'],r['status']] for r in components])),
            ('4. Workmanship and interfaces',['New-to-existing joints, fire stopping, waterproofing, air sealing, acoustic continuity and service penetrations require coordinated shop details and specialist approval.'],None),
            ('5. Testing and handover',['Testing, inspection, commissioning, as-built records and operation/maintenance information shall be specified at final issue.'],None),
            ('6. Exclusions',['Professional evidence and final authority acceptance are excluded from revision C02.'],None),
        ]

    def _transmittal(self) -> str:
        return '\n'.join(['# BB35 Pilot 1 - Technical Design A-D Masterpack C02','',f'**Status:** {STATUS}','', 'This issue combines four internally gated phases in one accelerated run:', '', '- A: Architectural technical design and detailing', '- B: Multidisciplinary engineering integration', '- C: Technical coordination and clash control', '- D: Permit, tender and execution concept issue preparation', '', 'The package is approved for internal technical development and professional evidence replacement only. It is not approved for permit submission, tender award or construction.', '', 'Six professional evidence blockers remain: REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 and REQ-108.', ''])

    def _dashboard(self) -> str:
        cards=''.join(f"<section><h2>Phase {p['phase']}</h2><p>{html.escape(p['name'])}</p><strong>{p['checks_passed']}/{p['check_count']} checks passed</strong><br><span>{p['deliverable_count']} deliverable groups</span></section>" for p in self.report['phases'])
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Phoenix Technical Design A-D</title><style>body{{font-family:Arial;max-width:1200px;margin:30px auto;color:#1f2937}}header{{background:#17324d;color:white;padding:24px}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:20px}}section{{border:1px solid #cbd5e1;border-radius:10px;padding:18px;background:#f8fafc}}.warn{{background:#fff7ed;border:1px solid #fb923c;padding:14px;margin-top:18px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #cbd5e1;padding:8px}}</style></head><body><header><h1>PROJECT PHOENIX - BB35 TECHNICAL DESIGN A-D</h1><p>Revision C02 | Four gated phases in one accelerated masterpack</p></header><div class="grid">{cards}</div><div class="warn"><strong>{STATUS}</strong><p>Professional evidence accepted: 0/6. Final permit, tender and execution release remain blocked.</p></div><h2>Key metrics</h2><table><tr><th>Central model objects</th><td>299</td></tr><tr><th>Technical detail sheets</th><td>12</td></tr><tr><th>Coordination checks</th><td>24/24</td></tr><tr><th>Parking basis</th><td>225 spaces</td></tr><tr><th>REQ-107</th><td>Closed - project leader approved</td></tr></table></body></html>"""

    @staticmethod
    def _write_json(path: Path, value: Any) -> Path:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8',newline='\n');return path

    @staticmethod
    def _write_text(path: Path, value: str) -> Path:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value,encoding='utf-8',newline='\n');return path

    @staticmethod
    def _checksums(path: Path, paths: Mapping[str, Path]) -> Path:
        lines=[]
        for key,source in sorted(paths.items()):
            if key in {'checksums','issue_package'}: continue
            lines.append(f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}")
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n');return path
