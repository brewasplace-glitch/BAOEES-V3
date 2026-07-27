"""Central semantic and geometric project model for Project Phoenix.

The module creates one deterministic model for the existing mosque, the
7 x 10 m two-storey extension, building interfaces, site, parcel and 225-space
parking environment. All outputs are concept-stage data.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import zipfile
from pathlib import Path
from typing import Any, Mapping

FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
STATUS = 'CONCEPT MODEL - NOT FOR SUBMISSION OR EXECUTION'


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode('utf-8')).hexdigest()


def polygon_area(points: list[list[float]]) -> float:
    return abs(sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )) / 2.0


def bbox_polygon(points: list[list[float]]) -> list[float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), 0.0, max(xs), max(ys), 0.0]


def cuboid_bbox(x: float, y: float, z: float, width: float, depth: float, height: float) -> list[float]:
    return [x, y, z, x + width, y + depth, z + height]


def point_in_rect(point: list[float], rect: list[float], tolerance: float = 1e-9) -> bool:
    return rect[0] - tolerance <= point[0] <= rect[3] + tolerance and rect[1] - tolerance <= point[1] <= rect[4] + tolerance


class CentralGeometricProjectModelEngine:
    VERSION = '1.0.0'

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = dict(config)

    def build(self) -> dict[str, Any]:
        objects: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []
        levels = [dict(item) for item in self.config['levels']]

        def add(obj: dict[str, Any]) -> None:
            if 'status' not in obj:
                obj['status'] = STATUS
            objects.append(obj)

        site = self.config['site']['polygon']
        parcel = self.config['site']['parcel_polygon']
        add({'id': 'SITE-001', 'type': 'site', 'name': 'Projectomgeving', 'geometry': {'kind': 'polygon', 'points': site}, 'bbox': bbox_polygon(site)})
        add({'id': 'PARCEL-001', 'type': 'parcel', 'name': 'Conceptperceel', 'geometry': {'kind': 'polygon', 'points': parcel}, 'bbox': bbox_polygon(parcel)})

        for building_key in ('existing_building', 'extension'):
            item = self.config[building_key]
            add({
                'id': item['id'], 'type': 'building', 'subtype': building_key,
                'name': item['name'], 'geometry': {'kind': 'polygon', 'points': item['footprint']},
                'bbox': bbox_polygon(item['footprint']), 'storeys': item['storeys'],
            })
            relationships.append({'id': f'REL-{item["id"]}-SITE', 'type': 'contained_in', 'source': item['id'], 'target': 'SITE-001'})

        c = self.config['construction']
        storey_h = c['storey_height_m']
        slab_t = c['slab_thickness_m']
        ext_t = c['external_wall_thickness_m']
        int_t = c['internal_wall_thickness_m']

        for level in levels[:2]:
            level_id = level['id']
            z = level['elevation_m']
            for building_key in ('existing_building', 'extension'):
                b = self.config[building_key]
                xs = [p[0] for p in b['footprint']]
                ys = [p[1] for p in b['footprint']]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                slab_id = f'SLAB-{b["id"]}-{level_id}'
                add({
                    'id': slab_id, 'type': 'slab', 'subtype': 'floor', 'level_id': level_id,
                    'building_id': b['id'], 'geometry': {'kind': 'cuboid', 'origin': [x0, y0, z], 'size': [x1-x0, y1-y0, slab_t]},
                    'bbox': cuboid_bbox(x0, y0, z, x1-x0, y1-y0, slab_t),
                })
                relationships.extend([
                    {'id': f'REL-{slab_id}-LEVEL', 'type': 'contained_in_level', 'source': slab_id, 'target': level_id},
                    {'id': f'REL-{slab_id}-BLD', 'type': 'part_of', 'source': slab_id, 'target': b['id']},
                ])

        # Roof slabs.
        for building_key in ('existing_building', 'extension'):
            b = self.config[building_key]
            xs = [p[0] for p in b['footprint']]
            ys = [p[1] for p in b['footprint']]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            roof_id = f'ROOF-{b["id"]}'
            add({'id': roof_id, 'type': 'slab', 'subtype': 'roof', 'level_id': 'LRF', 'building_id': b['id'], 'geometry': {'kind': 'cuboid', 'origin': [x0, y0, 6.4], 'size': [x1-x0, y1-y0, c['roof_thickness_m']]}, 'bbox': cuboid_bbox(x0, y0, 6.4, x1-x0, y1-y0, c['roof_thickness_m'])})
            relationships.append({'id': f'REL-{roof_id}-BLD', 'type': 'part_of', 'source': roof_id, 'target': b['id']})

        wall_specs: list[tuple[str, str, float, float, float, float, float, str]] = []
        # Existing outer envelope with the east connection zone removed between y=2 and y=12.
        base_existing = [
            ('N', 0, 14, 12, 14, ext_t), ('S', 0, 0, 12, 0, ext_t), ('W', 0, 0, 0, 14, ext_t),
            ('E-S', 12, 0, 12, 2, ext_t), ('E-N', 12, 12, 12, 14, ext_t),
        ]
        base_extension = [('N', 12, 12, 19, 12, ext_t), ('S', 12, 2, 19, 2, ext_t), ('E', 19, 2, 19, 12, ext_t)]
        internal_existing = [('I1', 4, 0.2, 4, 13.8, int_t), ('I2', 4, 7, 11.8, 7, int_t), ('I3', 8, 0.2, 8, 7, int_t)]
        internal_extension = [('I1', 15.5, 2.2, 15.5, 11.8, int_t), ('I2', 12.2, 7, 18.8, 7, int_t)]
        for level in levels[:2]:
            for code, x1, y1, x2, y2, thickness in base_existing + internal_existing:
                wall_specs.append((f'WALL-EX-{level["id"]}-{code}', level['id'], x1, y1, x2, y2, thickness, 'BLD-EXISTING'))
            for code, x1, y1, x2, y2, thickness in base_extension + internal_extension:
                wall_specs.append((f'WALL-NEW-{level["id"]}-{code}', level['id'], x1, y1, x2, y2, thickness, 'BLD-EXTENSION'))

        wall_index: dict[str, dict[str, Any]] = {}
        for wall_id, level_id, x1, y1, x2, y2, thickness, building_id in wall_specs:
            z = next(item['elevation_m'] for item in levels if item['id'] == level_id) + slab_t
            length = math.hypot(x2-x1, y2-y1)
            bbox = [min(x1,x2)-thickness/2, min(y1,y2)-thickness/2, z, max(x1,x2)+thickness/2, max(y1,y2)+thickness/2, z+storey_h-slab_t]
            obj = {'id': wall_id, 'type': 'wall', 'subtype': 'external' if thickness == ext_t else 'internal', 'level_id': level_id, 'building_id': building_id, 'geometry': {'kind': 'wall_segment', 'start': [x1,y1,z], 'end': [x2,y2,z], 'thickness_m': thickness, 'height_m': storey_h-slab_t}, 'length_m': round(length,3), 'bbox': bbox}
            add(obj); wall_index[wall_id] = obj
            relationships.extend([
                {'id': f'REL-{wall_id}-LEVEL', 'type': 'contained_in_level', 'source': wall_id, 'target': level_id},
                {'id': f'REL-{wall_id}-BLD', 'type': 'part_of', 'source': wall_id, 'target': building_id},
            ])

        # Spaces are explicit semantic polygons.
        spaces = [
            ('SP-L00-01','L00','Entree en verkeersruimte',[[0.2,0.2],[3.8,0.2],[3.8,6.8],[0.2,6.8]],'BLD-EXISTING'),
            ('SP-L00-02','L00','Gebedsruimte heren',[[4.2,7.2],[11.8,7.2],[11.8,13.8],[4.2,13.8]],'BLD-EXISTING'),
            ('SP-L00-03','L00','Ontmoeting en conferentie',[[4.2,0.2],[7.8,0.2],[7.8,6.8],[4.2,6.8]],'BLD-EXISTING'),
            ('SP-L00-04','L00','Wasruimte en toiletten',[[8.2,0.2],[11.8,0.2],[11.8,6.8],[8.2,6.8]],'BLD-EXISTING'),
            ('SP-L00-05','L00','Uitbreiding multifunctioneel west',[[12.2,2.2],[15.3,2.2],[15.3,11.8],[12.2,11.8]],'BLD-EXTENSION'),
            ('SP-L00-06','L00','Uitbreiding multifunctioneel oost',[[15.7,2.2],[18.8,2.2],[18.8,11.8],[15.7,11.8]],'BLD-EXTENSION'),
            ('SP-L01-01','L01','Gebedsruimte dames',[[0.2,7.2],[11.8,7.2],[11.8,13.8],[0.2,13.8]],'BLD-EXISTING'),
            ('SP-L01-02','L01','Kantine en ontmoeting',[[0.2,0.2],[3.8,0.2],[3.8,6.8],[0.2,6.8]],'BLD-EXISTING'),
            ('SP-L01-03','L01','Leslokaal 1',[[4.2,0.2],[7.8,0.2],[7.8,6.8],[4.2,6.8]],'BLD-EXISTING'),
            ('SP-L01-04','L01','Leslokaal 2 en sanitair',[[8.2,0.2],[11.8,0.2],[11.8,6.8],[8.2,6.8]],'BLD-EXISTING'),
            ('SP-L01-05','L01','Uitbreiding les en gebed west',[[12.2,2.2],[15.3,2.2],[15.3,11.8],[12.2,11.8]],'BLD-EXTENSION'),
            ('SP-L01-06','L01','Uitbreiding les en gebed oost',[[15.7,2.2],[18.8,2.2],[18.8,11.8],[15.7,11.8]],'BLD-EXTENSION'),
        ]
        for sid, level_id, name, points, building_id in spaces:
            obj={'id':sid,'type':'space','name':name,'level_id':level_id,'building_id':building_id,'geometry':{'kind':'polygon','points':points},'area_m2':round(polygon_area(points),2),'bbox':bbox_polygon(points)}
            add(obj); relationships.extend([
                {'id':f'REL-{sid}-LEVEL','type':'contained_in_level','source':sid,'target':level_id},
                {'id':f'REL-{sid}-BLD','type':'part_of','source':sid,'target':building_id},
            ])

        # Stair and interface connections.
        add({'id':'STAIR-001','type':'stair','name':'Hoofdtrap','level_id':'L00','connects_levels':['L00','L01'],'geometry':{'kind':'stair_flight','origin':[1.0,1.0,0.25],'width_m':1.2,'run_m':4.0,'rise_m':2.95,'steps':18},'bbox':[1.0,1.0,0.25,2.2,5.0,3.2]})
        relationships.extend([
            {'id':'REL-STAIR-L00','type':'connects_level','source':'STAIR-001','target':'L00'},
            {'id':'REL-STAIR-L01','type':'connects_level','source':'STAIR-001','target':'L01'},
        ])
        connection_specs = [
            ('CONN-001','L00','Zuidelijke aansluiting bestaand-nieuw',[12.0,2.0,0.25]),
            ('CONN-002','L00','Noordelijke aansluiting bestaand-nieuw',[12.0,12.0,0.25]),
            ('CONN-003','L01','Verdiepingsvloeraansluiting',[12.0,7.0,3.2]),
            ('CONN-004','LRF','Dakaansluiting',[12.0,7.0,6.4]),
        ]
        for cid, level_id, name, point in connection_specs:
            add({'id':cid,'type':'connection','subtype':'existing_to_extension','name':name,'level_id':level_id,'geometry':{'kind':'point','point':point},'bbox':[point[0],point[1],point[2],point[0],point[1],point[2]]})
            relationships.extend([
                {'id':f'REL-{cid}-EX','type':'connects','source':cid,'target':'BLD-EXISTING'},
                {'id':f'REL-{cid}-NEW','type':'connects','source':cid,'target':'BLD-EXTENSION'},
            ])

        # Openings hosted by explicit wall IDs.
        openings = [
            ('DOOR-001','door','L00','WALL-EX-L00-S',2.0,1.2,2.3),
            ('DOOR-002','door','L00','WALL-NEW-L00-E',4.0,1.2,2.3),
            ('DOOR-003','door','L00','WALL-EX-L00-I1',3.0,1.0,2.2),
            ('DOOR-004','door','L00','WALL-NEW-L00-I1',2.0,1.0,2.2),
            ('DOOR-005','door','L01','WALL-EX-L01-I1',3.0,1.0,2.2),
            ('DOOR-006','door','L01','WALL-NEW-L01-I1',2.0,1.0,2.2),
            ('WINDOW-001','window','L00','WALL-EX-L00-N',2.0,1.8,1.4),
            ('WINDOW-002','window','L00','WALL-EX-L00-N',7.0,1.8,1.4),
            ('WINDOW-003','window','L00','WALL-EX-L00-W',5.0,1.5,1.4),
            ('WINDOW-004','window','L00','WALL-NEW-L00-N',2.0,1.8,1.4),
            ('WINDOW-005','window','L00','WALL-NEW-L00-E',6.0,1.8,1.4),
            ('WINDOW-006','window','L01','WALL-EX-L01-N',2.0,1.8,1.4),
            ('WINDOW-007','window','L01','WALL-EX-L01-N',7.0,1.8,1.4),
            ('WINDOW-008','window','L01','WALL-EX-L01-W',5.0,1.5,1.4),
            ('WINDOW-009','window','L01','WALL-NEW-L01-N',2.0,1.8,1.4),
            ('WINDOW-010','window','L01','WALL-NEW-L01-E',6.0,1.8,1.4),
        ]
        for oid, kind, level_id, host, offset, width, height in openings:
            host_obj=wall_index[host]
            add({'id':oid,'type':'opening','subtype':kind,'level_id':level_id,'host_id':host,'offset_m':offset,'width_m':width,'height_m':height,'geometry':{'kind':'hosted_opening','host_id':host,'offset_m':offset,'width_m':width,'height_m':height},'bbox':host_obj['bbox']})
            relationships.append({'id':f'REL-{oid}-HOST','type':'hosted_by','source':oid,'target':host})

        # Parking zones and all 225 individual parking bays.
        bay_w=self.config['parking_bay']['width_m']; bay_l=self.config['parking_bay']['length_m']; gap=self.config['parking_bay']['gap_m']
        parking_bay_count=0
        for zone in self.config['parking_zones']:
            rows=math.ceil(zone['spaces']/zone['columns'])
            ox,oy=zone['origin']
            zone_w=zone['columns']*(bay_w+gap)-gap
            zone_h=rows*(bay_l+gap)-gap
            add({'id':zone['id'],'type':'parking_zone','name':zone['name'],'space_count':zone['spaces'],'geometry':{'kind':'rectangle','origin':[ox,oy,0.0],'size':[zone_w,zone_h,0.0]},'bbox':[ox,oy,0.0,ox+zone_w,oy+zone_h,0.0]})
            relationships.append({'id':f'REL-{zone["id"]}-SITE','type':'contained_in','source':zone['id'],'target':'SITE-001'})
            for index in range(zone['spaces']):
                row=index//zone['columns']; col=index%zone['columns']
                x=ox+col*(bay_w+gap); y=oy+row*(bay_l+gap)
                bay_id=f'BAY-{zone["id"]}-{index+1:03d}'
                add({'id':bay_id,'type':'parking_bay','zone_id':zone['id'],'sequence':index+1,'geometry':{'kind':'rectangle','origin':[x,y,0.0],'size':[bay_w,bay_l,0.0]},'bbox':[x,y,0.0,x+bay_w,y+bay_l,0.0]})
                relationships.append({'id':f'REL-{bay_id}-ZONE','type':'part_of','source':bay_id,'target':zone['id']})
                parking_bay_count += 1

        model = {
            'schema_version': 'phoenix.central-geometric-project-model-result/1.0',
            'engine_version': self.VERSION,
            'model_id': self.config['model_id'],
            'project_id': self.config['project_id'],
            'pilot_id': self.config['pilot_id'],
            'status': self.config['status'],
            'units': self.config['units'],
            'coordinate_system': self.config['coordinate_system'],
            'levels': levels,
            'objects': sorted(objects, key=lambda item:item['id']),
            'relationships': sorted(relationships, key=lambda item:item['id']),
            'professional_blockers': self.config['professional_blockers'],
            'req107_status': self.config['req107_status'],
        }
        model['model_fingerprint_sha256'] = fingerprint(model)
        checks = self._checks(model, parking_bay_count)
        model['validation'] = {
            'check_count': len(checks),
            'checks_passed': sum(1 for item in checks if item['passed']),
            'all_checks_passed': all(item['passed'] for item in checks),
        }
        return {'model': model, 'checks': checks}

    def _checks(self, model: Mapping[str, Any], parking_bay_count: int) -> list[dict[str, Any]]:
        objects=model['objects']; ids=[item['id'] for item in objects]
        types={name:sum(1 for item in objects if item['type']==name) for name in set(item['type'] for item in objects)}
        ext=self.config['extension']; ex=self.config['existing_building']
        host_ids={item['id'] for item in objects if item['type']=='wall'}
        checks=[
            ('GEO-001','unique_object_ids',len(ids)==len(set(ids)),len(ids)),
            ('GEO-002','levels_defined',len(model['levels'])==3,len(model['levels'])),
            ('GEO-003','existing_footprint_area',abs(polygon_area(ex['footprint'])-168.0)<1e-9,polygon_area(ex['footprint'])),
            ('GEO-004','extension_width',abs(ext['width_m']-7.0)<1e-9,ext['width_m']),
            ('GEO-005','extension_length',abs(ext['length_m']-10.0)<1e-9,ext['length_m']),
            ('GEO-006','extension_floor_area',abs(polygon_area(ext['footprint'])-70.0)<1e-9,polygon_area(ext['footprint'])),
            ('GEO-007','extension_gross_area',abs(ext['gross_area_m2']-140.0)<1e-9,ext['gross_area_m2']),
            ('GEO-008','two_storeys',ext['storeys']==2,ext['storeys']),
            ('GEO-009','connection_points',types.get('connection')==4,types.get('connection',0)),
            ('GEO-010','stair_connects_levels',any(item['type']=='stair' and item['connects_levels']==['L00','L01'] for item in objects),types.get('stair',0)),
            ('GEO-011','spaces_present',types.get('space')==12,types.get('space',0)),
            ('GEO-012','walls_present',types.get('wall')==26,types.get('wall',0)),
            ('GEO-013','slabs_and_roofs_present',types.get('slab')==6,types.get('slab',0)),
            ('GEO-014','openings_present',types.get('opening')==16,types.get('opening',0)),
            ('GEO-015','opening_hosts_exist',all(item.get('host_id') in host_ids for item in objects if item['type']=='opening'),types.get('opening',0)),
            ('GEO-016','parking_zone_total',sum(z['spaces'] for z in self.config['parking_zones'])==225,sum(z['spaces'] for z in self.config['parking_zones'])),
            ('GEO-017','parking_bay_objects',parking_bay_count==225,parking_bay_count),
            ('GEO-018','parking_zones_present',types.get('parking_zone')==5,types.get('parking_zone',0)),
            ('GEO-019','site_and_parcel_present',types.get('site')==1 and types.get('parcel')==1,[types.get('site',0),types.get('parcel',0)]),
            ('GEO-020','professional_blockers_visible',len(model['professional_blockers'])==6,len(model['professional_blockers'])),
            ('GEO-021','req107_closed',model['req107_status']=='CLOSED_PROJECT_LEADER_APPROVED',model['req107_status']),
            ('GEO-022','fingerprint_length',len(model['model_fingerprint_sha256'])==64,len(model['model_fingerprint_sha256'])),
        ]
        return [{'check_id':cid,'name':name,'passed':passed,'observed':observed} for cid,name,passed,observed in checks]


class CentralGeometricProjectModelExporter:
    def export_all(self, result: Mapping[str, Any], output_dir: str | Path) -> dict[str, Path]:
        root=Path(output_dir)
        if root.exists():
            for child in root.iterdir():
                if child.is_dir():
                    import shutil; shutil.rmtree(child)
                else: child.unlink()
        root.mkdir(parents=True, exist_ok=True)
        model=result['model']; checks=result['checks']; paths:dict[str,Path]={}
        counts={}
        for item in model['objects']: counts[item['type']]=counts.get(item['type'],0)+1
        summary={
            'schema_version':'phoenix.central-geometric-model-summary/1.0','model_id':model['model_id'],
            'model_fingerprint_sha256':model['model_fingerprint_sha256'],'status':'CENTRAL_GEOMETRIC_PROJECT_MODEL_GENERATED',
            'object_count':len(model['objects']),'relationship_count':len(model['relationships']),'level_count':len(model['levels']),
            'space_count':counts.get('space',0),'wall_count':counts.get('wall',0),'opening_count':counts.get('opening',0),
            'parking_zone_count':counts.get('parking_zone',0),'parking_bay_count':counts.get('parking_bay',0),
            'extension_width_m':7.0,'extension_length_m':10.0,'extension_storeys':2,'extension_gross_area_m2':140.0,
            'geometry_check_count':len(checks),'geometry_checks_passed':sum(1 for c in checks if c['passed']),
            'all_geometry_checks_passed':all(c['passed'] for c in checks),'professional_blocker_count':6,
            'req107_status':model['req107_status'],'final_permit_ready_generation_allowed':False,
            'model_is_single_source_for_drawings_reports_calculations':True,
        }
        paths['summary']=self._json(root/'01_model_summary.json',summary)
        paths['model']=self._json(root/'02_canonical_geometric_project_model.json',model)
        paths['objects']=self._csv(root/'03_object_register.csv',model['objects'],['id','type','subtype','name','level_id','building_id','host_id','zone_id','status'])
        paths['levels']=self._csv(root/'04_level_register.csv',model['levels'],['id','name','elevation_m','storey_index'])
        paths['spaces']=self._csv(root/'05_space_register.csv',[o for o in model['objects'] if o['type']=='space'],['id','name','level_id','building_id','area_m2','status'])
        paths['openings']=self._csv(root/'06_opening_register.csv',[o for o in model['objects'] if o['type']=='opening'],['id','subtype','level_id','host_id','offset_m','width_m','height_m','status'])
        paths['connections']=self._csv(root/'07_connection_register.csv',[o for o in model['objects'] if o['type']=='connection'],['id','name','level_id','subtype','status'])
        paths['parking']=self._csv(root/'08_parking_zone_register.csv',[o for o in model['objects'] if o['type']=='parking_zone'],['id','name','space_count','status'])
        paths['relations']=self._csv(root/'09_relationship_register.csv',model['relationships'],['id','type','source','target'])
        paths['checks']=self._csv(root/'10_geometry_validation_checks.csv',checks,['check_id','name','passed','observed'])
        dependency={'model_id':model['model_id'],'model_fingerprint_sha256':model['model_fingerprint_sha256'],'downstream_consumers':[
            {'consumer':'real_concept_drawings_reports_v1_1_0','role':'geometry_source','required':True},
            {'consumer':'future_calculation_sheets','role':'quantities_and_dimensions_source','required':True},
            {'consumer':'future_permit_dossier','role':'drawing_and_area_source','required':True},
        ],'rule':'No downstream geometry may be authored independently of the central model.'}
        paths['dependency']=self._json(root/'11_model_dependency_map.json',dependency)
        paths['ground_svg']=self._svg_plan(root/'12_ground_floor_plan.svg',model,'L00','Begane grond')
        paths['first_svg']=self._svg_plan(root/'13_first_floor_plan.svg',model,'L01','Verdieping')
        paths['site_svg']=self._svg_site(root/'14_site_parking_plan.svg',model)
        paths['iso_svg']=self._svg_isometric(root/'15_isometric_model.svg',model)
        paths['browser']=self._browser(root/'16_model_browser.html',summary,model)
        paths['dxf']=self._dxf(root/'17_central_model_plan.dxf',model)
        paths['obj']=self._obj(root/'18_central_model_3d.obj',model)
        paths['mtl']=self._mtl(root/'19_central_model_3d.mtl')
        paths['manifest']=self._json(root/'20_model_export_manifest.json',{
            'model_id':model['model_id'],'model_fingerprint_sha256':model['model_fingerprint_sha256'],
            'exports':['JSON','CSV','SVG','HTML','DXF','OBJ','MTL'],'coordinate_system':model['coordinate_system'],'units':model['units'],
        })
        paths['checksums']=self._checksums(paths,root/'checksums.sha256')
        paths['package']=self._zip(paths,root/'BB35_PILOT_1_CENTRAL_GEOMETRIC_PROJECT_MODEL_v1_0_0.zip')
        return paths

    @staticmethod
    def _json(path:Path,value:Any)->Path:
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n'); return path

    @staticmethod
    def _csv(path:Path,rows:list[dict[str,Any]],fields:list[str])->Path:
        with path.open('w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\r\n'); writer.writeheader()
            for row in rows: writer.writerow({field:row.get(field,'') for field in fields})
        return path

    @staticmethod
    def _svg_plan(path:Path,model:Mapping[str,Any],level_id:str,title:str)->Path:
        scale=24; ox=80; oy=390
        def sx(x):return ox+x*scale
        def sy(y):return oy-y*scale
        lines=[]; labels=[]
        for obj in model['objects']:
            if obj['type']=='wall' and obj.get('level_id')==level_id:
                g=obj['geometry']; x1,y1,_=g['start']; x2,y2,_=g['end']; width=max(2,g['thickness_m']*scale)
                lines.append(f'<line x1="{sx(x1):.2f}" y1="{sy(y1):.2f}" x2="{sx(x2):.2f}" y2="{sy(y2):.2f}" stroke="#18212b" stroke-width="{width:.2f}"/>')
            if obj['type']=='space' and obj.get('level_id')==level_id:
                pts=obj['geometry']['points']; cx=sum(p[0] for p in pts)/len(pts); cy=sum(p[1] for p in pts)/len(pts)
                labels.append(f'<text x="{sx(cx):.2f}" y="{sy(cy):.2f}" text-anchor="middle" font-size="10">{html.escape(obj["name"])}</text>')
                labels.append(f'<text x="{sx(cx):.2f}" y="{sy(cy)+13:.2f}" text-anchor="middle" font-size="9">{obj["area_m2"]:.1f} m²</text>')
        connection=''.join(f'<circle cx="{sx(o["geometry"]["point"][0]):.2f}" cy="{sy(o["geometry"]["point"][1]):.2f}" r="5" fill="#d97706"/>' for o in model['objects'] if o['type']=='connection' and o.get('level_id')==level_id)
        content=f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="520" viewBox="0 0 1000 520"><rect width="1000" height="520" fill="white"/><text x="40" y="38" font-family="Arial" font-size="24" font-weight="bold">{title} — centraal geometrisch model</text><text x="40" y="62" font-family="Arial" font-size="13">{STATUS}</text><g font-family="Arial">{''.join(lines)}{''.join(labels)}{connection}</g><line x1="40" y1="480" x2="280" y2="480" stroke="black" stroke-width="3"/><text x="40" y="505" font-family="Arial" font-size="12">10 m modelschaal</text></svg>"""
        path.write_text(content,encoding='utf-8',newline='\n'); return path

    @staticmethod
    def _svg_site(path:Path,model:Mapping[str,Any])->Path:
        scale=6; ox=330; oy=280
        def sx(x):return ox+x*scale
        def sy(y):return oy-y*scale
        elements=[]
        for obj in model['objects']:
            if obj['type'] in {'site','parcel','building'}:
                pts=' '.join(f'{sx(p[0]):.2f},{sy(p[1]):.2f}' for p in obj['geometry']['points'])
                style={'site':'fill:#f8fafc;stroke:#64748b;stroke-width:2','parcel':'fill:#ecfccb;stroke:#4d7c0f;stroke-width:2','building':'fill:#dbeafe;stroke:#1d4ed8;stroke-width:2'}[obj['type']]
                elements.append(f'<polygon points="{pts}" style="{style}"/>')
            elif obj['type']=='parking_zone':
                x,y,_=obj['geometry']['origin']; w,h,_=obj['geometry']['size']
                elements.append(f'<rect x="{sx(x):.2f}" y="{sy(y+h):.2f}" width="{w*scale:.2f}" height="{h*scale:.2f}" fill="#fef3c7" stroke="#b45309" stroke-width="1.5"/>')
                elements.append(f'<text x="{sx(x+w/2):.2f}" y="{sy(y+h/2):.2f}" text-anchor="middle" font-family="Arial" font-size="11">{obj["id"]}: {obj["space_count"]} pp</text>')
        content=f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600"><rect width="900" height="600" fill="white"/><text x="35" y="35" font-family="Arial" font-size="24" font-weight="bold">Terrein, perceel en parkeeromgeving</text><text x="35" y="58" font-family="Arial" font-size="13">225 projectleider-bevestigde plaatsen — veldverificatie pending</text>{''.join(elements)}</svg>"""
        path.write_text(content,encoding='utf-8',newline='\n'); return path

    @staticmethod
    def _svg_isometric(path:Path,model:Mapping[str,Any])->Path:
        def proj(x,y,z): return (420+(x-y)*18,430-(x+y)*8-z*28)
        polys=[]
        colors={'BLD-EXISTING':'#93c5fd','BLD-EXTENSION':'#fbbf24'}
        for bid,footprint,height in [('BLD-EXISTING',[[0,0],[12,0],[12,14],[0,14]],6.4),('BLD-EXTENSION',[[12,2],[19,2],[19,12],[12,12]],6.4)]:
            bottom=[proj(x,y,0) for x,y in footprint]; top=[proj(x,y,height) for x,y in footprint]
            polys.append(f'<polygon points="{' '.join(f'{x:.1f},{y:.1f}' for x,y in top)}" fill="{colors[bid]}" stroke="#1f2937"/>')
            for i in range(4):
                j=(i+1)%4; pts=[bottom[i],bottom[j],top[j],top[i]]
                polys.append(f'<polygon points="{' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)}" fill="{colors[bid]}" fill-opacity="0.72" stroke="#1f2937"/>')
        content=f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="560" viewBox="0 0 900 560"><rect width="900" height="560" fill="white"/><text x="35" y="38" font-family="Arial" font-size="24" font-weight="bold">Isometrisch centraal projectmodel</text><text x="35" y="62" font-family="Arial" font-size="13">Bestaand blauw — uitbreiding geel — conceptmodel</text>{''.join(polys)}</svg>"""
        path.write_text(content,encoding='utf-8',newline='\n'); return path

    @staticmethod
    def _browser(path:Path,summary:Mapping[str,Any],model:Mapping[str,Any])->Path:
        rows=''.join(f'<tr><td>{html.escape(o["id"])}</td><td>{html.escape(o["type"])}</td><td>{html.escape(str(o.get("level_id","")))}</td><td>{html.escape(str(o.get("name","")))}</td></tr>' for o in model['objects'] if o['type']!='parking_bay')
        content=f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Phoenix centraal geometrisch model</title><style>body{{font-family:Arial;max-width:1250px;margin:25px auto;color:#17202a}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.card{{background:#eef2ff;padding:13px;border:1px solid #c7d2fe}}iframe{{width:100%;height:550px;border:1px solid #bbb}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#1e293b;color:white}}</style></head><body><h1>Project Phoenix — centraal geometrisch projectmodel</h1><p><strong>{STATUS}</strong></p><div class="cards"><div class="card"><b>Objecten</b><br>{summary['object_count']}</div><div class="card"><b>Ruimten</b><br>{summary['space_count']}</div><div class="card"><b>Parkeerplaatsen</b><br>{summary['parking_bay_count']}</div><div class="card"><b>Controles</b><br>{summary['geometry_checks_passed']}/{summary['geometry_check_count']}</div></div><h2>Modelbeelden</h2><p><a href="12_ground_floor_plan.svg">Begane grond</a> | <a href="13_first_floor_plan.svg">Verdieping</a> | <a href="14_site_parking_plan.svg">Terrein en parkeren</a> | <a href="15_isometric_model.svg">Isometrie</a></p><iframe src="15_isometric_model.svg"></iframe><h2>Semantische objecten</h2><table><thead><tr><th>ID</th><th>Type</th><th>Niveau</th><th>Naam</th></tr></thead><tbody>{rows}</tbody></table><p>Modelvingerafdruk: <code>{summary['model_fingerprint_sha256']}</code></p></body></html>"""
        path.write_text(content,encoding='utf-8',newline='\n'); return path

    @staticmethod
    def _dxf(path:Path,model:Mapping[str,Any])->Path:
        lines=['0','SECTION','2','HEADER','0','ENDSEC','0','SECTION','2','ENTITIES']
        def add_line(x1,y1,x2,y2,layer): lines.extend(['0','LINE','8',layer,'10',str(x1),'20',str(y1),'30','0','11',str(x2),'21',str(y2),'31','0'])
        for obj in model['objects']:
            if obj['type']=='wall' and obj.get('level_id')=='L00':
                g=obj['geometry']; add_line(g['start'][0],g['start'][1],g['end'][0],g['end'][1],'WALLS')
            elif obj['type'] in {'site','parcel','building'}:
                pts=obj['geometry']['points']
                for i in range(len(pts)): add_line(pts[i][0],pts[i][1],pts[(i+1)%len(pts)][0],pts[(i+1)%len(pts)][1],obj['type'].upper())
        lines.extend(['0','ENDSEC','0','EOF']); path.write_text('\n'.join(lines)+'\n',encoding='ascii',newline='\n'); return path

    @staticmethod
    def _obj(path:Path,model:Mapping[str,Any])->Path:
        lines=['mtllib 19_central_model_3d.mtl','o HBM_CENTRAL_MODEL']; vertex_index=1
        def box(name,bbox,material):
            nonlocal vertex_index
            x0,y0,z0,x1,y1,z1=bbox; verts=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
            lines.append(f'g {name}'); lines.append(f'usemtl {material}')
            for v in verts: lines.append(f'v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}')
            faces=[(1,2,3,4),(5,8,7,6),(1,5,6,2),(2,6,7,3),(3,7,8,4),(5,1,4,8)]
            for face in faces: lines.append('f '+' '.join(str(vertex_index+i-1) for i in face))
            vertex_index+=8
        for obj in model['objects']:
            if obj['type'] in {'wall','slab'}:
                material='extension' if obj.get('building_id')=='BLD-EXTENSION' else 'existing'; box(obj['id'],obj['bbox'],material)
            elif obj['type']=='stair': box(obj['id'],obj['bbox'],'stair')
        path.write_text('\n'.join(lines)+'\n',encoding='ascii',newline='\n'); return path

    @staticmethod
    def _mtl(path:Path)->Path:
        path.write_text('newmtl existing\nKd 0.45 0.70 0.95\nnewmtl extension\nKd 0.96 0.65 0.15\nnewmtl stair\nKd 0.55 0.55 0.55\n',encoding='ascii',newline='\n'); return path

    @staticmethod
    def _checksums(paths:Mapping[str,Path],destination:Path)->Path:
        lines=[f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for key,p in sorted(paths.items()) if key not in {'checksums','package'}]
        destination.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n'); return destination

    @classmethod
    def _zip(cls,paths:Mapping[str,Path],destination:Path)->Path:
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
            for key,source in sorted(paths.items()):
                if key=='package': continue
                info=zipfile.ZipInfo(source.name,FIXED_ZIP_TIME); info.compress_type=zipfile.ZIP_STORED; info.create_system=3; info.external_attr=0o100644<<16
                archive.writestr(info,source.read_bytes())
        return destination
