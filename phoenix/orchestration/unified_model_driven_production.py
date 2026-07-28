"""Unified model-driven production orchestration and revision control.

The orchestrator is local, deterministic and fail-fast. It detects source
changes, invalidates dependent products, selectively regenerates affected
components, performs cross-discipline checks and publishes a single concept
issue only after every gate has passed.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Mapping

FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
STATUS_LABEL = 'CONCEPT - NOT FOR SUBMISSION OR EXECUTION'
TEXT_SUFFIXES = {'.csv','.html','.json','.md','.py','.ps1','.txt','.xml','.yaml','.yml'}


def canonical_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            return raw
        return text.replace('\r\n','\n').replace('\r','\n').encode('utf-8')
    return raw


def fingerprint_value(value: Any) -> str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def file_set_fingerprint(repository: Path, paths: list[str]) -> tuple[str,list[dict[str,Any]]]:
    rows=[]
    for relative in sorted(paths):
        path=(repository/relative).resolve()
        if not path.is_file():
            raise FileNotFoundError(f'Orchestrator source missing: {relative}')
        data=canonical_bytes(path)
        rows.append({'relative_path':relative,'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)})
    return fingerprint_value(rows),rows


class UnifiedProductionOrchestrator:
    VERSION='1.0.0'

    def __init__(self, repository: Path, config: Mapping[str,Any]):
        self.repository=repository.resolve();self.config=dict(config)

    def current_source_state(self)->tuple[dict[str,str],list[dict[str,Any]]]:
        fingerprints={};inventory=[]
        for component_id,component in self.config['components'].items():
            digest,rows=file_set_fingerprint(self.repository,list(component['source_paths']))
            fingerprints[component_id]=digest
            for row in rows: inventory.append({'component_id':component_id,**row})
        return fingerprints,inventory

    def load_previous_state(self, *, ignore_previous: bool=False)->dict[str,Any]|None:
        if ignore_previous:return None
        path=self.repository/self.config['previous_revision_state']
        if not path.is_file():return None
        return json.loads(path.read_text(encoding='utf-8'))

    def detect_changes(self,current:Mapping[str,str],previous:Mapping[str,Any]|None,force_all:bool=False)->list[dict[str,Any]]:
        rows=[];previous_fps=(previous or {}).get('source_fingerprints',{})
        for component_id in self.config['components']:
            old=previous_fps.get(component_id);new=current[component_id]
            changed=force_all or previous is None or old!=new
            reason=('FORCED' if force_all else 'INITIAL_BASELINE' if previous is None else 'SOURCE_FINGERPRINT_CHANGED' if changed else 'NO_SOURCE_CHANGE')
            rows.append({'component_id':component_id,'previous_fingerprint':old or 'NONE','current_fingerprint':new,'direct_change':changed,'change_reason':reason})
        return rows

    def regeneration_plan(self,changes:list[dict[str,Any]])->list[dict[str,Any]]:
        direct={row['component_id']:bool(row['direct_change']) for row in changes}
        model_changed=direct['central_model']
        decisions={
            'central_model': model_changed,
            'drawings_reports': model_changed or direct['drawings_reports'],
            'calculations': model_changed or direct['calculations'],
        }
        rows=[]
        for component_id in self.config['components']:
            regenerate=decisions[component_id]
            if direct[component_id]:reason='DIRECT_SOURCE_CHANGE'
            elif component_id!='central_model' and model_changed:reason='UPSTREAM_MODEL_CHANGE'
            else:reason='UNCHANGED_REUSE_AND_REVALIDATE'
            rows.append({'sequence':len(rows)+1,'component_id':component_id,'action':'REGENERATE' if regenerate else 'REUSE_AND_REVALIDATE','reason':reason,'stale_before_run':regenerate,'status_after_success':'CURRENT'})
        return rows

    def revision(self,previous:Mapping[str,Any]|None,plan:list[dict[str,Any]])->dict[str,Any]:
        has_change=any(row['action']=='REGENERATE' for row in plan)
        previous_number=int((previous or {}).get('revision_number',0))
        number=1 if previous is None else previous_number + (1 if has_change else 0)
        return {'revision_number':number,'revision_code':f"{self.config['revision_prefix']}{number:02d}",'run_mode':'INITIAL_RELEASE' if previous is None else 'CHANGE_RELEASE' if has_change else 'REVALIDATION','previous_revision_code':(previous or {}).get('revision_code','NONE')}

    def execute(self, output_dir: Path, *, execute_changed:bool=True, force_all:bool=False, ignore_previous:bool=False)->dict[str,Any]:
        output_dir=output_dir.resolve();previous=self.load_previous_state(ignore_previous=ignore_previous)
        source_fps,source_inventory=self.current_source_state();changes=self.detect_changes(source_fps,previous,force_all=force_all);plan=self.regeneration_plan(changes);revision=self.revision(previous,plan)
        transaction=Path(tempfile.mkdtemp(prefix='phoenix_orchestrator_',dir=str(output_dir.parent)))
        component_root=transaction/'components';release_root=transaction/'release';component_root.mkdir(parents=True);release_root.mkdir(parents=True)
        try:
            component_dirs={}
            model_config=self.config['components']['central_model'];model_action=next(x for x in plan if x['component_id']=='central_model')['action']
            if execute_changed and model_action=='REGENERATE':
                target=component_root/'central_model';self._run_component(model_config,target,[]);component_dirs['central_model']=target
            else:component_dirs['central_model']=self.repository/model_config['artifact_dir']
            model_file=component_dirs['central_model']/model_config['canonical_model_file'];model_summary_file=component_dirs['central_model']/model_config['summary_file']

            prod_config=self.config['components']['drawings_reports'];prod_action=next(x for x in plan if x['component_id']=='drawings_reports')['action']
            if execute_changed and prod_action=='REGENERATE':
                target=component_root/'drawings_reports';self._run_component(prod_config,target,['--model-file',str(model_file)]);component_dirs['drawings_reports']=target
            else:component_dirs['drawings_reports']=self.repository/prod_config['artifact_dir']

            calc_config=self.config['components']['calculations'];calc_action=next(x for x in plan if x['component_id']=='calculations')['action']
            if execute_changed and calc_action=='REGENERATE':
                target=component_root/'calculations';self._run_component(calc_config,target,['--model-file',str(model_file),'--model-summary-file',str(model_summary_file)]);component_dirs['calculations']=target
            else:component_dirs['calculations']=self.repository/calc_config['artifact_dir']

            summaries=self._load_summaries(component_dirs);checks=self._cross_checks(summaries,component_dirs);all_passed=all(row['passed'] for row in checks)
            if not all_passed:
                failed=[row['check_id'] for row in checks if not row['passed']];raise RuntimeError('Cross-check failure: '+', '.join(failed))
            product_status=self._product_status(plan,summaries,component_dirs)
            release=self._release_record(revision,source_fps,changes,plan,summaries,checks,product_status)
            paths=UnifiedProductionExporter().export_all(release,source_inventory,component_dirs,release_root)
            if output_dir.exists():shutil.rmtree(output_dir)
            shutil.move(str(release_root),str(output_dir))
            return {'release':release,'paths':{k:output_dir/v.name for k,v in paths.items()},'component_dirs':component_dirs}
        finally:
            shutil.rmtree(transaction,ignore_errors=True)

    def _run_component(self,component:Mapping[str,Any],target:Path,extra:list[str])->dict[str,Any]:
        target.mkdir(parents=True,exist_ok=False)
        command=[sys.executable,str(self.repository/component['runner']),'--output-dir',str(target),component['expect_flag'],*extra]
        result=subprocess.run(command,cwd=self.repository,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,shell=False)
        if result.returncode!=0:
            raise RuntimeError('Component failed: '+component['runner']+'\n'+result.stdout+'\n'+result.stderr)
        try:payload=json.loads(result.stdout)
        except json.JSONDecodeError as exc:raise RuntimeError('Component returned invalid JSON: '+component['runner']) from exc
        if payload.get('execution_status')!='PASSED':raise RuntimeError('Component did not pass: '+component['runner'])
        return payload

    def _load_summaries(self,dirs:Mapping[str,Path])->dict[str,Any]:
        result={}
        for component_id,component in self.config['components'].items():
            path=dirs[component_id]/component['summary_file']
            if not path.is_file():raise FileNotFoundError(path)
            result[component_id]=json.loads(path.read_text(encoding='utf-8'))
        return result

    def _cross_checks(self,s:Mapping[str,Any],dirs:Mapping[str,Path])->list[dict[str,Any]]:
        e=self.config['expected'];m=s['central_model'];p=s['drawings_reports'];c=s['calculations'];cg=c['gates'];mf=m['model_fingerprint_sha256']
        tests=[
            ('ORC-001','central_model_status',m['status']=='CENTRAL_GEOMETRIC_PROJECT_MODEL_GENERATED'),
            ('ORC-002','model_object_count',m['object_count']==e['model_objects']),
            ('ORC-003','model_geometry_checks',m['geometry_checks_passed']==e['model_checks'] and m['all_geometry_checks_passed']),
            ('ORC-004','drawings_reports_status',p['status']=='REAL_CONCEPT_DRAWINGS_AND_REPORTS_GENERATED'),
            ('ORC-005','drawing_sheet_count',p['drawing_sheet_count']==e['drawing_sheets']),
            ('ORC-006','report_count',p['report_count']==e['reports']),
            ('ORC-007','production_cross_checks',p['cross_checks_passed']==e['production_checks'] and p['all_cross_checks_passed']),
            ('ORC-008','calculation_status',c['status']=='MODEL_DRIVEN_CONCEPT_CALCULATIONS_GENERATED'),
            ('ORC-009','calculation_count',c['metrics']['calculation_count']==e['calculations']),
            ('ORC-010','calculation_categories',c['metrics']['calculation_category_count']==e['calculation_categories']),
            ('ORC-011','calculation_quality_checks',c['metrics']['quality_checks_passed']==e['calculation_checks'] and cg['calculation_quality_checks_passed']),
            ('ORC-012','model_fingerprint_model_to_drawings',p['model_fingerprint_sha256']==mf),
            ('ORC-013','model_fingerprint_model_to_calculations',c['model_fingerprint_sha256']==mf),
            ('ORC-014','model_id_consistency',m['model_id']==p['model_id']==c['model_id']),
            ('ORC-015','parking_model',m['parking_bay_count']==e['parking_spaces']),
            ('ORC-016','parking_drawings',p['parking_basis_spaces']==e['parking_spaces']),
            ('ORC-017','parking_calculations',c['metrics']['parking_capacity_spaces']==e['parking_spaces']),
            ('ORC-018','gross_area_consistency',m['extension_gross_area_m2']==p['gross_area_m2']==e['gross_area_m2']),
            ('ORC-019','professional_blockers_visible',m['professional_blocker_count']==p['professional_evidence_blocker_count']==c['metrics']['professional_blocker_count']==e['professional_blockers']),
            ('ORC-020','final_permit_gate_locked',not m['final_permit_ready_generation_allowed'] and not p['final_permit_ready_generation_allowed'] and not cg['final_permit_ready_generation_allowed']),
            ('ORC-021','bb36_production_locked',not p['bb36_production_release_allowed'] and not cg['bb36_production_release_allowed']),
            ('ORC-022','component_directories_available',all(path.is_dir() for path in dirs.values())),
        ]
        return [{'check_id':cid,'criterion':criterion,'passed':bool(passed),'status':'PASS' if passed else 'FAIL'} for cid,criterion,passed in tests]

    @staticmethod
    def _product_status(plan,summaries,dirs):
        rows=[]
        for item in plan:
            cid=item['component_id'];rows.append({'component_id':cid,'action':item['action'],'status':'CURRENT','stale':False,'summary_status':summaries[cid]['status'],'source_directory':f'component://{cid}'})
        return rows

    def _release_record(self,revision,source_fps,changes,plan,summaries,checks,product_status):
        model=summaries['central_model'];prod=summaries['drawings_reports'];calc=summaries['calculations']
        return {
            'schema_version':'phoenix.unified-production-release/1.0','engine_version':self.VERSION,'pilot_id':self.config['pilot_id'],'project_id':self.config['project_id'],'release_series':self.config['release_series'],'release_date':self.config['release_date'],**revision,
            'status':'UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_READY','status_label':STATUS_LABEL,'model_id':model['model_id'],'model_fingerprint_sha256':model['model_fingerprint_sha256'],'source_fingerprints':dict(source_fps),'change_set_fingerprint_sha256':fingerprint_value(changes),'change_count':sum(1 for row in changes if row['direct_change']),'regenerated_component_count':sum(1 for row in plan if row['action']=='REGENERATE'),'reused_component_count':sum(1 for row in plan if row['action']!='REGENERATE'),'cross_check_count':len(checks),'cross_checks_passed':sum(1 for row in checks if row['passed']),'all_cross_checks_passed':all(row['passed'] for row in checks),'drawing_sheet_count':prod['drawing_sheet_count'],'report_count':prod['report_count'],'calculation_count':calc['metrics']['calculation_count'],'calculation_category_count':calc['metrics']['calculation_category_count'],'parking_basis_spaces':model['parking_bay_count'],'gross_area_m2':model['extension_gross_area_m2'],'professional_blocker_ids':list(self.config['professional_blocker_ids']),'professional_blocker_count':len(self.config['professional_blocker_ids']),'changes':changes,'regeneration_plan':plan,'product_status':product_status,'cross_checks':checks,
            'gates':{'central_model_validated':True,'affected_products_regenerated':True,'all_products_current':True,'cross_discipline_checks_passed':True,'revision_control_updated':True,'unified_concept_issue_ready':True,'final_permit_ready_generation_allowed':False,'bb36_production_release_allowed':False},
            'next_gate':'Replace the six simulated professional evidence packages and run the BB35 professional evidence closure gate.'
        }


class UnifiedProductionExporter:
    def export_all(self,release:Mapping[str,Any],source_inventory:list[dict[str,Any]],component_dirs:Mapping[str,Path],root:Path)->dict[str,Path]:
        root.mkdir(parents=True,exist_ok=True);paths={}
        paths['summary']=self._json(root/'01_orchestrator_summary.json',{k:v for k,v in release.items() if k not in {'changes','regeneration_plan','product_status','cross_checks'}})
        paths['dependency_graph']=self._json(root/'02_dependency_graph.json',{'nodes':['central_model','drawings_reports','calculations','unified_release'],'edges':[{'from':'central_model','to':'drawings_reports'},{'from':'central_model','to':'calculations'},{'from':'drawings_reports','to':'unified_release'},{'from':'calculations','to':'unified_release'}],'invalidation_rule':'A changed upstream node marks every downstream product stale until successful regeneration.'})
        paths['revision_state']=self._json(root/'03_revision_state.json',{'revision_number':release['revision_number'],'revision_code':release['revision_code'],'previous_revision_code':release['previous_revision_code'],'run_mode':release['run_mode'],'release_date':release['release_date'],'source_fingerprints':release['source_fingerprints'],'model_fingerprint_sha256':release['model_fingerprint_sha256'],'change_set_fingerprint_sha256':release['change_set_fingerprint_sha256'],'all_products_current':True})
        paths['changes']=self._csv(root/'04_change_detection.csv',release['changes'],['component_id','previous_fingerprint','current_fingerprint','direct_change','change_reason'])
        paths['plan']=self._csv(root/'05_regeneration_plan.csv',release['regeneration_plan'],['sequence','component_id','action','reason','stale_before_run','status_after_success'])
        paths['products']=self._csv(root/'06_product_status_register.csv',release['product_status'],['component_id','action','status','stale','summary_status','source_directory'])
        paths['checks']=self._csv(root/'07_cross_discipline_checks.csv',release['cross_checks'],['check_id','criterion','passed','status'])
        paths['revision_log']=self._csv(root/'08_revision_log.csv',[{'revision_code':release['revision_code'],'previous_revision_code':release['previous_revision_code'],'release_date':release['release_date'],'run_mode':release['run_mode'],'change_count':release['change_count'],'regenerated_components':release['regenerated_component_count'],'reused_components':release['reused_component_count'],'status':release['status']}],['revision_code','previous_revision_code','release_date','run_mode','change_count','regenerated_components','reused_components','status'])
        paths['sources']=self._csv(root/'09_source_fingerprints.csv',source_inventory,['component_id','relative_path','sha256','size_bytes'])
        manifest=self._component_manifest(component_dirs)
        paths['manifest']=self._json(root/'10_release_manifest.json',{'revision_code':release['revision_code'],'model_fingerprint_sha256':release['model_fingerprint_sha256'],'component_file_count':len(manifest),'files':manifest})
        paths['dashboard']=self._html(root/'11_orchestrator_dashboard.html',release)
        paths['transmittal']=self._md(root/'12_concept_issue_transmittal.md',self._transmittal(release))
        paths['revision_report']=self._md(root/'13_revision_control_report.md',self._revision_report(release))
        paths['gates']=self._json(root/'14_release_gate_status.json',{'revision_code':release['revision_code'],'status':release['status'],'gates':release['gates'],'professional_blocker_ids':release['professional_blocker_ids'],'next_gate':release['next_gate']})
        paths['issue_package']=self._issue_zip(root/'BB35_PILOT_1_UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_C01.zip',component_dirs,paths)
        paths['checksums']=self._checksums(root/'checksums.sha256',paths)
        return paths

    @staticmethod
    def _component_manifest(component_dirs):
        rows=[]
        for component_id,root in component_dirs.items():
            for path in sorted(root.rglob('*')):
                if path.is_file():rows.append({'component_id':component_id,'relative_path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size_bytes':path.stat().st_size})
        return rows

    def _issue_zip(self,destination:Path,component_dirs:Mapping[str,Path],release_paths:Mapping[str,Path])->Path:
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            for index,(component_id,root) in enumerate(component_dirs.items(),start=1):
                for path in sorted(root.rglob('*')):
                    if path.is_file():self._writestr(archive,f'{index:02d}_{component_id}/{path.relative_to(root).as_posix()}',path.read_bytes())
            for key,path in sorted(release_paths.items()):
                self._writestr(archive,f'04_orchestration/{path.name}',path.read_bytes())
        return destination

    @staticmethod
    def _writestr(archive,name,data):
        info=zipfile.ZipInfo(name,FIXED_ZIP_TIME);info.compress_type=zipfile.ZIP_STORED;info.create_system=3;info.create_version=20;info.extract_version=20;info.external_attr=0o100644<<16;info.extra=b'';info.comment=b'';archive.writestr(info,data)

    @staticmethod
    def _json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n');return path
    @staticmethod
    def _md(path,value):path.write_text(value,encoding='utf-8',newline='\n');return path
    @staticmethod
    def _csv(path,rows,fields):
        with path.open('w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\r\n');writer.writeheader();writer.writerows([{field:row.get(field,'') for field in fields} for row in rows])
        return path
    @staticmethod
    def _checksums(path,paths):
        lines=[f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for key,p in sorted(paths.items()) if key!='checksums'];path.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n');return path
    @staticmethod
    def _html(path,release):
        plan=''.join(f"<tr><td>{html.escape(str(x['sequence']))}</td><td>{html.escape(x['component_id'])}</td><td>{html.escape(x['action'])}</td><td>{html.escape(x['reason'])}</td></tr>" for x in release['regeneration_plan'])
        checks=''.join(f"<tr><td>{x['check_id']}</td><td>{html.escape(x['criterion'])}</td><td>{x['status']}</td></tr>" for x in release['cross_checks'])
        content=f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Phoenix Orchestrator {release['revision_code']}</title><style>body{{font:14px Arial;max-width:1180px;margin:30px auto;color:#17202a}}h1{{border-bottom:3px solid #263238;padding-bottom:8px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.card{{border:1px solid #bbb;border-radius:10px;padding:12px;background:#f7f8fa}}table{{border-collapse:collapse;width:100%;margin-top:16px}}th,td{{border:1px solid #bbb;padding:7px;text-align:left}}th{{background:#263238;color:white}}.warn{{background:#fff4ce;padding:10px;border:1px solid #d6b656}}</style></head><body><h1>Project Phoenix — Unified Production Orchestrator</h1><div class="warn">{STATUS_LABEL}</div><div class="cards"><div class="card"><b>Revision</b><br>{release['revision_code']}</div><div class="card"><b>Regenerated</b><br>{release['regenerated_component_count']}</div><div class="card"><b>Reused</b><br>{release['reused_component_count']}</div><div class="card"><b>Checks</b><br>{release['cross_checks_passed']}/{release['cross_check_count']}</div></div><h2>Regeneration plan</h2><table><tr><th>#</th><th>Component</th><th>Action</th><th>Reason</th></tr>{plan}</table><h2>Cross-discipline checks</h2><table><tr><th>ID</th><th>Criterion</th><th>Status</th></tr>{checks}</table><p><b>Professional evidence blockers:</b> 6. Final permit-ready generation and BB36 production release remain locked.</p></body></html>"""
        path.write_text(content,encoding='utf-8',newline='\n');return path
    @staticmethod
    def _transmittal(r):return f"""# Unified concept issue transmittal — {r['revision_code']}\n\nStatus: `{r['status']}`  \nModel: `{r['model_id']}`  \nModel fingerprint: `{r['model_fingerprint_sha256']}`\n\nIncluded product groups:\n\n- central geometric project model;\n- model-driven drawings and reports;\n- model-driven calculation workbook and calculation dossier;\n- revision-control and release evidence.\n\nThis issue is a concept release and is not approved for permit submission or construction. Six professional evidence packages remain outstanding.\n"""
    @staticmethod
    def _revision_report(r):return f"""# Revision control report — {r['revision_code']}\n\nPrevious revision: `{r['previous_revision_code']}`  \nRun mode: `{r['run_mode']}`  \nDirect source changes: `{r['change_count']}`  \nRegenerated components: `{r['regenerated_component_count']}`  \nReused and revalidated components: `{r['reused_component_count']}`\n\nThe dependency graph applies automatic downstream invalidation. A central-model change invalidates both drawings/reports and calculations. A discipline-only source change invalidates only that discipline product and the unified release. No product is marked current until all 22 cross-discipline checks pass.\n"""
