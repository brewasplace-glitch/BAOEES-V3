from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from phoenix.design.tropical_residential.ifc_identity_manifest import build_manifest, SCHEMA

class Obj:
    def __init__(self, name, guid, typ): self.Name=name;self.GlobalId=guid;self.typ=typ
    def is_a(self): return self.typ
class Rel:
    def __init__(self, **k): self.__dict__.update(k)
class Model:
    def __init__(self, mapping): self.mapping=mapping
    def by_type(self, typ): return self.mapping.get(typ, [])

class IdentityTest(unittest.TestCase):
    def fixtures(self):
        wall=Obj('Internal S1:0.0000,0.0000-1.0000,0.0000','wall-guid','IfcWall')
        op=Obj('test-door','opening-guid','IfcOpeningElement')
        door=Obj('test-door_DOOR','door-guid','IfcDoor')
        m=Model({'IfcWall':[wall], 'IfcOpeningElement':[op], 'IfcDoor':[door],
                 'IfcRelVoidsElement':[Rel(RelatedOpeningElement=op,RelatingBuildingElement=wall)],
                 'IfcRelFillsElement':[Rel(RelatingOpeningElement=op,RelatedBuildingElement=door)]})
        layout={'variant_id':'A','walls':[{'wall_key':'S1:0.0000,0.0000-1.0000,0.0000','external':False,'storey_index':0}],
                'openings':[{'opening_id':'test-door','host_wall_key':'S1:0.0000,0.0000-1.0000,0.0000','kind':'door'}]}
        return m,layout
    def test_exact_relations(self):
        m,l=self.fixtures()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.ifc';p.write_bytes(b'IFC')
            r=build_manifest(m,l,p)
            self.assertEqual(r['schema'], SCHEMA)
            self.assertEqual((r['wall_count'],r['opening_count']),(1,1))
            self.assertEqual(r['walls'][0]['ifc_global_id'],'wall-guid')
            self.assertFalse(r['structural_approval'])
    def test_missing_relation_fails_closed(self):
        m,l=self.fixtures();m.mapping['IfcRelFillsElement']=[]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.ifc';p.write_bytes(b'IFC')
            with self.assertRaisesRegex(ValueError,'R15_IFC_RELATION_MISMATCH'): build_manifest(m,l,p)
    def test_ambiguous_name_fails_closed(self):
        m,l=self.fixtures();m.mapping['IfcWall'].append(m.mapping['IfcWall'][0])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.ifc';p.write_bytes(b'IFC')
            with self.assertRaisesRegex(ValueError,'R15_IDENTITY_WALL_COUNT'): build_manifest(m,l,p)
if __name__=='__main__': unittest.main()
