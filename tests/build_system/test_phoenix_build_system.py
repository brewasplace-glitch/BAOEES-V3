from pathlib import Path
import json
import tempfile
import unittest

from phoenix.build_system import BuildPlan, BuildSystem
from phoenix.build_system.knowledge_index import generate_index


class BuildSystemTests(unittest.TestCase):
    def test_plan_requires_files(self) -> None:
        plan = BuildPlan(
            build_block="BB9A",
            version="1.0.0",
            commit_message="docs: add PKB",
        )
        with self.assertRaises(ValueError):
            plan.validate()

    def test_evidence_contains_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("Phoenix\n", encoding="utf-8")
            plan = BuildPlan(
                build_block="BB9A",
                version="1.0.0",
                files=["README.md"],
                tests=["unit"],
                commit_message="docs: add PKB",
            )
            payload = BuildSystem(root).create_evidence(
                plan,
                root / "evidence.json",
            )
            self.assertEqual(len(payload["files"][0]["sha256"]), 64)

    def test_missing_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = BuildPlan(
                build_block="BB9A",
                version="1.0.0",
                files=["missing.md"],
                commit_message="docs: add PKB",
            )
            with self.assertRaises(FileNotFoundError):
                BuildSystem(root).create_evidence(
                    plan,
                    root / "evidence.json",
                )

    def test_index_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "architecture").mkdir()
            (root / "architecture" / "system_overview.md").write_text(
                "# Overview\n",
                encoding="utf-8",
            )
            output = generate_index(root)
            text = output.read_text(encoding="utf-8")
            self.assertIn("architecture/system_overview.md", text)


if __name__ == "__main__":
    unittest.main()
