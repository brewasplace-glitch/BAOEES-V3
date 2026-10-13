"""R14 diagnostic: union of planar axis-aligned wall strips clipped to room rectangles.
No deductions for other fixtures/stairs; NOT a formal usable-area measurement.
"""
import math


def _number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def _union_area(rectangles):
    if not rectangles:
        return 0.0
    xs = sorted({v for a, b, c, d in rectangles for v in (a, c)})
    area = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        intervals = sorted((b, d) for a, b, c, d in rectangles if a < x1 and c > x0)
        if not intervals:
            continue
        lo, hi = intervals[0]
        covered = 0.0
        for y0, y1 in intervals[1:]:
            if y0 > hi:
                covered += hi - lo
                lo, hi = y0, y1
            else:
                hi = max(hi, y1)
        covered += hi - lo
        area += (x1 - x0) * covered
    return area


def evaluate(layout):
    rows=[]
    warnings=[]
    for room in layout.get('rooms', []):
        rid=str(room.get('room_id'))
        if not all(_number(room.get(k)) for k in ('x','y','width','depth')) or room['width']<=0 or room['depth']<=0:
            rows.append({'room_id':rid,'status':'UNSUPPORTED_ROOM','reason':'INVALID_ROOM_GEOMETRY'})
            continue
        x0,y0=room['x'],room['y'];x1=x0+room['width'];y1=y0+room['depth']
        clipped=[];unsupported=[];matches=0
        for wall in layout.get('walls', []):
            if wall.get('storey_index') != room.get('storey_index'):
                continue
            fields=('x1','y1','x2','y2','thickness_m')
            if not all(_number(wall.get(k)) for k in fields) or wall['thickness_m']<=0:
                unsupported.append(str(wall.get('wall_key','UNKNOWN')))
                continue
            ax,ay,bx,by,t=(wall[k] for k in fields)
            if abs(ax-bx)<1e-8 and abs(ay-by)>1e-8:
                bounds=(ax-t/2,min(ay,by),ax+t/2,max(ay,by))
            elif abs(ay-by)<1e-8 and abs(ax-bx)>1e-8:
                bounds=(min(ax,bx),ay-t/2,max(ax,bx),ay+t/2)
            else:
                unsupported.append(str(wall.get('wall_key','UNKNOWN')))
                continue
            a=max(x0,bounds[0]);b=max(y0,bounds[1]);c=min(x1,bounds[2]);d=min(y1,bounds[3])
            if c>a and d>b:
                clipped.append((a,b,c,d));matches+=1
        gross=(x1-x0)*(y1-y0)
        overlap=_union_area(clipped)
        area=None if unsupported else gross-overlap
        target=room.get('target_area_m2')
        rows.append({'room_id':rid,'storey_index':room.get('storey_index'),
            'rectangle_m2':round(gross,5),'wall_overlap_union_m2':round(overlap,5),
            'provisional_clear_m2':None if area is None else round(area,5),
            'target_m2':target if _number(target) else None,
            'delta_to_target_m2':round(area-target,5) if area is not None and _number(target) else None,
            'overlap_wall_count':matches,'unsupported_wall_ids':unsupported,
            'status':'ESTIMATE_NOT_APPROVED' if area is not None else 'UNSUPPORTED_WALL_GEOMETRY'})
        if unsupported: warnings.append(rid+':UNSUPPORTED_WALL_GEOMETRY')
    return {'schema':'PHOENIX_R14_PROVISIONAL_NET_AREA_V1',
        'method':'AXIS_ALIGNED_ROOM_RECTANGLE_MINUS_UNION_CENTERED_WALL_STRIPS',
        'formal_net_usable_area_approved':False,
        'programme_acceptance':'OPEN_NO_APPROVED_TOLERANCE',
        'status':'DIAGNOSTIC_ONLY' if not warnings and all(r['status']=='ESTIMATE_NOT_APPROVED' for r in rows) else 'PARTIAL_UNSUPPORTED',
        'warnings':warnings,'room_count':len(rows),'rooms':rows}
