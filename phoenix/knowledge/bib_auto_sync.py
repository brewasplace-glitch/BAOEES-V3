from __future__ import annotations
import argparse, hashlib, io, json, re, shutil, sqlite3, subprocess, zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

SCHEMA_VERSION="1.0"
MANAGED_REL="bib/PHOENIX_AUTO_SYNC"
RUNTIME_REL=f"{MANAGED_REL}/runtime"
TEXT_EXTENSIONS={".md",".txt",".rst",".json",".jsonl",".yaml",".yml",".toml",".ini",".cfg",".csv",".xml",".html",".htm",".sql",".docx",".pdf"}
SOURCE_EXTENSIONS=TEXT_EXTENSIONS|{".py",".ps1",".psm1",".js",".mjs",".cjs",".ts",".tsx",".jsx",".css",".scss",".sh",".bat",".cmd",".psd1",".ps1xml",".xsd"}
EXCLUDE_PREFIXES=(".git/","projects/runtime/","outputs/runtime/","runtime/",".venv/","venv/","node_modules/","__pycache__/",".pytest_cache/",".mypy_cache/","dist/","build/",f"{MANAGED_REL.lower()}/")
SECRET_PATTERNS=[
 (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",re.S),"[REDACTED_PRIVATE_KEY]"),
 (re.compile(r"\bAKIA[0-9A-Z]{16}\b"),"[REDACTED_AWS_ACCESS_KEY]"),
 (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),"[REDACTED_GITHUB_TOKEN]"),
 (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),"[REDACTED_GITHUB_TOKEN]"),
 (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),"[REDACTED_API_KEY]"),
]

def run(repo,args,check=True,text=True):
    cp=subprocess.run(args,cwd=repo,capture_output=True,text=text,encoding="utf-8" if text else None,errors="replace" if text else None)
    if check and cp.returncode!=0:
        out=cp.stdout if text else cp.stdout.decode("utf-8","replace")
        err=cp.stderr if text else cp.stderr.decode("utf-8","replace")
        raise RuntimeError(f"Command failed ({cp.returncode}): {' '.join(args)}\n{out}\n{err}")
    return cp

def git(repo,args,check=True,text=True): return run(repo,["git",*args],check=check,text=text)
def normalize(path):
    p=path.replace("\\","/")
    while p.startswith("./"):
        p=p[2:]
    return p
def excluded(path):
    p=normalize(path).lower()
    return any(p.startswith(x) for x in EXCLUDE_PREFIXES)

def source_candidate(path):
    if excluded(path): return False
    pp=PurePosixPath(normalize(path))
    return pp.suffix.lower() in SOURCE_EXTENSIONS or pp.name.lower() in {"readme","license","copying","notice",".gitignore",".gitattributes"}

def knowledge_segment(path):
    parts=[p.lower() for p in PurePosixPath(normalize(path)).parts]
    for part in parts[:-1]:
        compact=re.sub(r"[^a-z0-9]+","",part)
        if part in {"docs","documentation","configs","config","bib","knowledge","pkb"} or "knowledge" in part or compact=="brewsterengineeringwizardminlevenswerk":
            return True
    return False

def full_content(path):
    if not source_candidate(path): return False
    pp=PurePosixPath(normalize(path))
    if knowledge_segment(path): return True
    return len(pp.parts)==1 and (pp.suffix.lower() in TEXT_EXTENSIONS or pp.name.lower().startswith(("readme","roadmap","architecture")))

def detect_bib_roots(paths):
    roots=set()
    for path in paths:
        parts=PurePosixPath(normalize(path)).parts[:-1]
        for i,part in enumerate(parts):
            low=part.lower(); compact=re.sub(r"[^a-z0-9]+","",low)
            if low in {"bib","knowledge","pkb"} or "knowledge" in low or compact=="brewsterengineeringwizardminlevenswerk":
                roots.add("/".join(parts[:i+1])); break
    roots.discard(MANAGED_REL)
    return sorted(roots,key=lambda s:(s.count("/"),s.lower()))

def snapshot(repo,mode):
    branch=git(repo,["rev-parse","--abbrev-ref","HEAD"]).stdout.strip()
    head=git(repo,["rev-parse","HEAD"]).stdout.strip()
    entries=[]
    if mode=="git-index":
        raw=git(repo,["ls-files","-s","-z"],text=False).stdout
        for rec in raw.split(b"\0"):
            if not rec: continue
            meta,pb=rec.split(b"\t",1); mb,oidb,stageb=meta.split(b" ",2)
            if stageb!=b"0": continue
            path=pb.decode("utf-8","surrogateescape")
            if source_candidate(path):
                normalized=normalize(path)
                if path.startswith(".") and not normalized.startswith("."):
                    raise RuntimeError(f"Dotfile path normalization changed Git identity: {path} -> {normalized}")
                entries.append({"path":normalized,"oid":oidb.decode("ascii"),"git_mode":mb.decode("ascii")})
    elif mode=="head":
        raw=git(repo,["ls-tree","-r","-z","HEAD"],text=False).stdout
        for rec in raw.split(b"\0"):
            if not rec: continue
            meta,pb=rec.split(b"\t",1); mb,tb,oidb=meta.split(b" ",2)
            if tb!=b"blob": continue
            path=pb.decode("utf-8","surrogateescape")
            if source_candidate(path):
                normalized=normalize(path)
                if path.startswith(".") and not normalized.startswith("."):
                    raise RuntimeError(f"Dotfile path normalization changed Git identity: {path} -> {normalized}")
                entries.append({"path":normalized,"oid":oidb.decode("ascii"),"git_mode":mb.decode("ascii")})
    else: raise ValueError(mode)
    entries.sort(key=lambda x:x["path"].lower())
    return entries,branch,head

def read_blob(repo,mode,path):
    spec=f":{path}" if mode=="git-index" else f"HEAD:{path}"
    return git(repo,["show",spec],text=False).stdout

def digest(entries):
    h=hashlib.sha256()
    for e in entries:
        h.update(e["path"].encode("utf-8","surrogateescape")); h.update(b"\0"); h.update(e["oid"].encode("ascii")); h.update(b"\n")
    return h.hexdigest()

def redact(text):
    count=0
    for pattern,replacement in SECRET_PATTERNS:
        text,n=pattern.subn(replacement,text); count+=n
    return text,count

def decode_text(path,data):
    suffix=PurePosixPath(path).suffix.lower()
    if suffix==".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf: xml=zf.read("word/document.xml")
            root=ET.fromstring(xml)
            return "\n".join(n.text for n in root.iter() if n.tag.endswith("}t") and n.text),"docx-xml"
        except Exception: return None,"metadata-only"
    if suffix==".pdf":
        try:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(data)); text="\n".join((p.extract_text() or "") for p in reader.pages)
            return (text,"pypdf") if text.strip() else (None,"metadata-only")
        except Exception: return None,"metadata-only"
    for enc in ("utf-8-sig","utf-8","cp1252","latin-1"):
        try:
            text=data.decode(enc)
            if "\x00" in text: return None,"binary"
            return text,enc
        except UnicodeDecodeError: pass
    return None,"metadata-only"

def chunks(text,max_chars=12000):
    text=text.replace("\r\n","\n").replace("\r","\n").strip()
    if not text: return []
    out=[]; start=0; n=len(text)
    while start<n:
        end=min(start+max_chars,n)
        if end<n:
            split=text.rfind("\n\n",start,end)
            if split<start+max_chars//2: split=text.rfind("\n",start,end)
            if split<start+max_chars//2: split=text.rfind(" ",start,end)
            if split>start: end=split
        piece=text[start:end].strip()
        if piece: out.append(piece)
        start=max(end,start+1)
    return out

def previous(managed):
    by_path={}; by_chunks={}
    try:
        data=json.loads((managed/"BIB_MANIFEST.json").read_text(encoding="utf-8"))
        by_path={x["path"]:x for x in data.get("files",[])}
    except Exception: pass
    try:
        for line in (managed/"BIB_KNOWLEDGE_FALLBACK.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj=json.loads(line); by_chunks.setdefault(obj["path"],[]).append(obj)
    except Exception: pass
    return by_path,by_chunks

def history(repo,limit=500):
    cp=git(repo,["log",f"-n{limit}","--date=iso-strict","--pretty=format:%H%x1f%aI%x1f%s"])
    out=[]
    for line in cp.stdout.splitlines():
        p=line.split("\x1f",2)
        if len(p)==3: out.append({"commit":p[0],"date":p[1],"subject":p[2]})
    return out

def build_db(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): path.unlink()
    con=sqlite3.connect(path)
    try:
        con.execute("PRAGMA journal_mode=OFF"); con.execute("PRAGMA synchronous=OFF")
        try:
            con.execute("CREATE VIRTUAL TABLE knowledge USING fts5(path UNINDEXED, chunk_no UNINDEXED, text)"); backend="sqlite_fts5"
        except sqlite3.OperationalError:
            con.execute("CREATE TABLE knowledge(path TEXT, chunk_no INTEGER, text TEXT)"); con.execute("CREATE INDEX knowledge_path_idx ON knowledge(path)"); backend="sqlite_plain"
        con.executemany("INSERT INTO knowledge(path,chunk_no,text) VALUES(?,?,?)",[(r["path"],int(r["chunk"]),r["text"]) for r in rows]); con.commit()
        if backend=="sqlite_fts5" and rows: con.execute("SELECT count(*) FROM knowledge WHERE knowledge MATCH ?",("PROJECT",)).fetchone()
        return backend
    finally: con.close()

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="\n") as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

def hook_enabled(repo):
    cp=git(repo,["config","--local","--get","core.hooksPath"],check=False)
    return cp.returncode==0 and cp.stdout.strip().replace("\\","/").rstrip("/")==".githooks"

def sync(repo,mode):
    managed=repo/MANAGED_REL; runtime=repo/RUNTIME_REL
    managed.mkdir(parents=True,exist_ok=True); runtime.mkdir(parents=True,exist_ok=True)
    entries,branch,head=snapshot(repo,mode); sd=digest(entries); old,old_chunks=previous(managed)
    rows=[]; files=[]; redactions=0; extracted=0; meta_only=0
    for e in entries:
        path=e["path"]; cls="full-content" if full_content(path) else "source-metadata"
        item={"path":path,"git_oid":e["oid"],"git_mode":e["git_mode"],"classification":cls}
        if cls!="full-content":
            item.update({"extraction":"metadata-only","sha256":None,"chunks":0}); files.append(item); continue
        prev=old.get(path)
        if prev and prev.get("git_oid")==e["oid"] and path in old_chunks:
            cached=old_chunks[path]; rows.extend(cached)
            item.update({"extraction":prev.get("extraction","cached"),"sha256":prev.get("sha256"),"chunks":len(cached)}); files.append(item); extracted+=1; continue
        data=read_blob(repo,mode,path); sha=hashlib.sha256(data).hexdigest(); text,extract=decode_text(path,data)
        if text is None:
            item.update({"extraction":extract,"sha256":sha,"chunks":0}); files.append(item); meta_only+=1; continue
        text,n=redact(text); redactions+=n; pieces=chunks(text)
        for i,piece in enumerate(pieces,1): rows.append({"path":path,"chunk":i,"source_git_oid":e["oid"],"text":piece})
        item.update({"extraction":extract,"sha256":sha,"chunks":len(pieces)}); files.append(item); extracted+=1
    hist=history(repo,500)
    for c in hist: rows.append({"path":f"git://commit/{c['commit']}","chunk":1,"source_git_oid":c["commit"],"text":f"{c['date']} {c['subject']}"})
    backend=build_db(runtime/"BIB_SEARCH.sqlite3",rows)
    write_jsonl(managed/"BIB_KNOWLEDGE_FALLBACK.jsonl",rows)
    roots=detect_bib_roots([e["path"] for e in entries])
    state={"schema_version":SCHEMA_VERSION,"mode":mode,"branch":branch,"head_observed_before_commit":head,"source_digest":sd,"source_file_count":len(entries),
           "full_content_file_count":sum(1 for x in files if x["classification"]=="full-content"),"source_metadata_file_count":sum(1 for x in files if x["classification"]=="source-metadata"),
           "extracted_file_count":extracted,"metadata_only_file_count":meta_only,"chunk_count":len(rows),"git_history_entries":len(hist),"secret_redactions":redactions,
           "primary_backend":backend,"fallback_backend":"git_grep_over_tracked_jsonl","managed_root":MANAGED_REL,"bib_roots_discovered":roots,
           "auto_sync_hook_enabled":hook_enabled(repo),"release_status":"KNOWLEDGE_INDEX_ONLY_NO_PRODUCTION_RELEASE"}
    write_json(managed/"BIB_CURRENT_STATE.json",state)
    write_json(managed/"BIB_MANIFEST.json",{"schema_version":SCHEMA_VERSION,"source_digest":sd,"files":files})
    write_json(managed/"BIB_DISCOVERED_KNOWLEDGE_ROOTS.json",{"schema_version":SCHEMA_VERSION,"managed_bib_root":MANAGED_REL,"discovered_existing_bib_roots":roots,
      "full_content_policy":["docs/**","configs/**","BIB/bib/knowledge/PKB-like roots","root-level knowledge text"],"source_metadata_policy":["tracked Phoenix code/scripts/tests fingerprinted by Git object id"],"binary_policy":"DOCX extracted with stdlib XML; PDF via optional pypdf, otherwise metadata/hash only"})
    write_jsonl(managed/"BIB_GIT_HISTORY.jsonl",hist)
    (managed/"README.md").write_text("# PHOENIX AUTO-SYNC BIB\n\nMachine-managed BIB. Authoritative repository knowledge is indexed/fingerprinted here. Do not hand-edit generated state files.\n",encoding="utf-8",newline="\n")
    (managed/"BIB_BASELINE.md").write_text(f"# PROJECT PHOENIX BIB CURRENT BASELINE\n\n- Branch: `{branch}`\n- HEAD observed before containing commit: `{head}`\n- Snapshot mode: `{mode}`\n- Knowledge source digest: `{sd}`\n- Source files fingerprinted: `{len(entries)}`\n- Full-content knowledge files: `{state['full_content_file_count']}`\n- Search chunks: `{len(rows)}`\n- Primary: `{backend}`\n- Fallback: `git grep`\n\nCurrentness is validated by source digest against the actual Git snapshot, avoiding a self-referential commit hash.\n",encoding="utf-8",newline="\n")
    (managed/"BIB_SYNC_EVIDENCE.txt").write_text("\n".join(["BIB_FULL_BACKFILL=PASS",f"BIB_SOURCE_DIGEST={sd}",f"BIB_SOURCE_FILES={len(entries)}",f"BIB_SEARCH_CHUNKS={len(rows)}",f"BIB_PRIMARY_BACKEND={backend}","BIB_FALLBACK_BACKEND=git_grep_over_tracked_jsonl",f"BIB_AUTO_SYNC={'ENABLED' if state['auto_sync_hook_enabled'] else 'PENDING_HOOK_ENABLE'}","BIB_SECRET_REDACTION=ENABLED",""]) ,encoding="utf-8",newline="\n")
    (runtime/".gitignore").write_text("*\n!.gitignore\n",encoding="utf-8",newline="\n")
    return state

def validate(repo,mode,require_hook=True):
    managed=repo/MANAGED_REL; state=json.loads((managed/"BIB_CURRENT_STATE.json").read_text(encoding="utf-8")); manifest=json.loads((managed/"BIB_MANIFEST.json").read_text(encoding="utf-8"))
    entries,_,_=snapshot(repo,mode); sd=digest(entries)
    if state.get("source_digest")!=sd or manifest.get("source_digest")!=sd: raise RuntimeError("BIB source digest is stale.")
    if int(state.get("source_file_count",-1))!=len(entries): raise RuntimeError("BIB source file count mismatch.")
    rows=[json.loads(x) for x in (managed/"BIB_KNOWLEDGE_FALLBACK.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(rows)!=int(state.get("chunk_count",-1)): raise RuntimeError("BIB fallback chunk count mismatch.")
    db=repo/RUNTIME_REL/"BIB_SEARCH.sqlite3"
    if not db.exists(): backend=build_db(db,rows)
    else: backend=state.get("primary_backend","unknown")
    con=sqlite3.connect(db)
    try:
        if backend=="sqlite_fts5": con.execute("SELECT count(*) FROM knowledge WHERE knowledge MATCH ?",("PROJECT",)).fetchone()
        else: con.execute("SELECT count(*) FROM knowledge").fetchone()
    finally: con.close()
    if shutil.which("git") is None: raise RuntimeError("Git fallback search engine unavailable.")
    hook=hook_enabled(repo)
    if require_hook and not hook: raise RuntimeError("BIB auto-sync hook is not enabled via core.hooksPath=.githooks")
    return {"digest":sd,"source_files":len(entries),"chunks":len(rows),"primary_backend":backend,"fallback_backend":"git_grep_over_tracked_jsonl","hook_enabled":hook}

def status(r):
    print("BIB_FULL_BACKFILL=PASS"); print("BIB_CURRENT_BASELINE=PASS"); print("BIB_KNOWLEDGE_INDEX=PASS")
    print(f"BIB_PRIMARY_BACKEND={r['primary_backend']}"); print(f"BIB_FALLBACK_BACKEND={r['fallback_backend']}")
    print("BIB_AUTO_SYNC=ENABLED" if r["hook_enabled"] else "BIB_AUTO_SYNC=DISABLED"); print("BIB_UP_TO_DATE=YES")
    print(f"BIB_SOURCE_DIGEST={r['digest']}"); print(f"BIB_SOURCE_FILES={r['source_files']}"); print(f"BIB_SEARCH_CHUNKS={r['chunks']}")

def search(repo,query,limit):
    db=repo/RUNTIME_REL/"BIB_SEARCH.sqlite3"; fallback=repo/MANAGED_REL/"BIB_KNOWLEDGE_FALLBACK.jsonl"
    if db.exists():
        try:
            con=sqlite3.connect(db); rows=con.execute("SELECT path,chunk_no,snippet(knowledge,2,'[',']',' … ',14) FROM knowledge WHERE knowledge MATCH ? LIMIT ?",(query,limit)).fetchall(); con.close()
            for p,c,s in rows: print(f"{p}#{c}: {s}")
            if rows: return 0
        except Exception: pass
    cp=git(repo,["grep","--no-index","-n","-i","-F","-m",str(limit),"-e",query,"--",str(fallback)],check=False)
    if cp.returncode in (0,1):
        if cp.stdout: print(cp.stdout.rstrip())
        return 0 if cp.returncode==0 else 1
    return 1

def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=["sync","validate","status","search"]); p.add_argument("--repo",default="."); p.add_argument("--mode",choices=["git-index","head"],default="head"); p.add_argument("--query",default=""); p.add_argument("--limit",type=int,default=20); p.add_argument("--allow-hook-disabled",action="store_true"); a=p.parse_args()
    repo=Path(a.repo).resolve()
    if a.command=="sync": sync(repo,a.mode); r=validate(repo,a.mode,not a.allow_hook_disabled); status(r); return 0
    if a.command in {"validate","status"}: status(validate(repo,a.mode,not a.allow_hook_disabled)); return 0
    if not a.query: raise SystemExit("--query required")
    return search(repo,a.query,a.limit)
if __name__=="__main__": raise SystemExit(main())
