import argparse, csv, hashlib, json, math, pathlib, zipfile
SHA='1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def projection(p,a,b):
 v=(b[0]-a[0],b[1]-a[1]); den=v[0]**2+v[1]**2
 if den<1e-10:return 0,1e9
 t=((p[0]-a[0])*v[0]+(p[1]-a[1])*v[1])/den
 return t,dist(p,(a[0]+t*v[0],a[1]+t*v[1]))
def extract(page):
 seg={}
 for di,d in enumerate(page.get_drawings()):
  color=d.get('color');
  if color is None or not all(abs(color[i]-color[i+1])<.035 for i in (0,1)) or color[0]>.9:continue
  for ii,it in enumerate(d['items']):
   if it[0]!='l':continue
   p,q=it[1:3]; length=math.hypot(q.x-p.x,q.y-p.y)
   if length<42:continue
   cx=(p.x+q.x)/2;cy=(p.y+q.y)/2
   if not (180<cx<710 and 145<cy<735):continue
   angle=math.degrees(math.atan2(q.y-p.y,q.x-p.x))%180
   axis=0 if abs(angle-16)<2.5 else (1 if abs(angle-106)<2.5 else None)
   if axis is None:continue
   seg[f'B01_DRAW_{di}_LINE_{ii}']=((p.x,p.y),(q.x,q.y),axis)
 return seg
def main():
 p=argparse.ArgumentParser();p.add_argument('--pdf',required=True);p.add_argument('--r8',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 import fitz
 pdf=pathlib.Path(a.pdf);inp=pathlib.Path(a.r8);out=pathlib.Path(a.out)
 if sha(pdf)!=SHA:raise SystemExit('HOLD_WRONG_PDF_SHA')
 if not (inp/'R8_EVIDENCE.json').is_file():raise SystemExit('HOLD_R8_EVIDENCE_MISSING')
 ev=json.loads((inp/'R8_EVIDENCE.json').read_text(encoding='utf-8-sig'))
 if ev.get('source_pdf_sha256')!=SHA or ev.get('proposed_column_candidates')!=14:raise SystemExit('HOLD_R8_EVIDENCE_CONTRACT')
 with (inp/'R8_SOURCE_DRIVEN_COLUMN_CANDIDATES.csv').open(encoding='utf-8-sig',newline='') as f: cols=list(csv.DictReader(f))
 if len(cols)!=14 or len({c['candidate_id'] for c in cols})!=14:raise SystemExit('HOLD_R8_CANDIDATES')
 for c in cols:
  c['p']=(float(c['x_pdf_pt']),float(c['y_pdf_pt']))
 doc=fitz.open(pdf)
 if len(doc)!=15:raise SystemExit('HOLD_PDF_PAGE_COUNT')
 page=doc[0]; seg=extract(page)
 if any(c[k] not in seg for c in cols for k in ('source_vector_a','source_vector_b')):raise SystemExit('HOLD_R8_VECTOR_IDS_NOT_REPRODUCIBLE')
 out.mkdir(parents=True,exist_ok=True)
 # A potential beam alignment requires a near-collinear candidate pair; corroborating PDF vector support is assessed separately.
 pairs=[]
 for i,c in enumerate(cols):
  for d in cols[i+1:]:
   a0,b0=c['p'],d['p'];length=dist(a0,b0)
   if length<35:continue
   ang=math.degrees(math.atan2(b0[1]-a0[1],b0[0]-a0[0]))%180
   ax=0 if abs(ang-16)<2.5 else (1 if abs(ang-106)<2.5 else None)
   if ax is None:continue
   # Only directly neighboring nodes along the line within corridor, to avoid creating beams that skip intermediate nodes.
   between=[x['candidate_id'] for x in cols if x not in (c,d) and 0.05<projection(x['p'],a0,b0)[0]<0.95 and projection(x['p'],a0,b0)[1]<9]
   if between:continue
   # Union of overlap intervals from actual source vector lines, allowing slight tolerance, excluding shared endpoint alone.
   intervals=[];ids=[]
   for sid,(p1,p2,axis) in seg.items():
    if axis!=ax:continue
    t1,e1=projection(p1,a0,b0);t2,e2=projection(p2,a0,b0)
    if max(e1,e2)>5:continue
    lo=max(0,min(t1,t2));hi=min(1,max(t1,t2))
    if hi-lo>0.015:intervals.append((lo,hi,sid))
   intervals.sort();covered=0.;end=0.;maxgap=0.;start=0.;selected=[]
   for lo,hi,sid in intervals:
    if lo>end:
     maxgap=max(maxgap,lo-end)
    if hi>end:
     covered+=max(0,hi-max(lo,end));end=hi;selected.append(sid)
   maxgap=max(maxgap,1-end);ratio=min(1,covered)
   # Direct PDFs do not establish beam feasibility; this is vector continuity screening only.
   cls='GEOMETRIC_SUPPORT_CANDIDATE' if ratio>=.85 and maxgap<=.12 else 'UNSUPPORTED_GEOMETRIC_LINK'
   pairs.append({'node_a':c['candidate_id'],'node_b':d['candidate_id'],'span_pdf_pt':round(length,2),'axis':ax,'angle_deg':round(ang,2),'source_line_coverage':round(ratio,3),'max_uncovered_fraction':round(maxgap,3),'source_vector_ids':';'.join(selected[:30]),'geometric_screen':cls,'beam_status':'HOLD_NO_VERIFIED_SUPPORT_LOAD_PATH','metric_span_m':'UNVERIFIED','opening_clearance':'HOLD','solver':'NOT_RUN'})
 degrees={c['candidate_id']:0 for c in cols}
 for e in pairs:
  if e['geometric_screen']=='GEOMETRIC_SUPPORT_CANDIDATE':
   degrees[e['node_a']]+=1;degrees[e['node_b']]+=1
 with (out/'R9_CONNECTIVITY_CANDIDATES.csv').open('w',encoding='utf-8-sig',newline='') as f:
  names=['node_a','node_b','span_pdf_pt','axis','angle_deg','source_line_coverage','max_uncovered_fraction','source_vector_ids','geometric_screen','beam_status','metric_span_m','opening_clearance','solver'];w=csv.DictWriter(f,fieldnames=names);w.writeheader();w.writerows(pairs)
 with (out/'R9_COLUMN_QUALIFICATION.csv').open('w',encoding='utf-8-sig',newline='') as f:
  names=['candidate_id','x_pdf_pt','y_pdf_pt','source_vector_a','source_vector_b','geometry_degree','structural_role','architectural_clearance','support_to_foundation','qualification'];w=csv.DictWriter(f,fieldnames=names);w.writeheader()
  for c in cols:w.writerow({'candidate_id':c['candidate_id'],'x_pdf_pt':c['x_pdf_pt'],'y_pdf_pt':c['y_pdf_pt'],'source_vector_a':c['source_vector_a'],'source_vector_b':c['source_vector_b'],'geometry_degree':degrees[c['candidate_id']],'structural_role':'UNVERIFIED','architectural_clearance':'HOLD','support_to_foundation':'HOLD','qualification':'HOLD_GEOMETRY_NOT_STRUCTURAL_COLUMN'})
 img=out/'R9_ORIGINAL_B01.png';page.get_pixmap(alpha=False).save(str(img))
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{page.rect.width}" height="{page.rect.height}" viewBox="0 0 {page.rect.width} {page.rect.height}">',f'<image href="{img.name}" width="{page.rect.width}" height="{page.rect.height}"/>','<rect width="1060" height="69" fill="white" opacity="0.96"/>','<text x="18" y="25" font-size="18" font-family="Arial" font-weight="bold">ANIJSTRAAT 616 - R9 AUTO BRONLIJNVERBINDINGEN</text>','<text x="18" y="49" font-size="12" font-family="Arial" fill="#b91c1c">ALLEEN GEOMETRISCHE SCREENING / GEEN BEWEZEN BALKEN OF KOLOMMEN / RELEASE LOCKED</text>']
 lookup={c['candidate_id']:c['p'] for c in cols}
 for e in pairs:
  p1,p2=lookup[e['node_a']],lookup[e['node_b']];ok=e['geometric_screen']=='GEOMETRIC_SUPPORT_CANDIDATE'
  svg.append(f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="{"#0a8b58" if ok else "#d78a12"}" stroke-width="{"3" if ok else "1.6"}" stroke-dasharray="{"none" if ok else "5 5"}" opacity="0.85"/>')
 for c in cols:
  x,y=c['p'];svg.append(f'<circle cx="{x}" cy="{y}" r="5.7" fill="#e11d48" stroke="white" stroke-width="1.4"/><text x="{x+8}" y="{y-7}" font-size="11" font-family="Arial" fill="#9f1239">{c["candidate_id"]}</text>')
 svg.append('</svg>');(out/'R9_SOURCE_CONNECTIVITY_OVER_B01.svg').write_text('\n'.join(svg),encoding='utf-8')
 supported=sum(e['geometric_screen']=='GEOMETRIC_SUPPORT_CANDIDATE' for e in pairs)
 evidence={'project':'PHX-RP-ANIJSTRAAT-616','source_pdf_sha256':SHA,'r8_candidate_count':14,'r8_source_identity':'PASS','regenerated_pdf_source_line_count':len(seg),'candidate_links':len(pairs),'vector_supported_links':supported,'candidate_columns_with_vector_links':sum(x>0 for x in degrees.values()),'units':'PDF_POINTS_ONLY_NOT_REAL_WORLD_METERS','all_structural_columns_verified':False,'all_beams_verified':False,'load_path_complete':False,'gates':{'source':'PASS_ORIGINAL_PDF_AND_R8_CANDIDATES','topology':'PASS_GEOMETRIC_LINK_SCREEN_ONLY','structural_column_qualification':'HOLD_SEMANTIC_AND_FOUNDATION_SUPPORT','architectural_opening_clearance':'HOLD','metric_span':'HOLD_NO_INDEPENDENT_DIMENSION_ANCHORS','connectivity_for_FEM':'HOLD_NOT_VERIFIED_LOAD_PATH','solver':'NOT_EXECUTED_UNVERIFIED_LAYOUT','release':'LOCKED'}}
 (out/'R9_EVIDENCE.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding='utf-8')
 (out/'R9_REPORT.md').write_text('# R9 AUTO — Constructieve verbindingen, bronlijnscreening\n\n'+f'- 14 onverifieerde R8-kolomkandidaten, {len(pairs)} mogelijke verbindingen langs de herkenbare bronrichtingen.\n- {supported} verbindingen met voldoende vectorlijn-dekking als *geometrische* kandidaat; dit is geen balkontwerp.\n- {sum(x>0 for x in degrees.values())} van de 14 punten hebben minstens een dergelijke verbinding.\n- Lengtes zijn uitsluitend in PDF-punten, **niet** in meters.\n- Deur-/raamsemantiek, werkelijke funderingsoplegging, volledige lastafdracht, wind en maatvoering niet bewezen.\n- Geen nieuwe PyNiteFEA-berekening; geen toestemming om de R1-krachten naar dit stelsel over te zetten.\n\n## Besluit\n**HOLD:** eerst brongebonden wand-/openingssemantiek en gemeten schaal met onafhankelijk maatbewijs. Niet opnieuw willekeurige frames tekenen.\n',encoding='utf-8')
 with zipfile.ZipFile(out/'UPLOAD_THIS_REVIEW.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in ['R9_EVIDENCE.json','R9_REPORT.md','R9_CONNECTIVITY_CANDIDATES.csv','R9_COLUMN_QUALIFICATION.csv','R9_SOURCE_CONNECTIVITY_OVER_B01.svg','R9_ORIGINAL_B01.png']:z.write(out/name,name)
 print('R9_GATES='+json.dumps(evidence['gates']))
 print('R9_COUNTS='+json.dumps({k:evidence[k] for k in ['r8_candidate_count','candidate_links','vector_supported_links','candidate_columns_with_vector_links']}))
 print('RESULT='+str(out));print('UPLOAD='+str(out/'UPLOAD_THIS_REVIEW.zip'))
if __name__=='__main__':main()
