import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phoenix.engines.adapters.libreoffice_office_adapter_v1_0 import (
    LibreOfficeAdapterError,
    LibreOfficeOfficeAdapter,
    resolve_conversion_filter,
)


class LibreOfficeOfficeAdapterTests(unittest.TestCase):
    def test_docx_pdf_filter(self):
        self.assertEqual(
            resolve_conversion_filter("a.docx", "pdf"),
            "pdf:writer_pdf_Export",
        )

    def test_xlsx_pdf_filter(self):
        self.assertEqual(
            resolve_conversion_filter("a.xlsx", "pdf"),
            "pdf:calc_pdf_Export",
        )

    def test_pptx_pdf_filter(self):
        self.assertEqual(
            resolve_conversion_filter("a.pptx", "pdf"),
            "pdf:impress_pdf_Export",
        )

    def test_docx_to_xlsx_is_blocked(self):
        with self.assertRaises(LibreOfficeAdapterError):
            resolve_conversion_filter("a.docx", "xlsx")

    def test_unsupported_input_fails_closed(self):
        with self.assertRaises(LibreOfficeAdapterError):
            resolve_conversion_filter("a.bin", "pdf")

    def test_missing_input_fails_closed(self):
        adapter = LibreOfficeOfficeAdapter()
        with self.assertRaises(LibreOfficeAdapterError):
            adapter.convert("does-not-exist.docx", "pdf", ".")

    def test_document_export_bridge_imports(self):
        from baoees.document_export_engine.libreoffice_bridge import (
            DocumentExportLibreOfficeBridge,
        )
        bridge = DocumentExportLibreOfficeBridge()
        self.assertTrue(callable(bridge.convert_office_document))
        self.assertTrue(callable(bridge.open_office_document))


if __name__ == "__main__":
    unittest.main()
