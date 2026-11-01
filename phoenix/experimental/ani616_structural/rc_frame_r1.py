#!/usr/bin/env python3
"""Independent provisional RC FRAME grid run, read-only Phoenix repository.
Uses the existing PyNiteFEA environment and prior Phoenix loads as UNVERIFIED inputs.
Does NOT impersonate Phoenix's structural design/verification engine.
"""
import argparse,csv,hashlib,json,math,os,sys,traceback
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v): Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def file_csv(path,heads,rows):
 with open(path,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=heads);w.writeheader();w.writerows(rows)
def make_svg(out,xs,zs,tag,variant,beams):
 sx=720/max(xs[-1],1);sz=480/max(zs[-1],1)
 t=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="680" viewBox="0 0 1000 680">','<rect width="1000" height="680" fill="#fff"/>',f'<text x="40" y="42" font-family="Arial" font-size="23">ANIJSTRAAT 616 | {escape(tag)} | {variant}</text>','<text x="40" y="67" font-family="Arial" font-size="14" fill="#b04030">VOORLOPIG - SCHEMATISCH - NIET MAATVAST OP CAD - GEEN UITVOERINGSTEKENING</text>']
 def pt(x,z):return (120+x*sx,560-z*sz)
 for i,x in enumerate(xs):
  xx,_=pt(x,0); t.append(f'<line x1="{xx:.1f}" y1="110" x2="{xx:.1f}" y2="595" stroke="#999" stroke-dasharray="5 5"/>');t.append(f'<text x="{xx:.1f}" y="615" text-anchor="middle" font-size="15">{chr(65+i)}</text>')
 for j,z in enumerate(zs):
  _,yy=pt(0,z);t.append(f'<line x1="105" y1="{yy:.1f}" x2="860" y2="{yy:.1f}" stroke="#999" stroke-dasharray="5 5"/>');t.append(f'<text x="85" y="{yy+5:.1f}" text-anchor="middle" font-size="15">{j+1}</text>')
 for x in xs:
  for j in range(len(zs)-1):
   a=pt(x,zs[j]);b=pt(x,zs[j+1]);t.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#276a9d" stroke-width="6"/>')
 for z in zs:
  for i in range(len(xs)-1):
   a=pt(xs[i],z);b=pt(xs[i+1],z);t.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#276a9d" stroke-width="6"/>')
 for i,x in enumerate(xs):
  for j,z in enumerate(zs):
   px,py=pt(x,z);t.append(f'<rect x="{px-6:.1f}" y="{py-6:.1f}" width="12" height="12" fill="#b04030"/>')
 t.extend(['<text x="40" y="648" font-size="13">Blauw: voorgestelde balken. Rood: voorgestelde kolommen. Stippellijnen: ontwerpstramien.</text>','</svg>']);Path(out).write_text('\n'.join(t),encoding='utf-8')

def run(args):
 from Pynite import FEModel3D
 import Pynite
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 deriv=Path(args.derivation);assert deriv.is_file();data=json.loads(deriv.read_text(encoding='utf-8-sig'))
 # Source identity is verified against user-approved original drawing; derived model is NOT independently validated RC input.
 text=json.dumps(data,ensure_ascii=False).lower()
 original='1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0'
 if original not in text: raise ValueError('HOLD: expected original Anijstraat PDF SHA not present in supplied derivation JSON')
 variants={'A':([0,6.033333,12.066667,18.1],[0,4.566667,9.133333,13.7]),'B':([0,4.525,9.05,13.575,18.1],[0,6.85,13.7]),'C':([0,9.05,18.1],[0,3.425,6.85,10.275,13.7])}
 # 2-storey conceptual model, height to be reviewed; Phoenix 3430mm refers to ceiling, not accepted as structural interstorey height.
 E=28e6 # kN/m2 illustrative concrete stiffness
 nu=0.2;G=E/(2*(1+nu));rho=25 # kN/m3
 floors=[0,3.5,7.0] # illustrative: not measured from CAD
 loadcases={'D':'Gk floor/roof + beam self-weight + perimeter infill','L':'Qk floor + indicative roof'}
 results=[];all_beams=[];all_cols=[];gates={}
 for var,(xs,zs) in variants.items():
  m=FEModel3D();m.add_material('RC_PROVISIONAL',E,G,nu,rho)
  sections={'COLUMN_350x350':(.35,.35),'BEAM_300x600':(.30,.60),'ROOF_BEAM_250x500':(.25,.50)}
  for sn,(b,h) in sections.items():m.add_section(sn,b*h,b*h**3/12,h*b**3/12,(b*h*(min(b,h)**2))/3)
  names={};members={}; applied={'D':0.0,'L':0.0}
  for lev,y in enumerate(floors):
   for i,x in enumerate(xs):
    for j,z in enumerate(zs):
     n=f'V{var}_N{lev}_{i}_{j}';names[(lev,i,j)]=n;m.add_node(n,x,y,z)
     if lev==0:m.def_support(n,True,True,True,True,True,True)
  for lev in (1,2):
   for i,x in enumerate(xs):
    for j,z in enumerate(zs):
     name=f'{var}_C{lev}_{i}_{j}';m.add_member(name,names[(lev-1,i,j)],names[(lev,i,j)],'RC_PROVISIONAL','COLUMN_350x350');members[name]=('column',lev,x,z,None)
   # beams along x at each z, floor/roof tributary width in z, half area borne in each principal direction
   for j,z in enumerate(zs):
    trib=((zs[j]-zs[j-1] if j>0 else 0)+(zs[j+1]-zs[j] if j+1<len(zs) else 0))/2
    for i in range(len(xs)-1):
     name=f'{var}_BX{lev}_{i}_{j}';length=xs[i+1]-xs[i];m.add_member(name,names[(lev,i,j)],names[(lev,i+1,j)],'RC_PROVISIONAL','BEAM_300x600' if lev==1 else 'ROOF_BEAM_250x500');members[name]=('beam',lev,length,'X',trib)
     g=(4.77 if lev==1 else .55)*trib/2 + (0.30*.60 if lev==1 else .25*.50)*25
     if j in (0,len(zs)-1):g+=6.96 # assumed 100mm exterior perimeter infill at this level, not structurally bracing
     q=(2.0 if lev==1 else .4)*trib/2
     m.add_member_dist_load(name,'Fy',-g,-g,case='D');m.add_member_dist_load(name,'Fy',-q,-q,case='L');applied['D']+=g*length;applied['L']+=q*length
   # beams along z, tributary in x
   for i,x in enumerate(xs):
    trib=((xs[i]-xs[i-1] if i>0 else 0)+(xs[i+1]-xs[i] if i+1<len(xs) else 0))/2
    for j in range(len(zs)-1):
     name=f'{var}_BZ{lev}_{i}_{j}';length=zs[j+1]-zs[j];m.add_member(name,names[(lev,i,j)],names[(lev,i,j+1)],'RC_PROVISIONAL','BEAM_300x600' if lev==1 else 'ROOF_BEAM_250x500');members[name]=('beam',lev,length,'Z',trib)
     g=(4.77 if lev==1 else .55)*trib/2 + (0.30*.60 if lev==1 else .25*.50)*25
     if i in (0,len(xs)-1):g+=6.96
     q=(2.0 if lev==1 else .4)*trib/2
     m.add_member_dist_load(name,'Fy',-g,-g,case='D');m.add_member_dist_load(name,'Fy',-q,-q,case='L');applied['D']+=g*length;applied['L']+=q*length
  m.add_load_combo('SLS_D_PLUS_L',{'D':1,'L':1});m.add_load_combo('ILLUSTRATIVE_ULS',{'D':1.35,'L':1.5})
  # No approved local code basis: ULS combination is illustrative only
  m.analyze_linear(log=False,check_stability=True)
  base=[m.nodes[names[(0,i,j)]] for i in range(len(xs)) for j in range(len(zs))]
  for combo in ('SLS_D_PLUS_L','ILLUSTRATIVE_ULS'):
   reaction=sum(n.RxnFY[combo] for n in base)
   expected=applied['D']*(1 if combo.startswith('SLS') else 1.35)+applied['L']*(1 if combo.startswith('SLS') else 1.5)
   relative=abs(reaction-expected)/max(1,abs(expected))
   if relative>1e-4:raise ValueError(f'FAIL EQUILIBRIUM {var}/{combo} reactions={reaction} input={expected}')
   results.append({'variant':var,'combo':combo,'applied_kN':round(expected,3),'base_reaction_kN':round(reaction,3),'imbalance_pct':round(relative*100,5),'base_count':len(base),'solver':'PyNiteFEA'})
  for name,(kind,lev,a,b,trib) in members.items():
   mem=m.members[name]
   if kind=='beam':
    try:
     mz=max(abs(mem.max_moment('Mz','ILLUSTRATIVE_ULS')),abs(mem.min_moment('Mz','ILLUSTRATIVE_ULS')))
     my=max(abs(mem.max_moment('My','ILLUSTRATIVE_ULS')),abs(mem.min_moment('My','ILLUSTRATIVE_ULS')))
     v=max(abs(mem.max_shear('Fy','ILLUSTRATIVE_ULS')),abs(mem.min_shear('Fy','ILLUSTRATIVE_ULS')))
     df=max(abs(mem.max_deflection('dy','SLS_D_PLUS_L')),abs(mem.min_deflection('dy','SLS_D_PLUS_L')))*1000
     all_beams.append({'variant':var,'member':name,'level':lev,'span_m':round(a,3),'M_y_kNm':round(my,3),'M_z_kNm':round(mz,3),'V_y_kN':round(v,3),'deflection_sls_mm':round(df,3),'section_proposal':'300x600 mm' if lev==1 else '250x500 mm','status':'FOR_REVIEW_NO_RC_CAPACITY_CHECK'})
    except Exception as e:raise RuntimeError(f'Beam extraction {name}: {e}')
   else:
    try:
     ax=max(abs(mem.max_axial('ILLUSTRATIVE_ULS')),abs(mem.min_axial('ILLUSTRATIVE_ULS')))
     all_cols.append({'variant':var,'member':name,'level':lev,'axial_envelope_kN':round(ax,3),'section_proposal':'350x350 mm','status':'FOR_REVIEW_NO_INTERACTION_BUCKLING_CHECK'})
    except Exception as e:raise RuntimeError(f'Column extraction {name}: {e}')
  make_svg(out/f'{var}_FRAME_FLOOR.svg',xs,zs,'VERDIEPINGSBALKEN / KOLOMMEN',var,members)
  make_svg(out/f'{var}_FRAME_ROOF.svg',xs,zs,'DAKBALKEN / KOLOMMEN',var,members)
  gates[var]='PASS_LINEAR_SOLVER_GRAVITY_ONLY'
 file_csv(out/'FRAME_REACTIONS.csv',list(results[0]),results)
 file_csv(out/'BEAM_SCHEDULE.csv',list(all_beams[0]),all_beams)
 file_csv(out/'COLUMN_SCHEDULE.csv',list(all_cols[0]),all_cols)
 proven={'project':'ANIJSTRAAT_616','status':'PASS_PRELIMINARY_GRAVITY_FRAME_MODEL_NOT_ENGINEERING_APPROVAL','pdf_expected_sha256':original,'derivation_json_sha256':sha(deriv),'python':sys.executable,'pynite_version':'PyNiteFEA 3.2.1 environment expected','models':gates,'results':results,'assumptions':{'grid':'DESIGN_PROPOSALS_NOT_REGISTERED_TO_CAD','storey_heights_m':floors,'frame':'RC moment frame intended; lateral forces not applied','nonbearing_infill':'6.96 kN/m applied to exterior beams at both occupied levels, load-bearing strength excluded','floor_Gk_kN_m2':4.77,'roof_Gk_kN_m2':0.55,'floor_Qk_kN_m2':2.0,'roof_Qk_kN_m2':0.4,'concrete_E_kN_m2':E,'foundation':'fixed supports, not real soil','tank':'NOT_POSITIONED_OR_APPLIED','wind':'NOT_MODELED','seismic':'NOT_MODELED','member_design':'NO_REINFORCEMENT, PUNCHING, CRACKING, COLUMN INTERACTION, SHEAR OR STABILITY VERIFICATION'},'release':'LOCKED'}
 dump(out/'RC_FRAME_EXECUTION_EVIDENCE.json',proven)
 blockers=['1. Exacte CAD-getoetste posities/overspanningen/openingen en peilen','2. Constructieve vloertype, dikte, eigengewicht en echte verdiepingshoogte','3. Wind, stabiliteit, schijfwerking en tweede orde','4. Lokale code/ULS/SLS, materiaalsterkte, dekking en wapening','5. Tankpositie en belasting; overige geconcentreerde lasten','6. Bodemonderzoek/draagkracht/zetting en fundering zonder gefixeerde inklemming','7. Controle kolominteractie, dwarskracht, scheurwijdte, doorbuiging en verbindingen','8. Gekwalificeerde constructeur, vergunning/uitvoeringsvrijgave']
 (out/'BLOCKERS_FOR_RELEASE.txt').write_text('\n'.join(blockers)+'\n',encoding='utf-8')
 lines=['# ANIJSTRAAT 616 — VOORLOPIG GEWAPEND BETONFRAME','**Niet voor uitvoering, vergunning of constructieve vrijgave.**','','## Bronbasis','Oorspronkelijke 15-bladige PDF (SHA256 via bestaande Phoenix-derivation); hergebruik van voorlopig belastingmodel.','Geen bevestigde koppeling van het nieuwe raster aan de architectonische CAD-plattegrond.','','## Ontwerp','3 alternatieve design-rasters met betonkolommen 350x350 mm, verdiepingsbalken 300x600 mm, dakbalken 250x500 mm.','Alle afmetingen zijn ontwerpvoorstellen, niet getoetst op RC-sterkte. Niet-dragende invulwanden uitsluitend als belasting.','Vloerhoogtes 0, 3.5, 7.0 m zijn aannames.','', '## PyNiteFEA lineaire zwaartekracht-solver — evenwicht']
 for r in results:lines.append(f"- Variant {r['variant']} {r['combo']}: opgelegde verticale belasting {r['applied_kN']} kN, som steunreacties {r['base_reaction_kN']} kN, verschil {r['imbalance_pct']}%")
 lines+=['','## Beperkingen','Geen horizontale belasting/stabiliteit, niet-gecontroleerde ontwerpcombinatie, werkelijke grondwaarden, belasting tank, verificatie balken/kolommen of wapening.','Schematische SVG geen maatvaste CAD-tekeningen; kolommen kunnen samenvallen met deuren/ramen.','','## Vrijgave','HOLD: ONTWERP, STABILITEIT, GEOTECHNIEK EN PROFESSIONELE CONTROLE.','LOCKED — NIET VOOR UITVOERING.','','## Open punten']+[f'- {b}' for b in blockers]
 (out/'PRELIMINARY_RC_FRAME_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('RC_FRAME_GATES='+json.dumps({'source_sha':'PASS_DERIVATION_IDENTITY','solver':'PASS_PYNITE_REAL_LINEAR_GRAVITY','variants':len(variants),'equilibrium':'PASS_ALL','member_capacity':'HOLD_NOT_DESIGNED','cad_binding':'HOLD','wind_stability':'HOLD','geotechnical':'HOLD','release':'LOCKED'}))
 print('RC_FRAME_COUNTS='+json.dumps({'beam_rows':len(all_beams),'column_rows':len(all_cols),'load_cases':len(results),'svg_drawings':6}))
 print('OUTPUT='+str(out))

def main():
 a=argparse.ArgumentParser();a.add_argument('--derivation',required=True);a.add_argument('--output',required=True);args=a.parse_args()
 try:run(args)
 except Exception as e: print('RC_FRAME_STATUS=HOLD_EXECUTION_ERROR '+str(e),file=sys.stderr);traceback.print_exc();sys.exit(2)
if __name__=='__main__':main()
