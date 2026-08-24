import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.engines.adapters import libreoffice_document_router_v1_0 as router


class LibreOfficeDefaultDocumentRoutingTests(unittest.TestCase):
    def test_office_extension_classification(self):
        for name in (
            "a.doc", "a.docx", "a.odt", "a.rtf",
            "a.xls", "a.xlsx", "a.ods", "a.csv",
            "a.ppt", "a.pptx", "a.odp",
        ):
            self.assertTrue(router.is_office_document(name), name)

    def test_pdf_uses_non_office_route(self):
        self.assertFalse(router.is_office_document("a.pdf"))

    def test_docx_open_routes_to_libreoffice(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.docx"
            path.write_bytes(b"probe")
            with patch.object(
                router.LibreOfficeOfficeAdapter,
                "open_document",
                return_value={"status": "STARTED", "engine": "LibreOffice"},
            ) as mocked:
                result = router.open_document_path(path)
            mocked.assert_called_once()
            self.assertEqual(result["engine"], "LibreOffice")

    def test_pdf_companion_routes_to_libreoffice_convert(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sample.docx"
            source.write_bytes(b"probe")
            output = root / "out"
            expected = output / "sample.pdf"
            with patch.object(
                router.LibreOfficeOfficeAdapter,
                "convert",
                return_value={
                    "status": "PASS",
                    "engine": "LibreOffice",
                    "output": str(expected),
                },
            ) as mocked:
                result = router.create_pdf_companion(source, output)
            mocked.assert_called_once()
            self.assertEqual(result["output"], str(expected))

    def test_non_office_companion_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.pdf"
            path.write_bytes(b"%PDF")
            with self.assertRaises(ValueError):
                router.create_pdf_companion(path, Path(td) / "out")

    def test_missing_path_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            router.open_document_path("definitely_missing_phoenix_file.docx")


if __name__ == "__main__":
    unittest.main()
