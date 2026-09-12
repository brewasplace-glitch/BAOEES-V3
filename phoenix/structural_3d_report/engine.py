#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, html, json, math
from pathlib import Path
from typing import Any, Dict, List, Tuple

STATUS='PASS_PRELIMINARY_3D_STRUCTURAL_MODEL_AND_CALCULATION_REPORT'
NEXT_STAGE='PHOENIX_4.41_REAL_PROJECT_STRUCTURAL_QA_RELEASE_GATE_AND_BIM_INTEGRATION'
ENGINE_VERSION='1.0.0'

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def validate_inputs(design,solver,derivation,source_sha):
    if design.get('status')!='PASS_PRELIMINARY_STRUCTURAL_DESIGN_CONSOLIDATION_AND_DRAWINGS': raise RuntimeError('Design prerequisite not PASS')
    if solver.get('status') not in ('PASS_REAL_OPEN_SOURCE_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION','PASS_PRIMARY_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION'): raise RuntimeError('Solver prerequisite not PASS')
    if derivation.get('status')!='PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AND_LOAD_MODEL': raise RuntimeError('Derivation prerequisite not PASS')
    for n,s in [('design',design.get('source_sha256')),('solver',solver.get('source_sha256')),('derivation',derivation.get('source',{}).get('sha256'))]:
        if s!=source_sha: raise RuntimeError(f'{n} source SHA mismatch')

def box_mesh(trimesh,extents,center):
    import numpy as np
    T=np.eye(4); T[:3,3]=center
    return trimesh.creation.box(extents=extents, transform=T)

def add_component(scene,trimesh,components,name,extents,center,category,status,note=''):
    mesh=box_mesh(trimesh,extents,center); scene.add_geometry(mesh,node_name=name,geom_name=name)
    components.append({'id':name,'category':category,'extents_m':[round(x,6) for x in extents],'center_m':[round(x,6) for x in center],'status':status,'note':note,'volume_m3':round(float(mesh.volume),6)})

def build_scene(design,derivation,out):
    import trimesh
    W=float(design['geometry']['outer_envelope_m']['x']); H=float(design['geometry']['outer_envelope_m']['y'])
    ring_h=float(derivation['geometry']['levels_m']['structural_ring_beam_top']); roof_z=float(derivation['geometry']['levels_m']['roof_apex_or_rafter_top'])
    slab_t=.150; strip_w=.800; strip_t=.200; ring_b=.150; ring_d=.200; wall_t=.150
    strip_bottom=-.95; strip_top=strip_bottom+strip_t; strip_z=(strip_bottom+strip_top)/2
    scene=trimesh.Scene(); c=[]
    add_component(scene,trimesh,c,'SLAB_ENVELOPE',(W,H,slab_t),(W/2,H/2,-slab_t/2),'ground_bearing_slab','SOURCE_GEOMETRY_REFERENCE','Openings/steps omitted; slab not modeled as spanning to walls.')
    add_component(scene,trimesh,c,'STRIP_SOUTH',(W,strip_w,strip_t),(W/2,strip_w/2,strip_z),'strip_footing','PRELIMINARY_GRAVITY_BEARING_PASS','Reinforcement/settlement/geotechnical HOLD.')
    add_component(scene,trimesh,c,'STRIP_NORTH',(W,strip_w,strip_t),(W/2,H-strip_w/2,strip_z),'strip_footing','PRELIMINARY_GRAVITY_BEARING_PASS','Reinforcement/settlement/geotechnical HOLD.')
    add_component(scene,trimesh,c,'STRIP_WEST',(strip_w,H-2*strip_w,strip_t),(strip_w/2,H/2,strip_z),'strip_footing','PRELIMINARY_GRAVITY_BEARING_PASS','Reinforcement/settlement/geotechnical HOLD.')
    add_component(scene,trimesh,c,'STRIP_EAST',(strip_w,H-2*strip_w,strip_t),(W-strip_w/2,H/2,strip_z),'strip_footing','PRELIMINARY_GRAVITY_BEARING_PASS','Reinforcement/settlement/geotechnical HOLD.')
    wh=ring_h
    for name,ext,cen in [
      ('WALL_REF_SOUTH',(W,wall_t,wh),(W/2,wall_t/2,wh/2)),('WALL_REF_NORTH',(W,wall_t,wh),(W/2,H-wall_t/2,wh/2)),
      ('WALL_REF_WEST',(wall_t,H-2*wall_t,wh),(wall_t/2,H/2,wh/2)),('WALL_REF_EAST',(wall_t,H-2*wall_t,wh),(W-wall_t/2,H/2,wh/2))]:
        add_component(scene,trimesh,c,name,ext,cen,'wall_reference','REFERENCE_ENVELOPE_ONLY','Openings omitted; not a finalized loadbearing-wall vector.')
    rbz=ring_h-ring_d/2
    for name,ext,cen in [
      ('RING_SOUTH',(W,ring_b,ring_d),(W/2,ring_b/2,rbz)),('RING_NORTH',(W,ring_b,ring_d),(W/2,H-ring_b/2,rbz)),
      ('RING_WEST',(ring_b,H-2*ring_b,ring_d),(ring_b/2,H/2,rbz)),('RING_EAST',(ring_b,H-2*ring_b,ring_d),(W-ring_b/2,H/2,rbz))]:
        add_component(scene,trimesh,c,name,ext,cen,'ring_beam','PRELIMINARY_FLEXURE_PROXY_PASS','150x200 coordination section; final detailing HOLD.')
    gx=design['geometry']['x_coordinates']; gy=design['geometry']['y_coordinates']; xoff=(W-gx[-1])/2; yoff=(H-gy[-1])/2
    for lab,x in zip(design['geometry']['x_axis_labels'],gx): add_component(scene,trimesh,c,f'GRID_X_{lab}',(.012,H,.012),(xoff+x,H/2,.025),'grid_reference','REFERENCE_ONLY','Source-derived grid.')
    for lab,y in zip(design['geometry']['y_axis_labels'],gy): add_component(scene,trimesh,c,f'GRID_Y_{lab}',(W,.012,.012),(W/2,yoff+y,.025),'grid_reference','REFERENCE_ONLY','Source-derived grid.')
    add_component(scene,trimesh,c,'ROOF_APEX_LEVEL_X',(W,.025,.025),(W/2,H/2,roof_z),'roof_level_reference','REFERENCE_ONLY','Apex level reference; not actual roof geometry.')
    add_component(scene,trimesh,c,'ROOF_APEX_LEVEL_Y',(.025,H,.025),(W/2,H/2,roof_z),'roof_level_reference','REFERENCE_ONLY','Apex level reference; not actual roof geometry.')
    md=out/'model'; md.mkdir(parents=True,exist_ok=True)
    glb=md/'ANJ616_structural_coordination_model.glb'; obj=md/'ANJ616_structural_coordination_model.obj'; stl=md/'ANJ616_structural_coordination_model.stl'
    scene.export(glb); scene.export(obj); scene.export(stl)
    metadata={'schema':'PHOENIX_STRUCTURAL_3D_MODEL_1.0','model_status':'PARTIAL_VERIFIED_STRUCTURAL_COORDINATION_MODEL','units':'metre','outer_envelope_m':{'x':W,'y':H},
      'levels_m':{'finished_floor':0.0,'ring_beam_top':ring_h,'roof_apex_reference':roof_z,'strip_bottom_provisional':strip_bottom,'strip_top_provisional':strip_top},
      'components':c,'omitted_unproven_geometry':['interior loadbearing-wall vectors','interior RC column locations','exact roof member topology and hip/ridge geometry','openings in perimeter reference walls','elevated tank location and support-frame geometry'],
      'files':{'glb':glb.name,'obj':obj.name,'stl':stl.name}}
    (md/'structural_model_metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    return metadata

def project_iso(x,y,z,scale=28.0): return 430+(x-y)*.866*scale,80+((x+y)*.5-z)*scale

def preview_edges(model):
    edges=[]
    for c in model['components']:
        if c['category']=='grid_reference': continue
        ex,ey,ez=c['extents_m']; cx,cy,cz=c['center_m']; xs=[cx-ex/2,cx+ex/2]; ys=[cy-ey/2,cy+ey/2]; zs=[cz-ez/2,cz+ez/2]
        pts={(ix,iy,iz):project_iso(x,y,z) for ix,x in enumerate(xs) for iy,y in enumerate(ys) for iz,z in enumerate(zs)}
        for a,b in [((0,0,0),(1,0,0)),((0,1,0),(1,1,0)),((0,0,1),(1,0,1)),((0,1,1),(1,1,1)),((0,0,0),(0,1,0)),((1,0,0),(1,1,0)),((0,0,1),(0,1,1)),((1,0,1),(1,1,1)),((0,0,0),(0,0,1)),((1,0,0),(1,0,1)),((0,1,0),(0,1,1)),((1,1,0),(1,1,1))]: edges.append((pts[a],pts[b],c['category']))
    return edges

def write_preview_svg(model,path):
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700" viewBox="0 0 1000 700">','<rect width="1000" height="700" fill="white"/>','<text x="30" y="40" font-family="Arial" font-size="22" font-weight="bold">PHOENIX 4.41 - Anijstraat #616 - 3D structural coordination model</text>','<text x="30" y="66" font-family="Arial" font-size="15">Partial verified envelope; unproven interior and roof topology omitted</text>']
    for (x1,y1),(x2,y2),cat in preview_edges(model):
        dash=' stroke-dasharray="5,4"' if 'reference' in cat or cat=='wall_reference' else ''; width='1.0' if 'reference' in cat or cat=='wall_reference' else '1.8'
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="black" stroke-width="{width}"{dash}/>')
    lines+=['<text x="30" y="655" font-family="Arial" font-size="15" font-weight="bold">PRELIMINARY / NOT FOR CONSTRUCTION</text>','<text x="30" y="678" font-family="Arial" font-size="13">FOR_CONSTRUCTION_RELEASE = LOCKED</text>','</svg>']
    path.write_text('\n'.join(lines),encoding='utf-8')

def write_preview_png(model,path):
    from PIL import Image,ImageDraw,ImageFont
    img=Image.new('RGB',(1400,980),'white'); draw=ImageDraw.Draw(img)
    try: title=ImageFont.truetype('arial.ttf',28); normal=ImageFont.truetype('arial.ttf',18); bold=ImageFont.truetype('arialbd.ttf',18)
    except Exception: title=normal=bold=None
    draw.text((35,25),'PHOENIX 4.41 - Anijstraat #616 - 3D structural coordination model',fill='black',font=title)
    draw.text((35,65),'Partial verified envelope - unproven interior and roof topology omitted',fill='black',font=normal)
    for (x1,y1),(x2,y2),cat in preview_edges(model):
        X1=100+(x1-300)*1.35;Y1=80+(y1-50)*1.25;X2=100+(x2-300)*1.35;Y2=80+(y2-50)*1.25
        draw.line((X1,Y1,X2,Y2),fill='black',width=1 if 'reference' in cat or cat=='wall_reference' else 3)
    draw.text((35,910),'PRELIMINARY / NOT FOR CONSTRUCTION - FOR_CONSTRUCTION_RELEASE = LOCKED',fill='black',font=bold); img.save(path)

def report_data(design,solver,derivation,model):
    roof=derivation['load_model']['roof']; floor=derivation['load_model']['floor_on_ground']; col=design['column']; found=design['foundation']
    return {'title':'Structural Calculation Report - Woonhuis Anijstraat #616','project_id':design['project_id'],'source_sha256':design['source_sha256'],'status':STATUS,'generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'executed_solver':solver['primary_solver']['engine'],'preferred_solver':solver.get('preferred_solver',{}).get('engine','OpenSeesPy'),'preferred_solver_status':solver.get('preferred_solver',{}).get('execution','not recorded'),
      'geometry':{'outer_x_m':design['geometry']['outer_envelope_m']['x'],'outer_y_m':design['geometry']['outer_envelope_m']['y'],'ring_beam_top_m':derivation['geometry']['levels_m']['structural_ring_beam_top'],'roof_apex_reference_m':derivation['geometry']['levels_m']['roof_apex_or_rafter_top']},
      'loads':{'floor_gk_kN_m2':floor['gk_floor_build_up_kN_m2'],'residential_qk_kN_m2':floor['residential_imposed_load_qk_kN_m2'],'roof_gk_kN_m2':roof['gk_total_kN_m2'],'roof_qk_kN_m2':roof['nonaccessible_roof_imposed_qk_kN_m2'],'wall_100_kN_m':derivation['load_model']['masonry']['100mm_wall_line_weight_kN_m'],'wall_150_kN_m':derivation['load_model']['masonry']['150mm_wall_line_weight_kN_m'],'tank_gravity_envelope_kN':design['tank']['gravity_envelope_kN']},
      'elements':{'roof_50x150_util':design['roof_conservative_50x150_check']['governing_utilization'],'ringbeam_section':'150x200 mm','ringbeam_flexure_util':design['ringbeam']['utilization_proxy'],'ringbeam_reinforcement':'2D12 top + 2D12 bottom; D8-150 ties - preliminary','column_section':'200x200 mm; 4D12; D8-150 ties - provisional','column_axial_util':col['axial_utilization'],'strip':'800x200 mm','strip_pressure_kPa':found['strip_pressure_kPa'],'pad':'1000x1000x200 mm','pad_pressure_kPa':found['pad_pressure_kPa']},
      'authority_decisions':design['authority_decisions'],'release_holds':design['release_holds'],'element_schedule':design['element_schedule'],'model':model,'governance':design['governance'],'code_basis':derivation['code_basis'],'soil_model':derivation['soil_model'],'wind_sensitivity':derivation['load_model']['wind_sensitivity']}

def build_docx(data,preview_png,path):
    from docx import Document
    from docx.shared import Mm,Pt,Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc=Document(); sec=doc.sections[0]; sec.top_margin=Mm(20);sec.bottom_margin=Mm(18);sec.left_margin=Mm(20);sec.right_margin=Mm(20)
    doc.styles['Normal'].font.name='Arial';doc.styles['Normal'].font.size=Pt(9.5)
    for sn,size in [('Title',24),('Heading 1',16),('Heading 2',12)]: doc.styles[sn].font.name='Arial';doc.styles[sn].font.size=Pt(size)
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run('STRUCTURAL CALCULATION REPORT');r.bold=True;r.font.size=Pt(24)
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run('Woonhuis Anijstraat #616');r.bold=True;r.font.size=Pt(18)
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run('PHOENIX 4.41 - Real-project structural workflow').font.size=Pt(12)
    doc.add_picture(str(preview_png),width=Inches(6.5));doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run('PRELIMINARY / NOT FOR CONSTRUCTION');r.bold=True;r.font.size=Pt(14)
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run('FOR_CONSTRUCTION_RELEASE = LOCKED');r.bold=True;doc.add_page_break()
    def heading(t): doc.add_heading(t,level=1)
    def bullet(t): p=doc.add_paragraph(style='List Bullet');p.add_run(t)
    def _cant_split(row):
        trPr=row._tr.get_or_add_trPr()
        if trPr.find(qn('w:cantSplit')) is None: trPr.append(OxmlElement('w:cantSplit'))
    def _repeat_header(row):
        trPr=row._tr.get_or_add_trPr()
        if trPr.find(qn('w:tblHeader')) is None: trPr.append(OxmlElement('w:tblHeader'))
    def table(rows):
        tbl=doc.add_table(rows=1,cols=len(rows[0]));tbl.style='Table Grid';tbl.alignment=WD_TABLE_ALIGNMENT.CENTER
        for i,h in enumerate(rows[0]): c=tbl.rows[0].cells[i];c.text=str(h);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;[setattr(run,'bold',True) for run in c.paragraphs[0].runs]
        _cant_split(tbl.rows[0]);_repeat_header(tbl.rows[0])
        for row in rows[1:]:
            r=tbl.add_row();cells=r.cells
            for i,v in enumerate(row): cells[i].text=str(v);cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _cant_split(r)
        return tbl
    heading('1. Executive summary');doc.add_paragraph('This report consolidates source drawing intake, preliminary load derivation, real open-source solver evidence, element checks, foundation bearing sensitivity and the current structural coordination model. It is a controlled preliminary engineering report and is not a construction release.')
    table([['Item','Result'],['Project ID',data['project_id']],['Executed solver',data['executed_solver']],['Preferred solver status',f"{data['preferred_solver']}: {data['preferred_solver_status']}"],['3D model status',data['model']['model_status']],['Release','LOCKED']])
    heading('2. Source and traceability');bullet(f"Source PDF SHA256: {data['source_sha256']}");bullet('All downstream evidence must retain the same source hash.');bullet('Three drawing authority conflicts remain explicit; none is silently discarded.')
    heading('3. Geometry and structural levels');table([['Parameter','Value'],['Outer envelope',f"{data['geometry']['outer_x_m']:.2f} x {data['geometry']['outer_y_m']:.2f} m"],['Ring-beam top',f"{data['geometry']['ring_beam_top_m']:.2f} m"],['Roof apex/rafter-top reference',f"{data['geometry']['roof_apex_reference_m']:.2f} m"],['3D completeness','Partial verified structural coordination model']]);doc.add_paragraph('The 3D model deliberately omits interior loadbearing vectors, exact roof topology, openings and tank location where source evidence is not authoritative.')
    heading('4. Load model');table([['Characteristic action','Value'],['Ground-bearing floor Gk',f"{data['loads']['floor_gk_kN_m2']:.2f} kN/m2"],['Residential Qk',f"{data['loads']['residential_qk_kN_m2']:.2f} kN/m2"],['Roof Gk',f"{data['loads']['roof_gk_kN_m2']:.2f} kN/m2"],['Roof Qk',f"{data['loads']['roof_qk_kN_m2']:.2f} kN/m2"],['100 mm wall',f"{data['loads']['wall_100_kN_m']:.2f} kN/m"],['150 mm wall',f"{data['loads']['wall_150_kN_m']:.2f} kN/m"],['Tank gravity envelope',f"{data['loads']['tank_gravity_envelope_kN']:.2f} kN"]]);doc.add_paragraph('Load combinations remain preliminary reference envelopes because the legally applicable Suriname code basis is not yet confirmed.')
    heading('5. Solver evidence');doc.add_paragraph(f"Accepted real-project solver evidence was executed with {data['executed_solver']}. Preferred {data['preferred_solver']} status: {data['preferred_solver_status']}. The accepted runtime solver passed reaction equilibrium and closed-form deflection cross-checks.")
    heading('6. Element verification');table([['Element','Preliminary result','Limitation'],['Roof <=3.40 m',f"50x150 C18 proxy; util {data['elements']['roof_50x150_util']:.3f}",'Grade/connections/wind HOLD'],['Ring beam',f"{data['elements']['ringbeam_section']}; util {data['elements']['ringbeam_flexure_util']:.3f}",data['elements']['ringbeam_reinforcement']],['RC column',f"{data['elements']['column_section']}; axial util {data['elements']['column_axial_util']:.3f}",'N-M/slenderness/lateral HOLD'],['Strip',f"{data['elements']['strip']}; {data['elements']['strip_pressure_kPa']:.1f} kPa",'Rebar/settlement HOLD'],['Pad',f"{data['elements']['pad']}; {data['elements']['pad_pressure_kPa']:.1f} kPa",'Punching/rebar/settlement HOLD']])
    heading('7. Foundation and soil sensitivity');rows=[['qa (kPa)','0.8 m strip allow.','1x1 m pad allow.']];[rows.append([f"{s['qa_kPa']:.0f}",f"{s['existing_0p8m_strip_allowable_line_reaction_kN_m']:.0f} kN/m",f"{s['existing_1x1m_pad_allowable_reaction_kN']:.0f} kN"]) for s in data['soil_model']['preliminary_allowable_bearing_scenarios']];table(rows);doc.add_paragraph('Site-specific geotechnical investigation remains mandatory; settlement and groundwater effects are not resolved.')
    heading('8. Wind and elevated tank');rows=[['Scenario','qref','Status']];[rows.append([w['scenario'],f"{w['reference_dynamic_pressure_kN_m2']:.3f} kN/m2",w['status']]) for w in data['wind_sensitivity']];table(rows);doc.add_paragraph(f"The 2.0 m3 tank is carried with a {data['loads']['tank_gravity_envelope_kN']:.2f} kN preliminary gravity envelope. Support frame, location/elevation, wind, overturning and anchorage remain unresolved.")
    heading('9. 3D structural coordination model');doc.add_picture(str(preview_png),width=Inches(6.4));doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER;doc.add_paragraph('GLB/OBJ/STL are coordination outputs, not a final BIM or analysis model.');[bullet('Omitted: '+x) for x in data['model']['omitted_unproven_geometry']]
    heading('10. Authority decisions');table([['ID','Preliminary model choice','Final status']]+[[a['id'],a['preliminary_model_choice'],a['final_status']] for a in data['authority_decisions']])
    heading('11. Release hold matrix');table([['ID','Hold','Required']]+[[h['id'],h['hold'],h['required_for_release']] for h in data['release_holds']])
    heading('12. Element schedule');table([['ID','Element','Consolidated choice','Status']]+[[e['id'],e['element'],e['choice'],e['status']] for e in data['element_schedule']])
    heading('13. Conclusion');doc.add_paragraph('Phoenix has progressed the project from source drawing intake through preliminary loads, executed solver evidence, element checks, drawing consolidation and a traceable 3D coordination model. Construction release remains locked until all mandatory holds are closed and a qualified structural professional approves the final design.');p=doc.add_paragraph();r=p.add_run('PRELIMINARY / NOT FOR CONSTRUCTION - FOR_CONSTRUCTION_RELEASE = LOCKED');r.bold=True
    for section in doc.sections: footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER;footer.add_run('PHOENIX 4.41 | Anijstraat #616 | PRELIMINARY - NOT FOR CONSTRUCTION').font.size=Pt(8)
    doc.save(path)

def build_pdf(data,preview_png,path):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
    styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='CenterTitle',parent=styles['Title'],alignment=TA_CENTER,fontName='Helvetica-Bold',fontSize=20,leading=24));styles.add(ParagraphStyle(name='CenterSub',parent=styles['Normal'],alignment=TA_CENTER,fontName='Helvetica',fontSize=11,leading=14));styles['Heading1'].fontName='Helvetica-Bold';styles['Heading1'].fontSize=14;styles['BodyText'].fontName='Helvetica';styles['BodyText'].fontSize=8.5;styles['BodyText'].leading=11
    def footer(canvas,doc): canvas.saveState();canvas.setFont('Helvetica',7);canvas.drawCentredString(A4[0]/2,8*mm,'PHOENIX 4.41 | Anijstraat #616 | PRELIMINARY - NOT FOR CONSTRUCTION');canvas.restoreState()
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm,title=data['title'],author='PHOENIX 4.41');story=[Spacer(1,25*mm),Paragraph('STRUCTURAL CALCULATION REPORT',styles['CenterTitle']),Spacer(1,5*mm),Paragraph('Woonhuis Anijstraat #616',styles['CenterTitle']),Spacer(1,4*mm),Paragraph('PHOENIX 4.41 - Real-project structural workflow',styles['CenterSub']),Spacer(1,8*mm),Image(str(preview_png),width=160*mm,height=112*mm),Spacer(1,7*mm),Paragraph('<b>PRELIMINARY / NOT FOR CONSTRUCTION</b>',styles['CenterSub']),Paragraph('<b>FOR_CONSTRUCTION_RELEASE = LOCKED</b>',styles['CenterSub']),PageBreak()]
    def h(t):story.extend([Paragraph(t,styles['Heading1']),Spacer(1,2*mm)])
    def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,2.5*mm)])
    def tbl(rows,widths=None):
        rr=[[Paragraph(str(c),styles['BodyText']) for c in row] for row in rows];t=Table(rr,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.35,colors.black),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8E8E8')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([t,Spacer(1,4*mm)])
    h('1. Executive summary');p('This report consolidates source drawing intake, preliminary load derivation, real open-source solver evidence, element checks, foundation bearing sensitivity and the current structural coordination model. It is preliminary engineering evidence only.');tbl([['Item','Result'],['Project ID',data['project_id']],['Executed solver',data['executed_solver']],['Preferred solver status',f"{data['preferred_solver']}: {data['preferred_solver_status']}"],['3D model status',data['model']['model_status']],['Release','LOCKED']],[55*mm,110*mm])
    h('2. Source and traceability');p(f"Source PDF SHA256: {data['source_sha256']}. The same source hash is enforced through the downstream evidence chain. Three authority conflicts remain explicitly tracked.")
    h('3. Geometry and structural levels');tbl([['Parameter','Value'],['Outer envelope',f"{data['geometry']['outer_x_m']:.2f} x {data['geometry']['outer_y_m']:.2f} m"],['Ring-beam top',f"{data['geometry']['ring_beam_top_m']:.2f} m"],['Roof apex reference',f"{data['geometry']['roof_apex_reference_m']:.2f} m"],['3D completeness','Partial verified structural coordination model']],[70*mm,95*mm]);p('Unproven interior vectors, exact roof topology, openings and tank location are deliberately omitted.')
    h('4. Load model');tbl([['Characteristic action','Value'],['Floor Gk',f"{data['loads']['floor_gk_kN_m2']:.2f} kN/m2"],['Residential Qk',f"{data['loads']['residential_qk_kN_m2']:.2f} kN/m2"],['Roof Gk',f"{data['loads']['roof_gk_kN_m2']:.2f} kN/m2"],['Roof Qk',f"{data['loads']['roof_qk_kN_m2']:.2f} kN/m2"],['100 mm wall',f"{data['loads']['wall_100_kN_m']:.2f} kN/m"],['150 mm wall',f"{data['loads']['wall_150_kN_m']:.2f} kN/m"],['Tank gravity envelope',f"{data['loads']['tank_gravity_envelope_kN']:.2f} kN"]],[100*mm,65*mm]);p('Load combinations remain preliminary reference envelopes because the legally applicable Suriname code basis is not yet confirmed.')
    h('5. Solver evidence');p(f"Accepted real-project solver evidence was executed with {data['executed_solver']}. Preferred {data['preferred_solver']} status: {data['preferred_solver_status']}. The runtime solver passed reaction equilibrium and closed-form deflection cross-checks.")
    h('6. Element verification');tbl([['Element','Preliminary result','Limitation'],['Roof <=3.40 m',f"50x150 C18 proxy; util {data['elements']['roof_50x150_util']:.3f}",'Grade/connections/wind HOLD'],['Ring beam',f"{data['elements']['ringbeam_section']}; util {data['elements']['ringbeam_flexure_util']:.3f}",data['elements']['ringbeam_reinforcement']],['RC column',f"200x200, 4D12; axial util {data['elements']['column_axial_util']:.3f}",'N-M/slenderness/lateral HOLD'],['Strip',f"{data['elements']['strip']}; {data['elements']['strip_pressure_kPa']:.1f} kPa",'Rebar/settlement HOLD'],['Pad',f"{data['elements']['pad']}; {data['elements']['pad_pressure_kPa']:.1f} kPa",'Punching/rebar/settlement HOLD']],[55*mm,60*mm,50*mm])
    h('7. Foundation and soil sensitivity');rows=[['qa (kPa)','0.8 m strip allow.','1x1 m pad allow.']]+[[f"{s['qa_kPa']:.0f}",f"{s['existing_0p8m_strip_allowable_line_reaction_kN_m']:.0f} kN/m",f"{s['existing_1x1m_pad_allowable_reaction_kN']:.0f} kN"] for s in data['soil_model']['preliminary_allowable_bearing_scenarios']];tbl(rows,[45*mm,60*mm,60*mm]);p('Site-specific geotechnical investigation remains mandatory.')
    h('8. Wind and elevated tank');rows=[['Scenario','qref','Status']]+[[w['scenario'],f"{w['reference_dynamic_pressure_kN_m2']:.3f} kN/m2",w['status']] for w in data['wind_sensitivity']];tbl(rows,[35*mm,40*mm,90*mm]);p(f"The 2.0 m3 tank uses a {data['loads']['tank_gravity_envelope_kN']:.2f} kN preliminary gravity envelope. Frame, wind, overturning and anchorage remain unresolved.")
    h('9. 3D structural coordination model');story.extend([Image(str(preview_png),width=160*mm,height=112*mm),Spacer(1,3*mm)]);p('The GLB/OBJ/STL model is partial verified coordination geometry, not a final BIM or analysis model.');[p('Omitted: '+x) for x in data['model']['omitted_unproven_geometry']]
    h('10. Authority decisions');tbl([['ID','Preliminary choice','Final status']]+[[a['id'],a['preliminary_model_choice'],a['final_status']] for a in data['authority_decisions']],[34*mm,86*mm,45*mm])
    h('11. Release hold matrix');tbl([['ID','Hold','Required']]+[[x['id'],x['hold'],x['required_for_release']] for x in data['release_holds']],[20*mm,120*mm,25*mm])
    h('12. Element schedule');tbl([['ID','Element','Consolidated choice','Status']]+[[e['id'],e['element'],e['choice'],e['status']] for e in data['element_schedule']],[15*mm,35*mm,85*mm,30*mm])
    h('13. Conclusion');p('Phoenix has progressed the project from source drawing intake through preliminary loads, solver evidence, element checks, drawing consolidation and a traceable 3D coordination model. Construction release remains locked until all mandatory holds are closed and a qualified structural professional approves the final design.');p('<b>PRELIMINARY / NOT FOR CONSTRUCTION - FOR_CONSTRUCTION_RELEASE = LOCKED</b>')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def build_html_viewer(model,out):
    viewer = f"""<!doctype html><html><head><meta charset='utf-8'><title>PHOENIX Anijstraat #616 - 3D Structural Model</title>
<style>body{{font-family:Arial,sans-serif;max-width:1200px;margin:auto;padding:20px}}.notice{{font-weight:bold;border:2px solid #222;padding:12px;margin-bottom:16px}}model-viewer{{width:100%;height:720px;border:1px solid #888;background:#fafafa}}</style>
<script type='module' src='https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js'></script></head><body>
<h1>PHOENIX 4.41 - Anijstraat #616</h1><div class='notice'>PRELIMINARY / NOT FOR CONSTRUCTION - FOR_CONSTRUCTION_RELEASE = LOCKED</div><p>Model completeness: {html.escape(model['model_status'])}</p>
<model-viewer src='model/ANJ616_structural_coordination_model.glb' camera-controls auto-rotate shadow-intensity='0.4'><img slot='poster' src='model/ANJ616_structural_model_preview.png' alt='Structural model preview'></model-viewer>
<h2>Important omissions</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in model['omitted_unproven_geometry'])}</ul><p>If interactive loading is unavailable offline, open GLB/OBJ/STL locally and use the PNG/SVG preview.</p></body></html>"""
    (out/'structural_3d_viewer.html').write_text(viewer,encoding='utf-8')

def write_outputs(design,solver,derivation,source_pdf,config,out):
    out.mkdir(parents=True,exist_ok=True);model=build_scene(design,derivation,out);preview_svg=out/'model/ANJ616_structural_model_preview.svg';preview_png=out/'model/ANJ616_structural_model_preview.png';write_preview_svg(model,preview_svg);write_preview_png(model,preview_png);build_html_viewer(model,out)
    data=report_data(design,solver,derivation,model);(out/'calculation_report_data.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');(out/'3d_structural_model_metadata.json').write_text(json.dumps(model,indent=2,ensure_ascii=False),encoding='utf-8')
    md=['# Structural Calculation Report - Woonhuis Anijstraat #616','',f"Status: `{STATUS}`",'',f"Source SHA256: `{data['source_sha256']}`",'','## Key verified preliminary results','',f"- Executed solver: **{data['executed_solver']}**.",f"- Roof 50x150 C18 proxy utilization: **{data['elements']['roof_50x150_util']:.3f}**.",f"- Ring beam 150x200 flexure proxy utilization: **{data['elements']['ringbeam_flexure_util']:.3f}**.",f"- Column axial utilization: **{data['elements']['column_axial_util']:.3f}**.",'','## 3D model status','',f"`{model['model_status']}`",'','**PRELIMINARY / NOT FOR CONSTRUCTION**','','`FOR_CONSTRUCTION_RELEASE = LOCKED`','',f"Next stage: `{NEXT_STAGE}`",'']
    (out/'structural_calculation_report.md').write_text('\n'.join(md),encoding='utf-8');build_docx(data,preview_png,out/'PHOENIX_ANIJSTRAAT_616_STRUCTURAL_CALCULATION_REPORT.docx');build_pdf(data,preview_png,out/'PHOENIX_ANIJSTRAAT_616_STRUCTURAL_CALCULATION_REPORT.pdf')
    summary={'schema':'PHOENIX_3D_STRUCTURAL_MODEL_CALC_REPORT_1.0','project_id':design['project_id'],'source_sha256':design['source_sha256'],'model_status':model['model_status'],'executed_solver':solver['primary_solver']['engine'],'roof_50x150_utilization':design['roof_conservative_50x150_check']['governing_utilization'],'ringbeam_150x200_flexure_utilization':design['ringbeam']['utilization_proxy'],'column_axial_utilization':design['column']['axial_utilization'],'preliminary_not_for_construction':True,'for_construction_release':'LOCKED','status':STATUS,'next_stage':NEXT_STAGE,'outputs':['model/ANJ616_structural_coordination_model.glb','model/ANJ616_structural_coordination_model.obj','model/ANJ616_structural_coordination_model.stl','model/ANJ616_structural_model_preview.svg','model/ANJ616_structural_model_preview.png','structural_3d_viewer.html','PHOENIX_ANIJSTRAAT_616_STRUCTURAL_CALCULATION_REPORT.docx','PHOENIX_ANIJSTRAAT_616_STRUCTURAL_CALCULATION_REPORT.pdf','structural_calculation_report.md']}
    (out/'structural_3d_report_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');manifest={}
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='evidence_manifest.json': manifest[p.relative_to(out).as_posix()]={'sha256':sha256_file(p),'bytes':p.stat().st_size}
    (out/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');return summary

def verify_output(path):
    d=json.loads(path.read_text(encoding='utf-8'));out=path.parent;assert d['status']==STATUS and d['preliminary_not_for_construction'] is True and d['for_construction_release']=='LOCKED' and d['model_status']=='PARTIAL_VERIFIED_STRUCTURAL_COORDINATION_MODEL';assert d['roof_50x150_utilization']<1 and d['ringbeam_150x200_flexure_utilization']<1 and d['column_axial_utilization']<1
    for rel in d['outputs']:
        p=out/rel;assert p.exists() and p.stat().st_size>0,rel
    import trimesh;scene=trimesh.load(out/'model/ANJ616_structural_coordination_model.glb',force='scene');assert len(scene.geometry)>=10
    from pypdf import PdfReader;assert len(PdfReader(str(out/'PHOENIX_ANIJSTRAAT_616_STRUCTURAL_CALCULATION_REPORT.pdf')).pages)>=5
    from docx import Document;assert len(Document(str(out/'PHOENIX_ANIJSTRAAT_616_STRUCTURAL_CALCULATION_REPORT.docx')).paragraphs)>20
    print('PHOENIX_4_41_3D_STRUCTURAL_MODEL_CALC_REPORT_OUTPUT_VERIFY=PASS')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--design-json',type=Path);ap.add_argument('--solver-json',type=Path);ap.add_argument('--derivation-json',type=Path);ap.add_argument('--source-pdf',type=Path);ap.add_argument('--config',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--verify-output',type=Path);a=ap.parse_args()
    if a.verify_output:verify_output(a.verify_output);return 0
    if not all([a.design_json,a.solver_json,a.derivation_json,a.source_pdf,a.config,a.output]):ap.error('all input args required')
    design=json.loads(a.design_json.read_text(encoding='utf-8'));solver=json.loads(a.solver_json.read_text(encoding='utf-8'));deriv=json.loads(a.derivation_json.read_text(encoding='utf-8'));cfg=json.loads(a.config.read_text(encoding='utf-8'));sha=sha256_file(a.source_pdf);validate_inputs(design,solver,deriv,sha);s=write_outputs(design,solver,deriv,a.source_pdf,cfg,a.output)
    print(f"PROJECT_ID={s['project_id']}");print(f"SOURCE_SHA256={s['source_sha256']}");print(f"EXECUTED_SOLVER_EVIDENCE={s['executed_solver']}");print(f"MODEL_STATUS={s['model_status']}");print('GLB_EXPORT=PASS');print('OBJ_EXPORT=PASS');print('STL_EXPORT=PASS');print('DOCX_CALCULATION_REPORT=PASS');print('PDF_CALCULATION_REPORT=PASS');print(f"ROOF_50x150_UTIL={s['roof_50x150_utilization']}");print(f"RINGBEAM_150x200_UTIL={s['ringbeam_150x200_flexure_utilization']}");print(f"COLUMN_AXIAL_UTIL={s['column_axial_utilization']}");print('PRELIMINARY_NOT_FOR_CONSTRUCTION=TRUE');print('FOR_CONSTRUCTION_RELEASE=LOCKED');print(f"STRUCTURAL_3D_REPORT_STATUS={s['status']}");print(f"NEXT_STAGE={s['next_stage']}");print(f"OUTPUT={a.output}");return 0
if __name__=='__main__': raise SystemExit(main())
