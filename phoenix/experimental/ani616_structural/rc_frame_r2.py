import csv,json,hashlib,sys,math,datetime,zipfile
from pathlib import Path
from xml.sax.saxutils import escape

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
 with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(p,items):
 if not items:return
 with open(p,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=items[0].keys());w.writeheader();w.writerows(items)
def main(root,out,repo):
 root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 names=['RC_FRAME_EXECUTION_EVIDENCE.json','FRAME_REACTIONS.csv','BEAM_SCHEDULE.csv','COLUMN_SCHEDULE.csv']
 for n in names:
  if not (root/n).is_file():raise RuntimeError('MISSING_R1:'+str(root/n))
 ev=json.loads((root/names[0]).read_text(encoding='utf-8-sig'))
 if ev.get('project')!='ANIJSTRAAT_616' or ev.get('models',{}).get('A')!='PASS_LINEAR_SOLVER_GRAVITY_ONLY':raise RuntimeError('R1_SOURCE_NOT_QUALIFIED')
 bs=[x for x in rows(root/names[2]) if x['variant']=='A'];cs=[x for x in rows(root/names[3]) if x['variant']=='A'];rs=[x for x in rows(root/names[1]) if x['variant']=='A']
 if not bs or not cs or len(rs)!=2:raise RuntimeError('R1_INCOMPLETE')
 # Previously calculated demand only; capacity checks are explicit screening assumptions, NOT formal NEN design.
 # Check physical beam demand and create working schedule. fyd = 500/1.15, fcd = 25/1.5 N/mm2 are candidate hypotheses only.
 beam=[]
 for x in bs:
  M=max(abs(float(x['M_y_kNm'])),abs(float(x['M_z_kNm'])));V=abs(float(x['V_y_kN']))
  depth=600 if str(x['section_proposal']).startswith('300x600') else 500
  width=300 if depth==600 else 250
  d=depth-60;z=.9*d
  As=M*1e6/(z*(500/1.15)) if M>0 else 0
  v=V*1000/(width*d)
  beam.append({'member':x['member'],'level':x['level'],'span_m':x['span_m'],'section_proposal':x['section_proposal'],'Mmax_kNm':round(M,3),'V_kN':round(V,3),'deflection_sls_mm':x['deflection_sls_mm'],'As_flexural_screen_mm2':round(As,0),'v_average_screen_MPa':round(v,3),'note':'ASSUMED_C25_F500_D60_NO_RC_CODE_CHECK_NO_MINIMUM_REINFORCEMENT'})
 col=[]
 for x in cs:
  n=abs(float(x['axial_envelope_kN']));area=350**2
  sigma=n*1000/area
  col.append({'member':x['member'],'level':x['level'],'section_proposal':x['section_proposal'],'Nmax_kN':round(n,3),'gross_axial_stress_screen_MPa':round(sigma,3),'note':'AXIAL_ONLY_NO_MOMENT_INTERACTION_SECOND_ORDER_OR_BUCKLING'})
 writecsv(out/'R2_VARIANT_A_BEAM_SCREEN.csv',beam);writecsv(out/'R2_VARIANT_A_COLUMN_SCREEN.csv',col)
 maxm=max(beam,key=lambda x:x['Mmax_kNm']);maxv=max(beam,key=lambda x:x['V_kN']);maxdef=max(beam,key=lambda x:float(x['deflection_sls_mm']));maxcol=max(col,key=lambda x:x['Nmax_kN'])
 # Read CAD source candidate metadata, but do not create registration claims.
 cad_candidates=[]
 search_roots=[root,root.parent,Path(repo)/'outputs',Path(repo)/'BIB'/'ANIJ616']
 for d in search_roots:
  if not d.exists():continue
  if d==root:
   for name in ['R9_GEOMETRY_OBJECTS.json','R10_6_OBJECT_PROPOSALS.csv']:
    p=d/name
    if p.is_file():cad_candidates.append({'file':str(p),'sha256':sha(p)})
 # E.g. DXF wall proposals cannot prove local coordinate transform to frame plan.
 cad_status='HOLD_NO_VERIFIED_CAD_TO_FRAME_TRANSFORM'
 # Grounded schematic conceptual plan, with axes dimensioned to provisional 18.1x13.7m frame. 4x4 nodes.
 W,H=1050,850; ox,oy=135,130;sx=760/18.1;sy=550/13.7
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="850" viewBox="0 0 1050 850">', '<rect width="1050" height="850" fill="white"/>','<text x="70" y="55" font-family="Arial" font-size="25" font-weight="bold">ANIJSTRAAT 616 — RC FRAME VARIANT A</text>','<text x="70" y="85" font-family="Arial" font-size="15" fill="#a33">SCHEMATISCH / ONBEVESTIGDE INPASSING / NIET VOOR UITVOERING</text>']
 for i in range(4):
  x=ox+(18.1*i/3)*sx;y=oy+(13.7*i/3)*sy
  svg.append(f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{oy+13.7*sy}" stroke="#708699" stroke-width="3"/>')
  svg.append(f'<line x1="{ox}" y1="{y}" x2="{ox+18.1*sx}" y2="{y}" stroke="#708699" stroke-width="3"/>')
  svg.append(f'<text x="{x-5}" y="{oy-25}" font-family="Arial" font-size="19">{i+1}</text><text x="{ox-42}" y="{y+7}" font-family="Arial" font-size="19">{chr(65+i)}</text>')
  for j in range(4):
   yy=oy+(13.7*j/3)*sy
   svg.append(f'<rect x="{x-9}" y="{yy-9}" width="18" height="18" fill="#384e62"/>')
 svg.append('<text x="135" y="750" font-family="Arial" font-size="17">Raster: 18,10 × 13,70 m | Kolomvoorstel: 350 × 350 mm</text>')
 svg.append('<text x="135" y="784" font-family="Arial" font-size="16">16 punten per laag. Geen CAD-registratie, fundering of windstabiliteit geverifieerd.</text></svg>')
 (out/'R2_VARIANT_A_SCHEMATIC_PLAN.svg').write_text('\n'.join(svg),encoding='utf-8')
 checks={'project':'ANIJSTRAAT_616','status':'PASS_R1_RESULT_REVIEW_ONLY','reused_r1':{n:sha(root/n) for n in names},'actual_solver_execution_this_stage':False,'r1_variant_a':{'beam_rows':len(bs),'column_rows':len(cs),'equilibrium':rs,'max_bending':maxm,'max_shear':maxv,'max_deflection':maxdef,'max_column_axial':maxcol},'preliminary_member_screening':'CALCULATED_ASSUMPTION_BASED_NOT_CAPACITY_VERIFICATION','cad_fit':cad_status,'cad_input_candidates':cad_candidates,'geotechnics':'HOLD','wind_stability':'HOLD','reinforcement_design':'HOLD','foundation':'HOLD','architectural_fit':'HOLD','release':'LOCKED','repository':'READ_ONLY_EXPECTED'}
 (out/'R2_EXECUTION_EVIDENCE.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False),encoding='utf-8')
 report=f'''# Anijstraat 616 — Voorlopig betonframe R2 — variant A\n\n**NIET VOOR UITVOERING — CONCEPT — PROFESSIONELE TOETS VEREIST**\n\n## Herkomst\nBerekende R1 PyNiteFEA-gegevens worden als *vraag* hergebruikt; in deze R2-run is geen nieuwe solverberekening uitgevoerd. Project: Anijstraat 616.\n\n## Variant A\n- {len(bs)} balkregels en {len(cs)} kolomregels in de R1-variant-A-resultaten.\n- Maatgevend absoluut balkmoment: **{maxm['Mmax_kNm']} kNm**, lid `{maxm['member']}`.\n- Grootste absolute dwarskracht: **{maxv['V_kN']} kN**, lid `{maxv['member']}`.\n- Grootste gerapporteerde SLS-doorbuiging: **{maxdef['deflection_sls_mm']} mm**, lid `{maxdef['member']}`.\n- Grootste kolomnormaalkracht: **{maxcol['Nmax_kN']} kN**, lid `{maxcol['member']}`.\n\n## Screening — geen normatieve betonberekening\nBij aangenomen C25-beton, fyk=500 MPa, veiligheidsfactor staal 1,15, effectieve hoogte h-60 mm en z=0,9d is de formule As=MEd/(z fyd) gebruikt voor een **indicatieve buigwapeningsvraag**. Hiermee is niet gecontroleerd: as-min/max, verankering, scheurvorming, dwarskrachtbeugels, knik, kolominteractie, brandwerendheid, milieuklasse, seismiek of 2e orde. De eerdere illustratieve ULS-lastcombinatie is niet formeel vastgesteld.\n\n## Architectonische inpassing\n**{cad_status}**. Het raster in de SVG is een ontwerpvoorstel zonder bewezen positie t.o.v. het VO. Er worden geen botsingen met deuren/ramen als PASS geclaimd.\n\n## Openstaande bouwbeslissingen\nBevestiging dragend frame en vloerwerking, maatvoering/cad-transformatie, tankplaatsing, windstabiliteit, lokale normbasis, materiaal- en wapeningseisen, geotechniek draagkracht/zetting en professionele beoordeling.\n\n**RELEASE=LOCKED**\n'''
 (out/'PRELIMINARY_RC_FRAME_R2_REPORT.md').write_text(report,encoding='utf-8')
 (out/'R2_BLOCKERS.txt').write_text('CAD-registratie en conflictcontrole: HOLD\nBetoncapaciteit inclusief ULS/SLS en wapening: HOLD\nWind en stabiliteit: HOLD\nFundering en bodem: HOLD\nBrongekoppelde definitieve tekeningen: HOLD\nProfessionele vrijgave: LOCKED\n',encoding='utf-8')
 with zipfile.ZipFile(out/'UPLOAD_THIS_REVIEW.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in ['R2_EXECUTION_EVIDENCE.json','R2_VARIANT_A_BEAM_SCREEN.csv','R2_VARIANT_A_COLUMN_SCREEN.csv','PRELIMINARY_RC_FRAME_R2_REPORT.md'] : z.write(out/name,name)
 print('RC_R2_GATES='+json.dumps({'r1':'PASS_SOURCE','variant_a':'PASS_DEMAND_REVIEW','member_design':'HOLD_PRELIM_SCREEN_ONLY','cad_fit':cad_status,'release':'LOCKED'}))
 print('RC_R2_COUNTS='+json.dumps({'beam_rows':len(beam),'column_rows':len(col),'drawings':1}))
 print('OUTPUT='+str(out));print('UPLOAD='+str(out/'UPLOAD_THIS_REVIEW.zip'))
if __name__=='__main__':main(*sys.argv[1:4])
