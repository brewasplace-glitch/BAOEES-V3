import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from phoenix.osif.adapters import (
    AdapterContext,
    AdapterExecutionRequest,
    AdapterLifecycleState,
    FreeCADAdapter,
    FreeCADIntegrationError,
)


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if "--version" in command:
            return subprocess.CompletedProcess(
                command, 0, "FreeCAD 1.0.0\n", ""
            )

        result_path = Path(command[-1])
        job_path = Path(command[-2])
        job = json.loads(job_path.read_text(encoding="utf-8"))
        destination = job.get("destination_file")
        output_files = []
        if destination:
            destination_path = Path(destination)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_text("fake-freecad-output", encoding="utf-8")
            output_files.append(str(destination_path))
        result_path.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "output_files": output_files,
                    "warnings": [],
                    "errors": [],
                    "metadata": {
                        "document": {
                            "document_name": "PhoenixDocument",
                            "object_count": 1,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "done", "")


class BB4FreeCADTests(unittest.TestCase):
    def make_executable(self, folder):
        executable = Path(folder) / "FreeCADCmd.exe"
        executable.write_text("placeholder", encoding="utf-8")
        return executable

    def test_health_check(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = self.make_executable(folder)
            adapter = FreeCADAdapter(
                executable=str(executable),
                runner=FakeRunner(),
            )
            health = adapter.health_check()
        self.assertEqual(health.status, "available")
        self.assertIn("FreeCAD", health.details["version"])

    def test_descriptor_is_operational(self):
        descriptor = FreeCADAdapter().descriptor()
        self.assertEqual(descriptor.metadata["bb4_status"], "operational")
        self.assertTrue(
            any(
                item.capability_id == "freecad.geometry.validate"
                for item in descriptor.capabilities
            )
        )

    def test_document_create_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = self.make_executable(folder)
            destination = Path(folder) / "model.FCStd"
            runner = FakeRunner()
            adapter = FreeCADAdapter(
                executable=str(executable),
                runner=runner,
            )
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    request_id="create-1",
                    project_id="PHX",
                    capability_id="freecad.document.create",
                    inputs={
                        "destination_file": str(destination),
                        "primitives": [
                            {
                                "type": "box",
                                "length": 5,
                                "width": 4,
                                "height": 3,
                            }
                        ],
                    },
                    output_directory=folder,
                )
            )
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.evidence_sha256), 64)
        self.assertEqual(adapter.state, AdapterLifecycleState.READY)

    def test_import_requires_existing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = FreeCADAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            with self.assertRaisesRegex(
                FreeCADIntegrationError, "does not exist"
            ):
                adapter.execute(
                    AdapterExecutionRequest(
                        "import-1",
                        "PHX",
                        "freecad.document.import",
                        {
                            "source_file": str(Path(folder) / "missing.step"),
                            "destination_file": str(Path(folder) / "model.FCStd"),
                        },
                        folder,
                    )
                )

    def test_unsupported_format_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.txt"
            source.write_text("x", encoding="utf-8")
            adapter = FreeCADAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            with self.assertRaisesRegex(
                FreeCADIntegrationError, "Unsupported source format"
            ):
                adapter.execute(
                    AdapterExecutionRequest(
                        "inspect-1",
                        "PHX",
                        "freecad.document.inspect",
                        {"source_file": str(source)},
                        folder,
                    )
                )

    def test_custom_macro_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            macro = Path(folder) / "macro.py"
            macro.write_text("pass\n", encoding="utf-8")
            adapter = FreeCADAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            with self.assertRaisesRegex(
                FreeCADIntegrationError, "disabled by policy"
            ):
                adapter.execute(
                    AdapterExecutionRequest(
                        "macro-1",
                        "PHX",
                        "freecad.macro.execute",
                        {"macro_file": str(macro)},
                        folder,
                    )
                )

    def test_custom_macro_can_be_enabled(self):
        with tempfile.TemporaryDirectory() as folder:
            macro = Path(folder) / "macro.py"
            macro.write_text("pass\n", encoding="utf-8")
            adapter = FreeCADAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(
                AdapterContext(
                    "PHX",
                    folder,
                    {"allow_custom_freecad_macros": True},
                )
            )
            adapter.validate_request(
                AdapterExecutionRequest(
                    "macro-2",
                    "PHX",
                    "freecad.macro.execute",
                    {"macro_file": str(macro)},
                    folder,
                )
            )

    def test_timeout_result(self):
        def timeout_runner(command, **kwargs):
            if "--version" in command:
                return subprocess.CompletedProcess(command, 0, "FreeCAD", "")
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with tempfile.TemporaryDirectory() as folder:
            adapter = FreeCADAdapter(
                executable=str(self.make_executable(folder)),
                runner=timeout_runner,
            )
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "timeout-1",
                    "PHX",
                    "freecad.document.create",
                    {
                        "destination_file": str(Path(folder) / "model.FCStd"),
                        "primitives": [
                            {
                                "type": "sphere",
                                "radius": 2,
                            }
                        ],
                    },
                    folder,
                    1,
                )
            )
        self.assertEqual(result.status, "timed_out")


if __name__ == "__main__":
    unittest.main()
