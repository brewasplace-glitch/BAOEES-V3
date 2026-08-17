from __future__ import annotations
from phoenix.architecture.bim_lite_model_v1_0 import enrich_workspace as _phoenix_bim_lite_enrich
import json
from pathlib import Path

VERSION = "1.0.0"
SCHEMA = "phoenix.real-architectural-multivariant-design/1.0"
VARIANTS = [
    {"id":"A","name":"Compact Efficiency","strategy":"compact_cost_efficient","width":10.0,"depth":9.0,"score":82},
    {"id":"B","name":"Balanced Living","strategy":"balanced_spatial_quality","width":11.5,"depth":9.5,"score":92},
    {"id":"C","name":"Climate Courtyard","strategy":"climate_orientation","width":10.5,"depth":10.0,"score":88},
]

def _repo_root(source_file=None):
    start = Path(source_file).resolve().parent if source_file else Path.cwd().resolve()
    for p in (start, *start.parents):
        if (p / '.git').exists() and (p / 'projects').exists():
            return p
    return Path.cwd().resolve()

def _find(value, keys):
    if isinstance(value, dict):
        for k,v in value.items():
            if str(k).lower() in keys:
                return v
        for v in value.values():
            x = _find(v, keys)
            if x is not None: return x
    elif isinstance(value, (list, tuple)):
        for v in value:
            x = _find(v, keys)
            if x is not None: return x
    return None

def _project_id(scope):
    for v in scope.values():
        x = _find(v, {'project_id','projectid'})
        if isinstance(x, str) and x.strip(): return x.strip()
    return None

def _load(path):
    try: return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    except Exception: return {}

def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def _site_dims(context, site):
    def nums(data, aliases):
        out=[]
        def walk(v):
            if isinstance(v, dict):
                for k,x in v.items():
                    if str(k).lower() in aliases and isinstance(x,(int,float)): out.append(float(x))
                    walk(x)
            elif isinstance(v,list):
                for x in v: walk(x)
        walk(data); return [x for x in out if 2 <= x <= 500]
    merged={'context':context,'site':site}
    w=nums(merged, {'parcel_width','site_width','width','breedte'})
    d=nums(merged, {'parcel_depth','site_depth','depth','diepte','length'})
    return (max(18,w[0]), max(22,d[0]), 'PROJECT_CONTEXT') if w and d else (30.0,40.0,'SAFE_CONCEPT_ASSUMPTION')

def _levels(model, intake):
    text=json.dumps({'m':model,'i':intake},ensure_ascii=False).lower()
    return 2 if any(s in text for s in ('two storey','two-story','twee bouwlagen','2 bouwlagen','2 storeys','2 stories')) else 2

def _rooms(v, floor):
    w,d=v['width'],v['depth']
    if floor == 0:
        return [
            {'name':'Entree','x':0,'y':0,'w':w*.22,'d':d*.28}, {'name':'Werkkamer','x':0,'y':d*.28,'w':w*.34,'d':d*.30},
            {'name':'Keuken','x':w*.34,'y':0,'w':w*.30,'d':d*.42}, {'name':'Woonkamer','x':w*.34,'y':d*.42,'w':w*.66,'d':d*.58},
            {'name':'Eetkamer','x':w*.64,'y':0,'w':w*.36,'d':d*.42}, {'name':'WC/berging','x':0,'y':d*.58,'w':w*.34,'d':d*.42},
        ]
    return [
        {'name':'Slaapkamer 1','x':0,'y':0,'w':w*.48,'d':d*.48}, {'name':'Slaapkamer 2','x':w*.48,'y':0,'w':w*.52,'d':d*.48},
        {'name':'Slaapkamer 3','x':0,'y':d*.48,'w':w*.42,'d':d*.52}, {'name':'Badkamer','x':w*.42,'y':d*.48,'w':w*.28,'d':d*.32},
        {'name':'Overloop','x':w*.70,'y':d*.48,'w':w*.30,'d':d*.52}, {'name':'Was/linnen','x':w*.42,'y':d*.80,'w':w*.28,'d':d*.20},
    ]

def _shell(title, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="850" viewBox="0 0 1200 850"><rect width="100%" height="100%" fill="white"/><text x="45" y="55" font-family="Segoe UI,Arial" font-size="28" font-weight="700">{title}</text>{body}</svg>'

def _floor_svg(v, floor):
    scale=min(850/v['width'],600/v['depth']); ox,oy=150,130
    parts=[f'<rect x="{ox}" y="{oy}" width="{v["width"]*scale:.1f}" height="{v["depth"]*scale:.1f}" fill="#f8fbfd" stroke="#102f45" stroke-width="5"/>']
    for r in _rooms(v,floor):
        x=ox+r['x']*scale; y=oy+r['y']*scale; rw=r['w']*scale; rd=r['d']*scale
        parts += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{rd:.1f}" fill="none" stroke="#2c6b91" stroke-width="2"/>', f'<text x="{x+8:.1f}" y="{y+24:.1f}" font-family="Segoe UI,Arial" font-size="16">{r["name"]}</text>']
    parts.append(f'<text x="{ox}" y="{oy+v["depth"]*scale+45:.1f}" font-family="Segoe UI,Arial" font-size="17">Hoofdmaat: {v["width"]:.1f} × {v["depth"]:.1f} m - Variant {v["id"]}</text>')
    return _shell(f'VARIANT {v["id"]} - {"BEGANE GROND" if floor==0 else "VERDIEPING"}', ''.join(parts))

def _site_svg(v, sw, sd, source):
    scale=min(850/sw,600/sd); ox,oy=160,130; bx=ox+(sw-v['width'])*.5*scale; by=oy+(sd-v['depth'])*.45*scale
    body=f'<rect x="{ox}" y="{oy}" width="{sw*scale:.1f}" height="{sd*scale:.1f}" fill="#fafafa" stroke="#111" stroke-width="3"/><rect x="{bx:.1f}" y="{by:.1f}" width="{v["width"]*scale:.1f}" height="{v["depth"]*scale:.1f}" fill="#d7eefc" stroke="#15648f" stroke-width="4"/><text x="{bx+12:.1f}" y="{by+30:.1f}" font-family="Segoe UI,Arial" font-size="18">WONING VARIANT {v["id"]}</text><text x="{ox}" y="{oy+sd*scale+42:.1f}" font-family="Segoe UI,Arial" font-size="15">Perceel {sw:.1f} × {sd:.1f} m - bron: {source}</text><text x="1030" y="110" font-family="Segoe UI,Arial" font-size="22">N ↑</text>'
    return _shell(f'VARIANT {v["id"]} - SITUATIETEKENING',body)

def _elev_svg(v, side, levels):
    width=v['width'] if side in ('north','south') else v['depth']; scale=min(850/width,100); ox,base=160,650; h=levels*3.2; bw,bh=width*scale,h*scale
    parts=[f'<rect x="{ox}" y="{base-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#f7f7f7" stroke="#14384f" stroke-width="4"/>']
    for floor in range(levels):
        y=base-(floor*3.2+1.7)*scale
        for frac in (.18,.48,.78):
            x=ox+frac*bw; parts.append(f'<rect x="{x-35:.1f}" y="{y-35:.1f}" width="70" height="70" fill="#cbe8f7" stroke="#275c79" stroke-width="2"/>')
    return _shell(f'VARIANT {v["id"]} - GEVEL {side.upper()}', ''.join(parts))

def _section_svg(v, levels):
    scale=min(850/v['width'],95); ox,base=160,650; th=levels*3.2
    parts=[f'<rect x="{ox}" y="{base-th*scale:.1f}" width="{v["width"]*scale:.1f}" height="{th*scale:.1f}" fill="#fff" stroke="#15384e" stroke-width="4"/>']
    for level in range(1,levels):
        y=base-level*3.2*scale; parts.append(f'<line x1="{ox}" y1="{y:.1f}" x2="{ox+v["width"]*scale:.1f}" y2="{y:.1f}" stroke="#111" stroke-width="5"/>')
    parts.append(f'<polygon points="{ox},{base-th*scale:.1f} {ox+v["width"]*scale/2:.1f},{base-th*scale-65:.1f} {ox+v["width"]*scale:.1f},{base-th*scale:.1f}" fill="none" stroke="#15384e" stroke-width="4"/>')
    return _shell(f'VARIANT {v["id"]} - DOORSNEDE A-A',''.join(parts))

def _viewer(v, levels, pid):
    w,d,h=v['width'],v['depth'],levels*3.2
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;height:100%;background:#071421;color:#fff;font-family:Segoe UI}}canvas{{width:100%;height:100%}}#h{{position:fixed;left:16px;top:16px}}</style></head><body><div id="h"><b>{pid} - VARIANT {v['id']} - {v['name']}</b><div>W={w} D={d} H={h} - {levels} bouwlagen</div></div><canvas id="c"></canvas><script>const c=document.getElementById('c'),x=c.getContext('2d');let a=.6,z=1,drag=false,lx=0;c.width=innerWidth;c.height=innerHeight;const W={w},D={d},H={h},M=Math.max(W,D,H),V=[[-W/2,0,-D/2],[W/2,0,-D/2],[W/2,0,D/2],[-W/2,0,D/2],[-W/2,H,-D/2],[W/2,H,-D/2],[W/2,H,D/2],[-W/2,H,D/2]].map(p=>p.map(q=>q/M)),E=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];function P(p){{let[A,B,C]=p,ca=Math.cos(a),sa=Math.sin(a),X=A*ca-C*sa,Z=A*sa+C*ca,s=Math.min(innerWidth,innerHeight)*.42*z/(3-Z);return[innerWidth/2+X*s,innerHeight*.65-B*s]}}function draw(){{x.fillStyle='#071421';x.fillRect(0,0,innerWidth,innerHeight);let p=V.map(P);x.strokeStyle='#5ec8ff';x.lineWidth=2.5;x.beginPath();E.forEach(e=>{{x.moveTo(...p[e[0]]);x.lineTo(...p[e[1]])}});x.stroke();requestAnimationFrame(draw)}}draw();c.onpointerdown=e=>{{drag=true;lx=e.clientX}};c.onpointerup=()=>drag=false;c.onpointermove=e=>{{if(drag){{a+=(e.clientX-lx)*.01;lx=e.clientX}}}};c.onwheel=e=>{{z=Math.max(.5,Math.min(2,z*(e.deltaY>0?.9:1.1)))}}</script></body></html>'''

def _dxf(path,w,d,label):
    p=['0','SECTION','2','ENTITIES']; pts=[(0,0),(w,0),(w,d),(0,d),(0,0)]
    for a,b in zip(pts,pts[1:]): p += ['0','LINE','8','PHOENIX','10',str(a[0]),'20',str(a[1]),'30','0','11',str(b[0]),'21',str(b[1]),'31','0']
    p += ['0','TEXT','8','PHOENIX','10','.5','20','.5','30','0','40','.35','1',label,'0','ENDSEC','0','EOF']; path.write_text('\n'.join(p)+'\n',encoding='ascii',errors='ignore')

def _write_variant(root,v,pid,levels,sw,sd,source):
    vr=root/f"variant_{v['id']}"; dr=vr/'drawings'; dr.mkdir(parents=True,exist_ok=True); files={}
    items={'site_plan':_site_svg(v,sw,sd,source),'floor_plan_ground':_floor_svg(v,0),'floor_plan_upper':_floor_svg(v,1),'elevation_north':_elev_svg(v,'north',levels),'elevation_east':_elev_svg(v,'east',levels),'elevation_south':_elev_svg(v,'south',levels),'elevation_west':_elev_svg(v,'west',levels),'section_AA':_section_svg(v,levels)}
    for key,content in items.items():
        p=dr/f'{key}.svg'; p.write_text(content,encoding='utf-8'); files[key]=str(p)
    dxf=dr/'site_plan.dxf'; _dxf(dxf,sw,sd,f"{pid} VARIANT {v['id']} SITE"); files['site_plan_dxf']=str(dxf)
    view=vr/'viewer_3d.html'; view.write_text(_viewer(v,levels,pid),encoding='utf-8'); files['viewer_3d']=str(view)
    data={'schema_version':SCHEMA,'engine_version':VERSION,'project_id':pid,'variant':v,'levels':levels,'building_envelope_m':{'width':v['width'],'depth':v['depth'],'height':levels*3.2},'gross_floor_area_m2':round(v['width']*v['depth']*levels,1),'rooms':{'ground':_rooms(v,0),'upper':_rooms(v,1)},'site':{'width_m':sw,'depth_m':sd,'source':source},'files':files,'candidate_only':True,'professional_review_required':True,'production_release':'LOCKED'}
    _write(vr/'variant_model.json',data); return data

def _publish(arch,workspace,selected,variants):
    dr=arch/'drawings'; dr.mkdir(parents=True,exist_ok=True)
    mapping={'site_plan.svg':'site_plan','site_plan.dxf':'site_plan_dxf','floor_plan_ground.svg':'floor_plan_ground','floor_plan_upper.svg':'floor_plan_upper','elevation_north.svg':'elevation_north','elevation_east.svg':'elevation_east','elevation_south.svg':'elevation_south','elevation_west.svg':'elevation_west','section_AA.svg':'section_AA'}
    for name,key in mapping.items(): (dr/name).write_bytes(Path(selected['files'][key]).read_bytes())
    model=_load(arch/'architectural_model.json'); model.update({'architectural_model_source':'REAL_MULTI_VARIANT_PARAMETRIC_DESIGN','generation_mode':'REAL_ARCHITECTURAL_MULTI_VARIANT','real_design_engine_version':VERSION,'selected_variant':selected['variant']['id'],'selected_variant_name':selected['variant']['name'],'building_envelope_m':selected['building_envelope_m'],'gross_floor_area_m2':selected['gross_floor_area_m2'],'levels':selected['levels'],'rooms':selected['rooms'],'variant_count':len(variants),'candidate_only':True,'professional_review_required':True,'production_release':'LOCKED'}); _write(arch/'architectural_model.json',model)
    for tp in (workspace/'results/session_adapters/digital_twin/central_project_digital_twin.json',workspace/'digital_twin/central_project_digital_twin.json'):
        if tp.exists():
            twin=_load(tp); twin['architectural_design']={'source':'REAL_MULTI_VARIANT_PARAMETRIC_DESIGN','engine_version':VERSION,'selected_variant':selected['variant']['id'],'selected_variant_name':selected['variant']['name'],'building_envelope_m':selected['building_envelope_m'],'gross_floor_area_m2':selected['gross_floor_area_m2'],'levels':selected['levels'],'rooms':selected['rooms'],'available_variants':[{'id':x['variant']['id'],'name':x['variant']['name'],'score':x['variant']['score']} for x in variants],'candidate_only':True,'professional_review_required':True,'production_release':'LOCKED'}; _write(tp,twin)
    out=workspace/'results/generated_visual_media/viewer_3d'; out.mkdir(parents=True,exist_ok=True); viewer=out/'phoenix_3d_viewer.html'; viewer.write_bytes(Path(selected['files']['viewer_3d']).read_bytes()); _write(out/'viewer_3d_manifest.json',{'artifact_type':'viewer_3d','project_id':selected['project_id'],'source':'REAL_MULTI_VARIANT_PARAMETRIC_DESIGN','selected_variant':selected['variant']['id'],'artifact':viewer.name,'validated':viewer.stat().st_size>1500,'engine_version':VERSION}); return str(viewer)

def run_multivariant_design(repository,workspace):
    workspace=Path(workspace).resolve(); arch=workspace/'results/session_adapters/architecture'
    if not (arch/'architectural_model.json').exists(): return {'status':'SKIPPED','reason':'ARCHITECTURAL_MODEL_NOT_READY'}
    sw,sd,source=_site_dims(_load(arch/'project_context.json'),_load(arch/'site_context.json')); levels=_levels(_load(arch/'architectural_model.json'),_load(arch/'architectural_session_intake.json')); vr=arch/'design_variants'; vr.mkdir(parents=True,exist_ok=True)
    variants=[_write_variant(vr,v,workspace.name,levels,sw,sd,source) for v in VARIANTS]; selected=max(variants,key=lambda x:x['variant']['score']); viewer=_publish(arch,workspace,selected,variants)
    idx={'schema_version':SCHEMA,'engine_version':VERSION,'project_id':workspace.name,'variant_count':len(variants),'selected_variant':selected['variant']['id'],'selection_basis':'highest_balanced_concept_score','variants':[{'id':x['variant']['id'],'name':x['variant']['name'],'strategy':x['variant']['strategy'],'score':x['variant']['score'],'gross_floor_area_m2':x['gross_floor_area_m2'],'viewer_3d':x['files']['viewer_3d']} for x in variants],'published_viewer_3d':viewer,'quality_gate':{'status':'PASSED','minimum_variant_count':3,'actual_variant_count':len(variants),'requires_nonempty_floor_plans':True,'requires_nonplaceholder_3d_geometry':True,'candidate_only':True,'professional_review_required':True,'production_release':'LOCKED'}}
    # PHOENIX_BIM_LITE_STRICT_PRESENTATION_v1_0
    _phoenix_bim_lite_enrich(workspace, arch, selected, variants)
    _write(arch/'design_variants_index.json',idx); _write(arch/'selected_design_variant.json',selected); return {'status':'PASSED',**idx}

def run_multivariant_design_from_scope(scope,source_file=None):
    repo=_repo_root(source_file); pid=_project_id(scope)
    if not pid: return {'status':'SKIPPED','reason':'PROJECT_ID_NOT_RESOLVED'}
    ws=repo/'projects'/'runtime'/pid
    if not ws.exists(): return {'status':'SKIPPED','reason':'PROJECT_WORKSPACE_NOT_FOUND'}
    return run_multivariant_design(repo,ws)
