import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "phoenix" / "autonomy" / "session_adapters.py"


class NlPdokSiteAcquisitionWiringTests(unittest.TestCase):
    def test_architecture_adapter_wires_pdok_after_upload_site_analysis(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        start = text.index("def run_architecture(")
        end = text.index("def run_digital_twin(", start)
        block = text[start:end]

        analyze = "site_result=analyze_site_drawings("
        acquire = "acquire_nl_pdok_site_evidence("
        assign = "context_result.site_context=site_result.site_context"
        write_site = 'write_json(site_context_path,context_result.site_context)'

        self.assertIn(analyze, block)
        self.assertIn(acquire, block)
        self.assertIn(assign, block)
        self.assertIn(write_site, block)
        self.assertLess(block.index(analyze), block.index(acquire))
        self.assertLess(block.index(acquire), block.index(assign))
        self.assertLess(block.index(assign), block.index(write_site))

    def test_pdok_evidence_outputs_are_added_to_architecture_outputs(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        self.assertIn(
            "from .nl_pdok_site_acquisition_v1_0 import acquire_nl_pdok_site_evidence",
            text,
        )
        self.assertIn("pdok_result=acquire_nl_pdok_site_evidence(", text)
        self.assertIn("pdok_result.output_files", text)
        self.assertIn("site_result.site_context=pdok_result.site_context", text)
        self.assertIn("site_result.evidence_register=pdok_result.evidence_register", text)


if __name__ == "__main__":
    unittest.main()
