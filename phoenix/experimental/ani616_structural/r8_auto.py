import argparse,csv,hashlib,json,math,pathlib,zipfile
from collections import Counter
SHA='1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0'
def hashfile(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for v in iter(lambda:f.read(1<<20),b''):h.update(v)
 return h.hexdigest()
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def inter(s,t):
 p=(s['x1'],s['y1']);r=(s['x2']-p[0],s['y2']-p[1]);q=(t['x1'],t['y1']);v=(t['x2']-q[0],t['y2']-q[1]);det=cross(r,v)
 if abs(det)<1e-5:return None
 d=(q[0]-p[0],q[1]-p[1]);u=cross(d,v)/det;w=cross(d,r)/det
 if -.025<=u<=1.025 and -.025<=w<=1.025:return (p[0]+u*r[0],p[1]+u*r[1])
 return None
def main():
 a=argparse.ArgumentParser();a.add_argument('--pdf',required=True);a.add_argument('--out',required=True);a.add_argument('--repo',default='');z=a.parse_args()
 import fitz
 pdf=pathlib.Path(z.pdf);out=pathlib.Path(z.out);out.mkdir(parents=True,exist_ok=True)
 if hashfile(pdf)!=SHA:raise SystemExit('HOLD_WRONG_ORIGINAL_VO_SHA')
 doc=fitz.open(pdf)
 if len(doc)!=15:raise SystemExit('HOLD_PDF_NOT_15_PAGES')
 page=doc[0];segments=[];skipped=Counter()
 # Vector selection: avoid cyan dimensions/magenta annotations. These remain geometry candidates, not classified walls.
 for di,d in enumerate(page.get_drawings()):
  color=d.get('color'); width=float(d.get('width') or 0)
  if color is None:skipped['unknown_color']+=1;continue
  if not all(abs(x-y)<.035 for x,y in ((color[0],color[1]),(color[1],color[2]))):skipped['colored_dimension_annotation']+=1;continue
  if color[0]>.9:continue
  for ii,it in enumerate(d['items']):
   if it[0]!='l':continue
   p,q=it[1:3];length=math.hypot(q.x-p.x,q.y-p.y)
   if length<42:continue
   cx=(p.x+q.x)/2;cy=(p.y+q.y)/2
   if not (180<cx<710 and 145<cy<735):continue
   angle=math.degrees(math.atan2(q.y-p.y,q.x-p.x))%180
   axis=0 if min(abs(angle-16),abs(angle-196))<2.5 else (1 if abs(angle-106)<2.5 else None)
   if axis is None:continue
   segments.append({'id':f'B01_DRAW_{di}_LINE_{ii}','x1':p.x,'y1':p.y,'x2':q.x,'y2':q.y,'length':length,'axis':axis,'color':color,'width':width})
 hits=[]
 for i,s in enumerate(segments):
  for t in segments[i+1:]:
   if s['axis']==t['axis']:continue
   xy=inter(s,t)
   if xy is None:continue
   x,y=xy
   if not (178<x<710 and 145<y<740):continue
   hits.append({'x':x,'y':y,'a':s['id'],'b':t['id'],'support':min(s['length'],t['length'])})
 # Cluster CAD line intersections; avoid summing identical linework as extra independent evidence.
 clusters=[]
 for h in sorted(hits,key=lambda t:-t['support']):
  c=next((c for c in clusters if math.hypot(c['x']-h['x'],c['y']-h['y'])<9),None)
  if c is None:clusters.append({'x':h['x'],'y':h['y'],'hits':[h]})
  else:c['hits'].append(h)
 for c in clusters:c['score']=round(max(v['support'] for v in c['hits']),2);c['source_pair']=[c['hits'][0]['a'],c['hits'][0]['b']]
 chosen=[]
 for c in sorted(clusters,key=lambda c:-c['score']):
  if any(math.hypot(c['x']-q['x'],c['y']-q['y'])<54 for q in chosen):continue
  chosen.append(c)
  if len(chosen)>=18:break
 # No fixed grid or fabricated semantic identifications. Results only source-based point proposals.
 png=out/'R8_B01_UNMODIFIED.png';page.get_pixmap(alpha=False).save(str(png))
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{page.rect.width}" height="{page.rect.height}" viewBox="0 0 {page.rect.width} {page.rect.height}">',f'<image href="{png.name}" width="{page.rect.width}" height="{page.rect.height}"/>','<rect x="0" y="0" width="1055" height="68" fill="white" opacity=".96"/>','<text x="18" y="24" font-family="Arial" font-size="18" font-weight="bold">ANIJSTRAAT 616 - R8 AUTO BRONGESTUURDE KOLOMKANDIDATEN</text>','<text x="18" y="49" font-family="Arial" font-size="13" fill="#bd1e28">BRONLIJNKRUISINGEN: ONGEVERIFIEERDE KOLOMVOORSTELLEN - GEEN CONSTRUCTIEVE VRIJGAVE</text>']
 for s in segments:
  svg.append(f'<line x1="{s["x1"]:.2f}" y1="{s["y1"]:.2f}" x2="{s["x2"]:.2f}" y2="{s["y2"]:.2f}" stroke="#07875e" stroke-width="1.2" opacity=".58"/>')
 for i,c in enumerate(chosen,1):
  x=c['x'];y=c['y'];svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6.5" fill="#e11d48" stroke="white" stroke-width="2"/><text x="{x+9:.2f}" y="{y-7:.2f}" font-family="Arial" font-size="11" fill="#8a0e2a" font-weight="bold">K{i:02}</text>')
 svg.append('</svg>');(out/'R8_SOURCE_DRIVEN_COLUMN_PROPOSALS.svg').write_text('\n'.join(svg),encoding='utf8')
 rows=[{'candidate_id':f'K{i:02}','x_pdf_pt':round(c['x'],3),'y_pdf_pt':round(c['y'],3),'support_length_pdf_pt':c['score'],'source_vector_a':c['source_pair'][0],'source_vector_b':c['source_pair'][1],'role':'UNVERIFIED_LINE_INTERSECTION_NOT_CONFIRMED_WALL','opening_clash':'HOLD_NO_SEMANTIC_OPENING_BINDING','member_design':'NOT_RUN','source_status':'PDF_B01_LINE_REFERENCE'} for i,c in enumerate(chosen,1)]
 with (out/'R8_SOURCE_DRIVEN_COLUMN_CANDIDATES.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['candidate_id','x_pdf_pt','y_pdf_pt','support_length_pdf_pt','source_vector_a','source_vector_b','role','opening_clash','member_design','source_status']);w.writeheader();w.writerows(rows)
 evidence={'project':'PHX-RP-ANIJSTRAAT-616','source_pdf_sha256':SHA,'method':'B01 PDF vector orthogonal intersections from neutral-color long lines; no preselected uniform grid','candidate_vector_lines':len(segments),'raw_intersections':len(hits),'distinct_intersection_clusters':len(clusters),'proposed_column_candidates':len(rows),'pdf_reference_points':len(rows),'independent_dimension_chain_anchors':0,'verified_wall_semantics':0,'geometry_status':'SOURCE_PDF_VECTOR_CANDIDATES_ONLY','warnings':['Grey/black PDF line segments can include wall outlines, construction/annotation lines; semantic identities are not verified','Candidate column positions are not checked for door, window, circulation, terrace or foundation clashes','Prior R1 PyNiteFEA frame results cannot be transferred to new irregular candidate layout','No member sizing, structural analysis, wind/stability or foundation design performed'],'gates':{'pdf':'PASS_EXACT_SOURCE','source_line_candidates':'PASS_EXTRACTED','source_driven_layout':'PASS_CONCEPT_CANDIDATES','metric_registration':'HOLD_NO_VERIFIED_DIMENSION_ENDPOINTS','column_clashes':'HOLD_SEMANTICS_UNVERIFIED','engineering_solver':'NOT_EXECUTED_NEW_LAYOUT_UNVERIFIED','release':'LOCKED'}}
 (out/'R8_EVIDENCE.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding='utf8')
 (out/'R8_REPORT.md').write_text('# R8 AUTO — brongestuurde kolomkandidaten\n\nOriginele PDF B01, geen 4x4-raster. '+str(len(segments))+' neutraal gekleurde bouwlijnkandidaten, '+str(len(clusters))+' kruisingclusters, '+str(len(rows))+' niet-gevalideerde kolomlocaties.\n\nDit is een **schematische kandidaatselectie**. PDF-vectorlijnen zijn nog geen betrouwbare wandassen of maatkettingen. Kolom-/deurconflicten en nieuwe frameberekening zijn terecht geblokkeerd.\n\nEerst automatisch wand- en openingsemantiek uit bewezen CAD/PDF-bronnen koppelen, daarna maatvaste registratie en pas dan opnieuw solver.\n',encoding='utf8')
 with zipfile.ZipFile(out/'UPLOAD_THIS_REVIEW.zip','w',zipfile.ZIP_DEFLATED) as zf:
  for name in ['R8_EVIDENCE.json','R8_REPORT.md','R8_SOURCE_DRIVEN_COLUMN_CANDIDATES.csv','R8_SOURCE_DRIVEN_COLUMN_PROPOSALS.svg','R8_B01_UNMODIFIED.png']:zf.write(out/name,name)
 print('R8_GATES='+json.dumps(evidence['gates']))
 print('R8_COUNTS='+json.dumps({k:evidence[k] for k in ['candidate_vector_lines','raw_intersections','distinct_intersection_clusters','proposed_column_candidates']}))
 print('RESULT='+str(out));print('UPLOAD='+str(out/'UPLOAD_THIS_REVIEW.zip'))
if __name__=='__main__': main()
