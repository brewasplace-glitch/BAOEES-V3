import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from phoenix.osif.adapters import (
    AdapterContext,
    AdapterExecutionRequest,
    BlenderAdapter,
    BlenderIntegrationError,
)


class FakeRunner:
    def __call__(self, command, **kwargs):
        if "--version" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                "Blender 4.3.0\n",
                "",
            )

        result_path = Path(command[-1])
        job_path = Path(command[-2])
        job = json.loads(job_path.read_text(encoding="utf-8"))
        destination = str(job.get("destination_file", ""))
        output_files = []
        if destination:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fake-blender-output", encoding="utf-8")
            output_files.append(str(path))

        result_path.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "output_files": output_files,
                    "warnings": [],
                    "errors": [],
                    "metadata": {
                        "scene": {
                            "object_count": 3,
                            "mesh_count": 1,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            command,
            0,
            "render complete",
            "",
        )


class BB6BlenderTests(unittest.TestCase):
    def make_executable(self, folder):
        path = Path(folder) / "blender.exe"
        path.write_text("placeholder", encoding="utf-8")
        return path

    def make_source(self, folder, suffix=".obj"):
        path = Path(folder) / f"model{suffix}"
        path.write_text("mesh", encoding="utf-8")
        return path

    def test_health_check(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            health = adapter.health_check()
        self.assertEqual(health.status, "available")
        self.assertIn("Blender", health.details["version"])

    def test_descriptor_operational(self):
        descriptor = BlenderAdapter().descriptor()
        self.assertEqual(
            descriptor.metadata["bb6_status"],
            "operational",
        )
        self.assertTrue(
            any(
                item.capability_id == "blender.render.animation"
                for item in descriptor.capabilities
            )
        )

    def test_render_still(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "render.png"
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "render-1",
                    "PHX",
                    "blender.render.still",
                    {
                        "source_file": str(self.make_source(folder)),
                        "destination_file": str(destination),
                        "camera": {"location": [10, -10, 8]},
                    },
                    folder,
                )
            )
            self.assertTrue(destination.is_file())
            self.assertEqual(result.status, "completed")
            self.assertEqual(len(result.evidence_sha256), 64)

    def test_render_animation(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "walkthrough.mp4"
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "animation-1",
                    "PHX",
                    "blender.render.animation",
                    {
                        "source_file": str(self.make_source(folder, ".glb")),
                        "destination_file": str(destination),
                        "render": {"frame_end": 60, "fps": 30},
                    },
                    folder,
                )
            )
            self.assertTrue(destination.is_file())
            self.assertEqual(result.status, "completed")

    def test_scene_inspect(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "inspect-1",
                    "PHX",
                    "blender.scene.inspect",
                    {"source_file": str(self.make_source(folder))},
                    folder,
                )
            )
            self.assertEqual(
                result.metadata["scene"]["object_count"],
                3,
            )

    def test_invalid_source_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.make_source(folder, ".txt")
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            with self.assertRaisesRegex(
                BlenderIntegrationError,
                "Unsupported source format",
            ):
                adapter.execute(
                    AdapterExecutionRequest(
                        "bad-source",
                        "PHX",
                        "blender.scene.inspect",
                        {"source_file": str(source)},
                        folder,
                    )
                )

    def test_invalid_destination_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=FakeRunner(),
            )
            adapter.initialize(AdapterContext("PHX", folder))
            with self.assertRaisesRegex(
                BlenderIntegrationError,
                "Unsupported destination format",
            ):
                adapter.execute(
                    AdapterExecutionRequest(
                        "bad-output",
                        "PHX",
                        "blender.render.still",
                        {
                            "source_file": str(self.make_source(folder)),
                            "destination_file": str(Path(folder) / "render.docx"),
                        },
                        folder,
                    )
                )

    def test_timeout_result(self):
        def timeout_runner(command, **kwargs):
            if "--version" in command:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "Blender",
                    "",
                )
            raise subprocess.TimeoutExpired(
                command,
                kwargs["timeout"],
            )

        with tempfile.TemporaryDirectory() as folder:
            adapter = BlenderAdapter(
                executable=str(self.make_executable(folder)),
                runner=timeout_runner,
            )
            adapter.initialize(AdapterContext("PHX", folder))
            result = adapter.execute(
                AdapterExecutionRequest(
                    "timeout-1",
                    "PHX",
                    "blender.render.still",
                    {
                        "source_file": str(self.make_source(folder)),
                        "destination_file": str(Path(folder) / "render.png"),
                    },
                    folder,
                    1,
                )
            )
            self.assertEqual(result.status, "timed_out")


if __name__ == "__main__":
    unittest.main()
