import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.osif import ApplicationRegistry, Capability
from phoenix.osif.discovery import (
    ApplicationDiscoveryService,
    DiscoveryCandidate,
    DiscoveryError,
)


class BB2DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.service = ApplicationDiscoveryService(timeout_seconds=5)

    def test_python_module_discovery(self):
        candidate = DiscoveryCandidate(
            application_id="json",
            name="JSON",
            adapter_id="adapter.json",
            execution_mode="python",
            python_modules=("json",),
            capabilities=(Capability("json.read", "Read JSON"),),
        )
        result = self.service.discover_candidate(candidate)
        self.assertTrue(result.found)
        self.assertEqual(result.python_module, "json")
        self.assertEqual(len(result.evidence_sha256), 64)

    def test_executable_discovery(self):
        candidate = DiscoveryCandidate(
            application_id="python",
            name="Python",
            adapter_id="adapter.python",
            execution_mode="cli",
            executable_names=(Path(sys.executable).name,),
            version_arguments=("--version",),
        )
        result = self.service.discover_candidate(candidate)
        self.assertTrue(result.found)
        self.assertTrue(result.executable)

    def test_unavailable_application(self):
        candidate = DiscoveryCandidate(
            application_id="missing",
            name="Missing",
            adapter_id="adapter.missing",
            execution_mode="cli",
            executable_names=("phoenix-definitely-missing-executable",),
        )
        result = self.service.discover_candidate(candidate)
        self.assertFalse(result.found)
        self.assertEqual(result.health_status, "unavailable")

    def test_duplicate_candidate_rejected(self):
        candidate = DiscoveryCandidate(
            "x",
            "X",
            "adapter.x",
            "python",
            python_modules=("json",),
        )
        with self.assertRaisesRegex(DiscoveryError, "Duplicate"):
            self.service.discover_all((candidate, candidate))

    def test_registry_update(self):
        registry = ApplicationRegistry()
        candidate = DiscoveryCandidate(
            "json",
            "JSON",
            "adapter.json",
            "python",
            python_modules=("json",),
            capabilities=(Capability("json.read", "Read JSON"),),
        )
        report = self.service.update_registry(
            registry=registry,
            candidates=(candidate,),
        )
        descriptor = registry.get("json")
        self.assertTrue(descriptor.enabled)
        self.assertEqual(report["results"][0]["health_status"], "available")

    def test_unavailable_registry_entry_disabled(self):
        registry = ApplicationRegistry()
        candidate = DiscoveryCandidate(
            "missing",
            "Missing",
            "adapter.missing",
            "cli",
            executable_names=("phoenix-definitely-missing-executable",),
        )
        self.service.update_registry(
            registry=registry,
            candidates=(candidate,),
        )
        self.assertFalse(registry.get("missing").enabled)

    def test_write_report_atomic(self):
        report = {"ok": True}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            result = self.service.write_report(report, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(result, path)
        self.assertTrue(loaded["ok"])


if __name__ == "__main__":
    unittest.main()
