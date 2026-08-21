from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, struct, subprocess, time, urllib.request, zlib
from pathlib import Path
CANONICAL_PROJECT_FILE="configs/projects/moskee_bunschoten.json"
PROJECT_FILE="configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"
TOKENS=("moskee","bunschoten","hbm-2026-001","hbm_2026_001")
OK={"completed","complete","succeeded","success","passed","done"}; BAD={"failed","failure","error","blocked","cancelled","canceled"}
def sha(p):
 h=hashlib.sha256(); f=p.open('rb')
 while True:
  b=f.read(1048576)
  if not b: break
  h.update(b)
 f.close(); return h.hexdigest()
def dump(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def getj(url,t=2):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'Cache-Control':'no-cache'}),timeout=t) as r: return json.loads(r.read().decode())
def gettext(url,t=2):
 with urllib.request.urlopen(url,timeout=t) as r: return r.read().decode(errors='replace')
def ports(repo):
 vals=[8765,8000,8080,5000,3000,8501,8888]; rx=re.compile(r'(?i)(?:127\.0\.0\.1|localhost):(\d{2,5})')
 for rel in ('START_PROJECT_PHOENIX_OFFICIAL.ps1','phoenix/local_app/server.py'):
  p=repo/rel
  if p.exists(): vals += [int(x) for x in rx.findall(p.read_text(encoding='utf-8',errors='ignore'))]
 return list(dict.fromkeys(vals))
def baseurl(repo):
 for port in ports(repo):
  for host in ('127.0.0.1','localhost'):
   b=f'http://{host}:{port}'
   try:
    if isinstance(getj(b+'/api/status',1),dict) and 'PHOENIX' in gettext(b+'/start-v3/',1).upper(): return b
   except: pass
 return ''
def start(repo):
 p=repo/'START_PROJECT_PHOENIX_OFFICIAL.ps1'
 if not p.exists(): return
 flags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0
 subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(p)],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
def waitbase(repo,sec=60):
 end=time.time()+sec
 while time.time()<end:
  b=baseurl(repo)
  if b:return b
  time.sleep(1.5)
 return ''
def channel():
 for c,p in [('msedge',Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')),('msedge',Path(r'C:\Program Files\Microsoft\Edge\Application\msedge.exe')),('chrome',Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')),('chrome',Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'))]:
  if p.exists(): return c
 return ''
def strings(v):
 if isinstance(v,dict):
  for x in v.values(): yield from strings(x)
 elif isinstance(v,list):
  for x in v: yield from strings(x)
 elif isinstance(v,str): yield v
def resolve(repo,s):
 if not s:return None
 if s.startswith('file:///'): s=s[8:].replace('/','\\')
 p=Path(s.strip().strip('"'))
 if p.is_absolute() and p.exists():return p
 q=repo/s.replace('\\',os.sep)
 return q.resolve() if q.exists() else None
def inventory(repo,start,status):
 out=[]; seen=set()
 for s in strings(status):
  p=resolve(repo,s)
  if p and p.is_file() and str(p).lower() not in seen: seen.add(str(p).lower()); out.append(p)
 for root in (repo/'outputs',repo/'projects',repo/'runtime'):
  if not root.exists():continue
  for p in root.rglob('*'):
   if not p.is_file():continue
   low=str(p).lower(); scoped=any(t in low for t in TOKENS)
   try: recent=p.stat().st_mtime>=start-120
   except: recent=False
   if (scoped or recent) and low not in seen: seen.add(low); out.append(p)
 return out
def cats(ps):
 d={k:[] for k in ('ifc','freecad','blender','visual','drawing','inp','raw','manifest','other')}
 for p in ps:
  n=p.name.lower(); s=p.suffix.lower()
  if s=='.ifc':k='ifc'
  elif s=='.fcstd' or 'freecad' in n:k='freecad'
  elif s=='.blend' or 'blender' in n:k='blender'
  elif s in {'.png','.jpg','.jpeg','.webp','.apng','.html','.htm','.mp4','.webm'} or 'viewer' in n or 'detv' in n:k='visual'
  elif s in {'.pdf','.svg','.dxf','.dwg'} or 'drawing' in n or 'tekening' in n:k='drawing'
  elif s=='.inp':k='inp'
  elif s in {'.frd','.dat','.sta','.cvg','.12d'}:k='raw'
  elif 'manifest' in n:k='manifest'
  else:k='other'
  d[k].append(p)
 return d
def png_quality(p):
 b=p.read_bytes()
 if not b.startswith(b'\x89PNG\r\n\x1a\n'): return {'checked':False}
 pos=8; idat=bytearray(); w=h=bd=ct=None
 while pos+8<=len(b):
  ln=struct.unpack('>I',b[pos:pos+4])[0]; typ=b[pos+4:pos+8]; data=b[pos+8:pos+8+ln]; pos+=12+ln
  if typ==b'IHDR':w,h,bd,ct,_,_,_=struct.unpack('>IIBBBBB',data)
  elif typ==b'IDAT':idat.extend(data)
  elif typ==b'IEND':break
 if not w or bd!=8 or ct not in (2,6):return {'checked':False}
 bpp=3 if ct==2 else 4; stride=w*bpp; raw=zlib.decompress(bytes(idat)); rows=[]; prev=bytearray(stride); idx=0
 def paeth(a,b,c):
  q=a+b-c; aa=abs(q-a);bb=abs(q-b);cc=abs(q-c);return a if aa<=bb and aa<=cc else (b if bb<=cc else c)
 for _ in range(h):
  f=raw[idx];idx+=1; scan=bytearray(raw[idx:idx+stride]);idx+=stride; rec=bytearray(stride)
  for i,x in enumerate(scan):
   a=rec[i-bpp] if i>=bpp else 0;bb=prev[i];c=prev[i-bpp] if i>=bpp else 0
   val=x if f==0 else ((x+a)&255 if f==1 else ((x+bb)&255 if f==2 else ((x+((a+bb)//2))&255 if f==3 else ((x+paeth(a,bb,c))&255 if f==4 else x))))
   rec[i]=val
  rows.append(rec);prev=rec
 vals=[]
 for y in range(0,h,max(1,h//50)):
  row=rows[y]
  for x in range(0,w,max(1,w//70)):
   i=x*bpp; vals.append((row[i]*299+row[i+1]*587+row[i+2]*114)//1000)
 spread=max(vals)-min(vals) if vals else 0; uniq=len(set(vals));return {'checked':True,'width':w,'height':h,'spread':spread,'unique':uniq,'nonblank':spread>=12 and uniq>=8}
def play(base,edir,timeout):
 from playwright.sync_api import sync_playwright
 with sync_playwright() as pw:
  kw={'headless':True};ch=channel();
  if ch:kw['channel']=ch
  browser=pw.chromium.launch(**kw); ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(edir/'video'));ctx.tracing.start(screenshots=True,snapshots=True,sources=True);page=ctx.new_page();logs=[];page.on('console',lambda m:logs.append(f'{m.type}: {m.text}'))
  page.goto(base+'/start-v3/',wait_until='networkidle',timeout=60000);page.screenshot(path=str(edir/'01_start.png'),full_page=True)
  status=page.evaluate("async()=>await(await fetch('/api/status',{cache:'no-store'})).json()");projects=(status.get('architectural_orchestration') or {}).get('projects') or []
  if not any(str(p.get('file','')).replace('\\\\','/')==PROJECT_FILE for p in projects):raise RuntimeError('moskee project absent from official catalog')
  t=page.locator('.phx-cap-toggle');
  if t.count():t.click()
  sel=page.locator('.phx-cap-project');sel.select_option(PROJECT_FILE);page.screenshot(path=str(edir/'02_selected.png'),full_page=True)
  btn=page.locator('button.phx-cap-run:not([disabled])');
  if btn.count()<1:raise RuntimeError('no enabled autonomous projectflow action')
  started=time.time();btn.first.click();page.screenshot(path=str(edir/'03_started.png'),full_page=True);end=time.time()+timeout;latest=None
  while time.time()<end:
   status=page.evaluate("async()=>await(await fetch('/api/status',{cache:'no-store'})).json()");latest=(status.get('architectural_orchestration') or {}).get('latest_job'); st=str((latest or {}).get('status','')).lower()
   if st in OK:break
   if st in BAD:raise RuntimeError(f'projectflow terminal failure: {latest}')
   page.wait_for_timeout(2000)
  else:raise RuntimeError('projectflow timeout')
  page.screenshot(path=str(edir/'04_completed.png'),full_page=True);ctx.tracing.stop(path=str(edir/'trace.zip'));ctx.close();browser.close();(edir/'console.log').write_text('\n'.join(logs)+'\n',encoding='utf-8')
  rec=(latest or {}).get('recommended_variant_id')
  if not rec:raise RuntimeError('recommended_variant_id missing')
  return status,latest,started,rec
def selenium_run(base,edir,timeout):
 from selenium import webdriver
 from selenium.webdriver.common.by import By
 from selenium.webdriver.support.ui import Select
 o=webdriver.EdgeOptions();o.add_argument('--headless=new');o.add_argument('--window-size=1440,1000');d=webdriver.Edge(options=o)
 try:
  d.get(base+'/start-v3/');d.save_screenshot(str(edir/'01_start.png'));status=d.execute_async_script("const done=arguments[0];fetch('/api/status',{cache:'no-store'}).then(r=>r.json()).then(done).catch(e=>done({__error:String(e)}));");projects=(status.get('architectural_orchestration') or {}).get('projects') or []
  if not any(str(p.get('file','')).replace('\\\\','/')==PROJECT_FILE for p in projects):raise RuntimeError('moskee project absent')
  ts=d.find_elements(By.CSS_SELECTOR,'.phx-cap-toggle');
  if ts:ts[0].click()
  Select(d.find_element(By.CSS_SELECTOR,'.phx-cap-project')).select_by_value(PROJECT_FILE);started=time.time();d.find_element(By.CSS_SELECTOR,'button.phx-cap-run:not([disabled])').click();end=time.time()+timeout;latest=None
  while time.time()<end:
   status=d.execute_async_script("const done=arguments[0];fetch('/api/status',{cache:'no-store'}).then(r=>r.json()).then(done).catch(e=>done({__error:String(e)}));");latest=(status.get('architectural_orchestration') or {}).get('latest_job');st=str((latest or {}).get('status','')).lower()
   if st in OK:break
   if st in BAD:raise RuntimeError(f'projectflow failure:{latest}')
   time.sleep(2)
  else:raise RuntimeError('projectflow timeout')
  d.save_screenshot(str(edir/'04_completed.png'));rec=(latest or {}).get('recommended_variant_id')
  if not rec:raise RuntimeError('recommended variant missing')
  return status,latest,started,rec
 finally:d.quit()
def render_visual(p,edir):
 from playwright.sync_api import sync_playwright
 shot=edir/'05_visual.png'
 with sync_playwright() as pw:
  kw={'headless':True};ch=channel();
  if ch:kw['channel']=ch
  b=pw.chromium.launch(**kw);pg=b.new_page(viewport={'width':1440,'height':1000});pg.goto(p.resolve().as_uri(),wait_until='load',timeout=60000);pg.wait_for_timeout(1000);pg.screenshot(path=str(shot),full_page=True);b.close()
 q=png_quality(shot)
 if not q.get('nonblank'):raise RuntimeError(f'blank visual:{q}')
 return q
def finddeck(repo,c):
 for p in c['inp']:
  if any(t in str(p).lower() for t in TOKENS):return p
 for p in repo.rglob('*.inp'):
  if any(t in str(p).lower() for t in TOKENS):return p
 return None
def ccx(deck,exe,edir):
 w=edir/'calculix_work';w.mkdir();cpdeck=w/deck.name;shutil.copy2(deck,cpdeck);cp=subprocess.run([str(exe),'-i',cpdeck.stem],cwd=w,text=True,capture_output=True,timeout=900);(edir/'calculix_stdout.txt').write_text(cp.stdout,encoding='utf-8',errors='replace');(edir/'calculix_stderr.txt').write_text(cp.stderr,encoding='utf-8',errors='replace');raw=[p for p in w.iterdir() if p.is_file()];return {'exit_code':cp.returncode,'success':cp.returncode==0 and any(p.suffix.lower() in {'.frd','.dat','.sta'} for p in raw),'deck':str(deck),'exe':str(exe),'raw':[{ 'path':str(p),'sha256':sha(p)} for p in raw]}
def main():
 a=argparse.ArgumentParser();a.add_argument('--repo',required=True);a.add_argument('--evidence-root',required=True);a.add_argument('--calculix',required=True);a.add_argument('--calculix-fallback',default='');a.add_argument('--timeout-seconds',type=int,default=1800);n=a.parse_args();repo=Path(n.repo).resolve();edir=Path(n.evidence_root)/('RUN_'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));edir.mkdir(parents=True);state={'project':PROJECT_FILE,'canonical_project':CANONICAL_PROJECT_FILE,'repo':str(repo),'result':'STARTED','production':'LOCKED','for_construction':'LOCKED'};dump(edir/'00_state.json',state)
 b=baseurl(repo)
 if not b:start(repo);b=waitbase(repo)
 if not b:state['result']='BLOCKED_OFFICIAL_START';dump(edir/'FINAL_E2E_RESULT.json',state);print('E2E_RUNTIME_RESULT=BLOCKED_OFFICIAL_START');print('E2E_EVIDENCE_DIR='+str(edir));return 20
 print('OFFICIAL_START_V3_REACHABLE=PASS');print('OFFICIAL_BASE_URL='+b)
 try:status,latest,started,rec=play(b,edir,n.timeout_seconds);backend='PLAYWRIGHT'
 except Exception as pe:
  (edir/'playwright_failure.txt').write_text(str(pe)+'\n',encoding='utf-8')
  try:status,latest,started,rec=selenium_run(b,edir,n.timeout_seconds);backend='SELENIUM_FALLBACK'
  except Exception as se:state.update(result='BLOCKED_BROWSER_OR_PROJECTFLOW',playwright_error=str(pe),selenium_error=str(se));dump(edir/'FINAL_E2E_RESULT.json',state);print('E2E_RUNTIME_RESULT=BLOCKED_BROWSER_OR_PROJECTFLOW');print('E2E_EVIDENCE_DIR='+str(edir));return 21
 print('BROWSER_EVIDENCE_BACKEND='+backend);print('AUTONOMOUS_PROJECTFLOW_TERMINAL_SUCCESS=PASS');print('RECOMMENDED_VARIANT='+str(rec));dump(edir/'06_terminal_status.json',status)
 ps=inventory(repo,started,status);c=cats(ps);inv={k:[{'path':str(p),'sha256':sha(p),'size':p.stat().st_size} for p in v] for k,v in c.items()};dump(edir/'07_inventory.json',inv);print('PROJECT_SCOPED_ARTIFACT_INVENTORY=PASS');print('ARTIFACT_COUNT='+str(sum(len(v) for v in c.values())))
 best=next(iter(sorted(c['visual'],key=lambda p:(('detv' in p.name.lower())*3+('viewer' in p.name.lower())*2+p.stat().st_mtime),reverse=True)),None)
 if not best:state.update(result='BLOCKED_NO_VISUAL_ARTIFACT');dump(edir/'FINAL_E2E_RESULT.json',state);print('E2E_RUNTIME_RESULT=BLOCKED_NO_VISUAL_ARTIFACT');print('E2E_EVIDENCE_DIR='+str(edir));return 22
 try:q=render_visual(best,edir);dump(edir/'08_visual_quality.json',{'artifact':str(best),'quality':q});print('VISUAL_ARTIFACT_BROWSER_RENDER=PASS');print('NON_BLANK_VISUAL_EVIDENCE=PASS')
 except Exception as e:state.update(result='BLOCKED_VISUAL_QUALITY',error=str(e),artifact=str(best));dump(edir/'FINAL_E2E_RESULT.json',state);print('E2E_RUNTIME_RESULT=BLOCKED_VISUAL_QUALITY');print('E2E_EVIDENCE_DIR='+str(edir));return 23
 deck=finddeck(repo,c);solver={'attempted':False,'reason':'no_project_scoped_input'}
 if deck:
  ex=Path(n.calculix);fb=Path(n.calculix_fallback) if n.calculix_fallback else None;ex=ex if ex.exists() else (fb if fb and fb.exists() else None)
  if not ex:state['result']='BLOCKED_CALCULIX_BINARY';dump(edir/'FINAL_E2E_RESULT.json',state);return 24
  try:solver=ccx(deck,ex,edir)
  except Exception as e:solver={'attempted':True,'success':False,'error':str(e)}
  dump(edir/'09_calculix.json',solver)
  if not solver.get('success'):state.update(result='BLOCKED_CALCULIX_REAL_EXECUTION',solver=solver);dump(edir/'FINAL_E2E_RESULT.json',state);print('E2E_RUNTIME_RESULT=BLOCKED_CALCULIX_REAL_EXECUTION');print('E2E_EVIDENCE_DIR='+str(edir));return 25
  print('CALCULIX_REAL_EXECUTION=PASS');print('RAW_SOLVER_EVIDENCE=PASS')
 else:print('CALCULIX_REAL_EXECUTION=NOT_RUN_NO_PROJECT_SCOPED_INPUT')
 man=[]
 for p in sorted(edir.rglob('*')):
  if p.is_file() and p.name!='E2E_SHA256_MANIFEST.json':man.append({'path':str(p.relative_to(edir)),'sha256':sha(p),'size':p.stat().st_size})
 dump(edir/'E2E_SHA256_MANIFEST.json',man);state.update(result='PASS',backend=backend,recommended_variant=rec,visual=str(best),solver=solver);dump(edir/'FINAL_E2E_RESULT.json',state);print('E2E_SHA256_EVIDENCE_MANIFEST=PASS');print('E2E_RUNTIME_RESULT=PASS');print('E2E_EVIDENCE_DIR='+str(edir));print('PRODUCTION_RELEASE=LOCKED');print('FOR_CONSTRUCTION=LOCKED');return 0
if __name__=='__main__':raise SystemExit(main())
