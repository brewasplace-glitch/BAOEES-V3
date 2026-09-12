import unittest
from phoenix.startscreen_repair.repair import canonicalize_labels, ensure_utf8_meta, suspicious_count

class TestStartscreenRepair(unittest.TestCase):
    def test_branding(self):
        s="<title>PROJECT PHOENIX 3.0.2</title> PROJECT PHOENIX 3.0.2 START v3.0.2"
        o=canonicalize_labels(s)
        self.assertIn("PROJECT PHOENIX 4.41",o)
        self.assertIn("START v4.41",o)
        self.assertNotIn("PROJECT PHOENIX 3.0.2",o)

    def test_utf8_meta(self):
        s="<html><head><title>x</title></head><body></body></html>"
        o=ensure_utf8_meta(s)
        self.assertIn('charset="utf-8"',o.lower())

    def test_suspicious(self):
        self.assertGreater(suspicious_count("ðŸŽ¤"),0)
        self.assertEqual(suspicious_count("🎤"),0)

    def test_toolbar_gate_scopes_only_toolbar_block(self):
        import re
        js = """
        #phoenix-cad-toolbar{display:flex;position:static!important}
        #phoenix-cad-modal{position:fixed;inset:0}
        """
        m = re.search(
            r"#phoenix-cad-toolbar\s*\{([^}]*)\}",
            js,
            flags=re.I | re.S,
        )
        self.assertIsNotNone(m)
        css = re.sub(r"\s+", "", m.group(1).lower())
        self.assertNotIn("position:fixed", css)
        self.assertIn("position:static!important", css)


if __name__=="__main__":
    unittest.main()
