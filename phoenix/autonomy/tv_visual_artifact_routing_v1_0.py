from pathlib import Path
VERSION="1.0.0"
VISUAL={".svg":10,".png":20,".jpg":30,".jpeg":30,".webp":35,".dxf":40,".dwg":45,".html":50,".htm":50,".gltf":55,".glb":56,".webm":60,".mp4":61,".mov":62,".avi":63,".pdf":70}
TECH={".json",".jsonl",".log",".txt",".md"}
TOK=("manifest","register","evidence","metadata","contract","state","summary","index")
DRAW=("site_plan","situatie","floor_plan","plattegrond","elevation","gevel","section","doorsnede","detail","foundation","fundering","structural","constructie","drawing","tekening")
def norm(v): return str(v or "").replace("\\","/").strip()
def suffix(v): return Path(norm(v)).suffix.casefold()
def is_visual_artifact(v): return suffix(v) in VISUAL
def is_technical_evidence(v):
    p=norm(v); n=Path(p).name.casefold()
    return suffix(p) in TECH or (any(t in n for t in TOK) and not is_visual_artifact(p))
def is_drawing_artifact(v):
    p=norm(v); n=Path(p).name.casefold()
    return suffix(p) in {".svg",".dxf",".dwg",".pdf"} and any(t in n for t in DRAW)
def priority(v):
    p=norm(v); return (VISUAL.get(suffix(p),999)- (5 if is_drawing_artifact(p) else 0),Path(p).name.casefold())
def order_presentable_artifacts(values):
    seen=[]; vals=[]
    for v in values:
        p=norm(v)
        if p and p not in seen: seen.append(p); vals.append(p)
    return sorted(vals,key=lambda p:(0 if is_visual_artifact(p) else 2 if is_technical_evidence(p) else 1,priority(p)))
def preferred_visual_artifact(values):
    for p in order_presentable_artifacts(values):
        if is_visual_artifact(p): return p
    return None
