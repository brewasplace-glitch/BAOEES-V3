from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from phoenix.governance.existing_capability_reuse_gate import GateError, _load_spec, classify, validate_spec


def git(repo: Path, *args: str) -> None:
    cp = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {cp.stderr}")


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ExistingCapabilityReuseGateTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        repo = Path(td.name)
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Phoenix Test")
        git(repo, "config", "user.email", "phoenix-test@example.invalid")
        write(repo, "README.md", "# fixture\n")
        git(repo, "add", "README.md")
        git(repo, "commit", "-q", "-m", "fixture")
        return td, repo

    def commit_all(self, repo: Path, message: str = "fixture update") -> None:
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", message)

    def test_build_when_no_evidence_exists(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        result = classify(
            repo,
            {
                "capability_id": "PHX.TEST.BUILD",
                "required_paths": ["phoenix/example.py"],
                "required_symbols": ["ExampleEngine"],
                "required_test_paths": ["tests/test_example.py"],
            },
            run_tests=True,
        )
        self.assertEqual("BUILD", result["decision"])
        self.assertTrue(result["build_required"])

    def test_reuse_when_contract_and_test_pass(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        write(repo, "phoenix/example.py", "class ExampleEngine:\n    pass\n")
        write(repo, "tests/test_example.py", "raise SystemExit(0)\n")
        self.commit_all(repo)
        result = classify(
            repo,
            {
                "capability_id": "PHX.TEST.REUSE",
                "keywords": ["ExampleEngine"],
                "required_paths": ["phoenix/example.py"],
                "required_symbols": ["ExampleEngine"],
                "required_test_paths": ["tests/test_example.py"],
            },
            run_tests=True,
        )
        self.assertEqual("REUSE", result["decision"])
        self.assertFalse(result["build_required"])

    def test_extend_when_existing_implementation_misses_required_symbol(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        write(repo, "phoenix/example.py", "class ExistingEngine:\n    pass\n")
        self.commit_all(repo)
        result = classify(
            repo,
            {
                "capability_id": "PHX.TEST.EXTEND",
                "keywords": ["ExistingEngine"],
                "required_paths": ["phoenix/example.py"],
                "required_symbols": ["RequiredBridge"],
            },
            run_tests=False,
        )
        self.assertEqual("EXTEND", result["decision"])

    def test_repair_when_required_test_fails(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        write(repo, "phoenix/example.py", "class ExampleEngine:\n    pass\n")
        write(repo, "tests/test_example.py", "raise SystemExit(7)\n")
        self.commit_all(repo)
        result = classify(
            repo,
            {
                "capability_id": "PHX.TEST.REPAIR",
                "required_paths": ["phoenix/example.py"],
                "required_symbols": ["ExampleEngine"],
                "required_test_paths": ["tests/test_example.py"],
            },
            run_tests=True,
        )
        self.assertEqual("REPAIR", result["decision"])
        self.assertIn("tests/test_example.py", result["requirements"]["failing_tests"])

    def test_discovery_only_evidence_blocks_blind_build(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        write(repo, "docs/note.md", "Future capability marker: ExistingThing\n")
        self.commit_all(repo)
        result = classify(
            repo,
            {
                "capability_id": "PHX.TEST.DISCOVERY",
                "keywords": ["ExistingThing"],
                "required_paths": ["phoenix/not_proven.py"],
            },
            run_tests=False,
        )
        self.assertEqual("EXTEND", result["decision"])

    def test_dirty_worktree_fails_closed(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        write(repo, "scratch.txt", "dirty\n")
        with self.assertRaises(GateError):
            classify(
                repo,
                {"capability_id": "PHX.TEST.DIRTY", "keywords": ["anything"]},
                run_tests=False,
            )

    def test_spec_file_with_utf8_bom_is_accepted(self):
        import argparse

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "spec.json"
            path.write_text(
                '{"capability_id":"PHX.TEST.BOM","keywords":["BOM"]}',
                encoding="utf-8-sig",
            )
            args = argparse.Namespace(spec=str(path), spec_json=None)
            loaded = _load_spec(args)
            self.assertEqual("PHX.TEST.BOM", loaded["capability_id"])
    def test_unsafe_path_is_rejected(self):
        with self.assertRaises(GateError):
            validate_spec(
                {
                    "capability_id": "PHX.TEST.UNSAFE",
                    "required_paths": ["../outside.txt"],
                }
            )

    def test_classification_is_read_only_on_clean_repo(self):
        td, repo = self.make_repo()
        self.addCleanup(td.cleanup)
        before = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repo,
            text=True,
        )
        classify(
            repo,
            {"capability_id": "PHX.TEST.READONLY", "keywords": ["definitely-not-present"]},
            run_tests=False,
        )
        after = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repo,
            text=True,
        )
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
