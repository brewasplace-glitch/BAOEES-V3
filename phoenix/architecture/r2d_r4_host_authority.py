from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


WINDOW_HOST_AUTHORITY_KIND = "EXTERIOR_WINDOW_HOST"
WINDOW_HOST_PROOF = "EXACT_GLOBAL_ROOM_UNION_EXTERIOR_BOUNDARY_WINDOW_HOST"


def _merge_intervals(intervals: Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
    vals=[]
    for lo,hi in intervals:
        lo=float(lo);hi=float(hi)
        if hi<=lo:
            continue
        vals.append((lo,hi))
    vals.sort()
    out=[]
    for lo,hi in vals:
        if not out or lo>out[-1][1]+1e-6:
            out.append([lo,hi])
        else:
            out[-1][1]=max(out[-1][1],hi)
    return [(a,b) for a,b in out]


def _subtract_interval(lo: float, hi: float, covers: Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
    pieces=[(float(lo),float(hi))]
    for clo,chi in _merge_intervals(covers):
        nxt=[]
        for a,b in pieces:
            if chi<=a+1e-6 or clo>=b-1e-6:
                nxt.append((a,b));continue
            if clo>a+1e-6:
                nxt.append((a,min(b,clo)))
            if chi<b-1e-6:
                nxt.append((max(a,chi),b))
        pieces=nxt
    return [(a,b) for a,b in pieces if b-a>0.20]


def exterior_segments_for_room(rooms: List[List[Any]], room_name: str) -> List[Dict[str, Any]]:
    target=next((r for r in rooms if str(r[0])==str(room_name)),None)
    if target is None:
        return []
    _,x,y,w,h,*_=target
    x0,y0,x1,y1=map(float,(x,y,x+w,y+h))
    sides=[('H',y0,x0,x1,'S'),('H',y1,x0,x1,'N'),('V',x0,y0,y1,'W'),('V',x1,y0,y1,'E')]
    out=[]
    eps=1e-6
    for ori,coord,lo,hi,side in sides:
        covers=[]
        for r in rooms:
            if str(r[0])==str(room_name):
                continue
            _,rx,ry,rw,rh,*_=r
            rx0,ry0,rx1,ry1=map(float,(rx,ry,rx+rw,ry+rh))
            if ori=='H':
                if (abs(coord-y0)<eps and abs(ry1-coord)<eps) or (abs(coord-y1)<eps and abs(ry0-coord)<eps):
                    a,b=max(lo,rx0),min(hi,rx1)
                    if b-a>eps:
                        covers.append((a,b))
            else:
                if (abs(coord-x0)<eps and abs(rx1-coord)<eps) or (abs(coord-x1)<eps and abs(rx0-coord)<eps):
                    a,b=max(lo,ry0),min(hi,ry1)
                    if b-a>eps:
                        covers.append((a,b))
        for a,b in _subtract_interval(lo,hi,covers):
            out.append({'orientation':ori,'coord':float(coord),'lo':float(a),'hi':float(b),'side':side})
    return out


def _opening_type(opening: Dict[str, Any]) -> str:
    typ=str(opening.get('opening_type') or '').upper().strip()
    if typ:
        return typ
    kind=str(opening.get('kind') or '').lower().strip()
    oid=str(opening.get('opening_id') or '').upper()
    if kind=='window' or '-W' in oid:
        return 'WINDOW'
    return typ


def _candidate_room_names(opening: Dict[str, Any], rooms: List[List[Any]]) -> List[str]:
    out=[]
    src=opening.get('source_room')
    if src:
        out.append(str(src))
    for rn in opening.get('exterior_inside_rooms',[]) or []:
        if str(rn) not in out:
            out.append(str(rn))
    if out:
        return out
    # Strict geometric fallback: only rooms for which the whole opening fits on a proven exposed segment.
    cx,cy=map(float,opening['center_xy']);ww=float(opening['width_m']);ori=opening['orientation']
    tangent=cx if ori=='H' else cy
    normal=cy if ori=='H' else cx
    for r in rooms:
        rn=str(r[0])
        for seg in exterior_segments_for_room(rooms,rn):
            if seg['orientation']!=ori:
                continue
            if abs(normal-float(seg['coord']))>0.08:
                continue
            if tangent-ww/2>=float(seg['lo'])-0.05 and tangent+ww/2<=float(seg['hi'])+0.05:
                out.append(rn);break
    return out


def resolve_exterior_window_host(
    code: str,
    opening: Dict[str, Any],
    rooms: List[List[Any]],
    zmin: float,
    zmax: float,
    wall_thickness_m: float = 0.16,
) -> Tuple[Dict[str, Any] | None, Dict[str, Any]]:
    if _opening_type(opening)!='WINDOW':
        return None, {'reason':'NOT_WINDOW'}
    proof_token=str(opening.get('exterior_boundary_proof') or '')
    if proof_token and 'PASS' not in proof_token and 'EXTERIOR' not in proof_token:
        return None, {'reason':'WINDOW_LACKS_EXTERIOR_RULE_ENGINE_PROOF','proof_token':proof_token}
    rooms_by_name={str(r[0]):r for r in rooms}
    candidates=_candidate_room_names(opening,rooms)
    if len(candidates)!=1:
        return None, {'reason':'WINDOW_EXTERIOR_ROOM_AMBIGUOUS','candidate_rooms':candidates}
    room_name=candidates[0]
    if room_name not in rooms_by_name:
        return None, {'reason':'ROOM_NOT_FOUND','room':room_name}
    segs=exterior_segments_for_room(rooms,room_name)
    cx,cy=map(float,opening['center_xy']);ww=float(opening['width_m']);ori=opening['orientation']
    tangent=cx if ori=='H' else cy
    normal=cy if ori=='H' else cx
    matches=[]
    for seg in segs:
        if seg['orientation']!=ori:
            continue
        delta=abs(normal-float(seg['coord']))
        fits=tangent-ww/2>=float(seg['lo'])-0.05 and tangent+ww/2<=float(seg['hi'])+0.05
        matches.append((not fits,delta,seg))
    matches.sort(key=lambda x:(x[0],x[1],-(x[2]['hi']-x[2]['lo'])))
    if not matches or matches[0][0] or matches[0][1]>0.08:
        return None, {
            'reason':'WINDOW_NOT_ON_EXACT_GLOBAL_ROOM_UNION_EXTERIOR_BOUNDARY',
            'room':room_name,
            'segments':segs,
        }
    seg=dict(matches[0][2])
    # Local wall only: enough tangential solid wall to make jambs, while full-storey height
    # provides sill and head. Never synthesize an entire facade.
    desired_margin=0.24
    win_lo=tangent-ww/2;win_hi=tangent+ww/2
    plo=max(float(seg['lo']),win_lo-desired_margin)
    phi=min(float(seg['hi']),win_hi+desired_margin)
    left_margin=win_lo-plo;right_margin=phi-win_hi
    if left_margin+right_margin<0.18 or max(left_margin,right_margin)<0.10:
        return None, {
            'reason':'EXTERIOR_SEGMENT_LACKS_WINDOW_JAMB_CAPACITY',
            'room':room_name,'segment':seg,'window_span':[win_lo,win_hi],
            'host_candidate':[plo,phi],'left_margin':left_margin,'right_margin':right_margin,
        }
    oid=str(opening['opening_id'])
    spec={
        'orientation':ori,'coord':float(seg['coord']),'lo':float(plo),'hi':float(phi),
        'wall_id':f'PHX_R2D_R4_EXT_WINDOW_WALL_{code}_{oid.replace("-","_")}',
        'variant':code,'storey':int(opening['storey']),'level':opening['level'],
        'thickness_m':float(wall_thickness_m),'zmin':float(zmin),'zmax':float(zmax),
        'room_from':room_name,'room_to':'OUTSIDE','derived_for_opening_id':oid,
        'authority_kind':WINDOW_HOST_AUTHORITY_KIND,
        'proof':WINDOW_HOST_PROOF,'full_exterior_segment':seg,
        'repair_reason':opening.get('repair_reason'),
    }
    return spec, {
        'reason':'EXTERIOR_WINDOW_BOUNDARY_PROVEN','room':room_name,'segment':seg,
        'window_host':spec,'rule_engine_proof':proof_token,
    }
