import json
from pathlib import Path
import tempfile
import unittest
from engineering_kernel.factory.generator import generate_domain_scaffolding

class FactoryTests(unittest.TestCase):
    def make_repo(self, root):
        p=root/"engineering_kernel/specification/functions/function_registry.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"functions":[
            {"id":"PEK-UNITS-0001","name":"quantity","domain":"UNITS","purpose":"Create quantity."},
            {"id":"PEK-UNITS-0002","name":"convert","domain":"UNITS","purpose":"Convert quantity."}
        ]}),encoding="utf-8")

    def test_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.make_repo(root)
            result=generate_domain_scaffolding(root,"UNITS",Path("out"),dry_run=True)
            self.assertEqual(result["created"],2)
            self.assertFalse((root/"out").exists())

    def test_generate_then_skip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.make_repo(root)
            self.assertEqual(generate_domain_scaffolding(root,"UNITS",Path("out"))["created"],2)
            self.assertEqual(generate_domain_scaffolding(root,"UNITS",Path("out"))["skipped"],2)
