import unittest
from phoenix.startscreen_runtime_sync.sync import patch_text

class TestStartRuntimeCors(unittest.TestCase):
    def test_runtime_label(self):
        out,n=patch_text("v1.8.7 · START v3.0.2")
        self.assertEqual(n,1)
        self.assertEqual(out,"v1.8.7 · START v4.41")

    def test_json_version_key(self):
        out,n=patch_text('{"start_version":"v3.0.2"}')
        self.assertEqual(n,1)
        self.assertEqual(out,'{"start_version":"v4.41"}')

    def test_engine_version_is_not_changed(self):
        out,n=patch_text("RUNTIME v1.8.7")
        self.assertEqual(n,0)
        self.assertEqual(out,"RUNTIME v1.8.7")

if __name__=="__main__":
    unittest.main()
