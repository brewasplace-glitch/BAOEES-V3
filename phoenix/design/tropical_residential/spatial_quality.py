from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Mapping, Sequence

R2_SCHEMA = "PHOENIX_REAL_ARCHITECTURAL_SPATIAL_QUALITY_V2"

PUBLIC = ("LIVING","DINING","KITCHEN","ENTRY","ENTRANCE","LOUNGE","FAMILY")
PRIVATE = ("BED","MASTER","PRIVATE","STUDY","OFFICE")
WET = ("BATH","WC","TOILET","SHOWER","LAUNDRY","WASH","UTILITY")
CIRC = ("CIRC","HALL","CORRIDOR","STAIR","LANDING","LOBBY","ENTRY","ENTRANCE")

def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d

def _storey(room):
    try:
        return int(room.get("storey_index") or 0)
    except (TypeError, ValueError):
        return 0

def _label(room):
    return str(room.get("zone") or room.get("name") or room.get("room_name") or room.get("room_id") or "UNSPECIFIED").upper()

def _box(room):
    x,y=_f(room.get("x")),_f(room.get("y"))
    return x,y,x+max(0.0,_f(room.get("width"))),y+max(0.0,_f(room.get("depth")))

def _overlap(a1,a2,b1,b2):
    return max(0.0,min(a2,b2)-max(a1,b1))

def _adjacent(a,b,tol=0.25):
    if _storey(a)!=_storey(b):
        return False
    ax1,ay1,ax2,ay2=_box(a); bx1,by1,bx2,by2=_box(b)
    hgap=round(max(0.0,max(bx1-ax2,ax1-bx2)),6)
    vgap=round(max(0.0,max(by1-ay2,ay1-by2)),6)
    return (hgap<=tol and _overlap(ay1,ay2,by1,by2)>=0.40) or (vgap<=tol and _overlap(ax1,ax2,bx1,bx2)>=0.40)

def _category(label):
    if any(t in label for t in WET): return "WET"
    if any(t in label for t in CIRC): return "CIRCULATION"
    if any(t in label for t in PRIVATE): return "PRIVATE"
    if any(t in label for t in PUBLIC): return "PUBLIC"
    return "OTHER"

def _graph(rooms):
    g={i:set() for i in range(len(rooms))}
    for i,a in enumerate(rooms):
        for j in range(i+1,len(rooms)):
            if _adjacent(a,rooms[j]):
                g[i].add(j); g[j].add(i)
    return g

def _components(g):
    unseen=set(g); out=[]
    while unseen:
        start=next(iter(unseen)); unseen.remove(start)
        comp={start}; q=deque([start])
        while q:
            n=q.popleft()
            for nxt in g[n]:
                if nxt in unseen:
                    unseen.remove(nxt); comp.add(nxt); q.append(nxt)
        out.append(comp)
    return out

def _shortest(g,start,goal):
    if start==goal: return 0
    seen={start}; q=deque([(start,0)])
    while q:
        n,d=q.popleft()
        for nxt in g[n]:
            if nxt==goal: return d+1
            if nxt not in seen:
                seen.add(nxt); q.append((nxt,d+1))
    return None

def _nearest_room(opening,rooms):
    ox,oy=_f(opening.get("x")),_f(opening.get("y"))
    best=None; bestd=None
    for i,r in enumerate(rooms):
        x1,y1,x2,y2=_box(r); cx=(x1+x2)/2; cy=(y1+y2)/2
        d=(cx-ox)**2+(cy-oy)**2
        if bestd is None or d<bestd:
            bestd=d; best=i
    return best

def evaluate_spatial_relationships(layout: Mapping[str,Any], variant: Mapping[str,Any]|None=None) -> dict[str,Any]:
    variant=dict(variant or {})
    rooms=list(layout.get("rooms") or [])
    openings=list(layout.get("openings") or [])
    g=_graph(rooms); comps=_components(g) if g else []
    n=len(rooms)
    degrees=[len(g[i]) for i in range(n)]
    largest=max((len(c) for c in comps),default=0)
    connectivity=largest/max(1,n)
    isolated=sum(1 for d in degrees if d==0)
    isolated_ratio=isolated/max(1,n)
    avg_degree=sum(degrees)/max(1,n)
    cats=[_category(_label(r)) for r in rooms]
    circ=[i for i,c in enumerate(cats) if c=="CIRCULATION"]
    wet=[i for i,c in enumerate(cats) if c=="WET"]
    private=[i for i,c in enumerate(cats) if c=="PRIVATE"]
    public=[i for i,c in enumerate(cats) if c=="PUBLIC"]

    if circ:
        circulation=sum(min(1.0,degrees[i]/2.0) for i in circ)/len(circ)
    else:
        circulation=min(1.0,avg_degree/2.0)

    if len(wet)>=2:
        linked=sum(1 for i in wet if any(j in wet for j in g[i]))
        wet_cluster=linked/len(wet)
    elif len(wet)==1:
        wet_cluster=0.75
    else:
        wet_cluster=0.50

    conflicts=sum(1 for i in public for j in g[i] if j in private)
    privacy=max(0.0,1.0-conflicts/max(1,len(public)*max(1,len(private))))

    routes=[]
    for i in public:
        for j in private:
            d=_shortest(g,i,j)
            if d is not None: routes.append(d)
    avg_route=sum(routes)/len(routes) if routes else None
    route_eff=max(0.0,min(1.0,1.0-max(0.0,(avg_route or 6)-3.0)/5.0)) if routes else connectivity*0.6

    hosts=[]
    for o in openings:
        h=_nearest_room(o,rooms)
        if h is not None: hosts.append(h)
    counts={}
    for h in hosts: counts[h]=counts.get(h,0)+1
    opening_coverage=len(counts)/max(1,n)
    if counts:
        total=sum(counts.values())
        concentration=sum((c/total)**2 for c in counts.values())
        opening_distribution=max(0.0,min(1.0,1.0-concentration))
    else:
        opening_distribution=0.0

    max_edges=max(1,n*(n-1)/2)
    edge_count=sum(degrees)/2
    density=edge_count/max_edges
    target=0.22
    density_quality=max(0.0,1.0-abs(density-target)/target)

    subs={
        "connectivity":connectivity,
        "circulation":circulation,
        "privacy":privacy,
        "wet_clustering":wet_cluster,
        "route_efficiency":route_eff,
        "opening_coverage":opening_coverage,
        "opening_distribution":opening_distribution,
        "graph_density_quality":density_quality,
    }
    weights={"connectivity":0.18,"circulation":0.16,"privacy":0.14,"wet_clustering":0.10,"route_efficiency":0.12,"opening_coverage":0.12,"opening_distribution":0.10,"graph_density_quality":0.08}
    score=100.0*sum(subs[k]*weights[k] for k in weights)

    hard=[]; warnings=[]
    if n and connectivity<0.50: hard.append("SPATIAL_GRAPH_MAJORITY_DISCONNECTED")
    if isolated_ratio>0.35: hard.append("EXCESSIVE_ISOLATED_ROOMS")
    if privacy<0.45: warnings.append("HIGH_PUBLIC_PRIVATE_ADJACENCY")
    if opening_coverage<0.40: warnings.append("LOW_OPENING_COVERAGE")
    if circulation<0.45: warnings.append("WEAK_CIRCULATION_CONNECTIVITY")

    return {
        "schema":R2_SCHEMA,
        "variant_id":str(variant.get("variant_id") or ""),
        "strategy":str(variant.get("strategy") or "").upper(),
        "score":round(score,2),
        "hard_pass":not hard,
        "hard_failures":hard,
        "warnings":warnings,
        "subscores":{k:round(v*100.0,2) for k,v in subs.items()},
        "metrics":{
            "room_count":n,
            "edge_count":int(edge_count),
            "average_degree":round(avg_degree,3),
            "graph_density":round(density,4),
            "component_count":len(comps),
            "largest_component_ratio":round(connectivity,4),
            "isolated_room_count":isolated,
            "isolated_room_ratio":round(isolated_ratio,4),
            "circulation_room_count":len(circ),
            "wet_room_count":len(wet),
            "public_room_count":len(public),
            "private_room_count":len(private),
            "privacy_conflict_edges":conflicts,
            "average_public_private_route":round(avg_route,3) if avg_route is not None else None,
            "rooms_with_openings":len(counts),
            "opening_coverage":round(opening_coverage,4),
        },
        "release_status":"CONCEPT_SPATIAL_QA_ONLY_NOT_FOR_CONSTRUCTION",
    }

def evaluate_variant_set_spatial_quality(items: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    rows=[dict(x) for x in items]
    scores=[float(x.get("score") or 0.0) for x in rows]
    hard=[]
    if len(rows)!=5: hard.append(f"VARIANT_COUNT_{len(rows)}_NE_5")
    if any(not x.get("hard_pass") for x in rows): hard.append("ONE_OR_MORE_VARIANTS_FAIL_SPATIAL_QA")
    ranking=[x.get("variant_id") for x in sorted(rows,key=lambda r:float(r.get("score") or 0.0),reverse=True)]
    return {
        "schema":"PHOENIX_REAL_ARCHITECTURAL_VARIANT_SET_SPATIAL_QUALITY_V2",
        "variant_count":len(rows),
        "minimum_score":round(min(scores),2) if scores else 0.0,
        "maximum_score":round(max(scores),2) if scores else 0.0,
        "average_score":round(sum(scores)/max(1,len(scores)),2),
        "score_spread":round(max(scores)-min(scores),2) if scores else 0.0,
        "ranking_best_to_worst":ranking,
        "hard_pass":not hard,
        "hard_failures":hard,
        "variants":rows,
        "release_status":"CONCEPT_SPATIAL_QA_ONLY_NOT_FOR_CONSTRUCTION",
    }

def write_spatial_quality_report(output_dir: Path, report: Mapping[str,Any]) -> dict[str,str]:
    output_dir.mkdir(parents=True,exist_ok=True)
    jp=output_dir/"architectural_spatial_quality_report_v2.json"
    mp=output_dir/"architectural_spatial_quality_report_v2.md"
    jp.write_text(json.dumps(dict(report),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=[
        "# Phoenix Architectural Spatial Quality Report V2","",
        f"- Variant count: {report.get('variant_count')}",
        f"- Minimum score: {report.get('minimum_score')}",
        f"- Maximum score: {report.get('maximum_score')}",
        f"- Average score: {report.get('average_score')}",
        f"- Score spread: {report.get('score_spread')}",
        f"- Ranking: {', '.join(report.get('ranking_best_to_worst') or [])}",
        f"- Hard pass: {report.get('hard_pass')}","",
    ]
    for row in report.get("variants") or []:
        lines.append(f"- Variant {row.get('variant_id')}: score={row.get('score')} warnings={row.get('warnings')}")
    mp.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return {"json":str(jp),"markdown":str(mp)}
