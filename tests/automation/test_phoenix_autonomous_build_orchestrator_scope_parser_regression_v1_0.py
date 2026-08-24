import unittest

from phoenix.autonomy.autonomous_build_orchestrator_v1_0 import (
    AutonomousBuildOrchestrator,
    CommandResult,
)


class PorcelainScopeExecutor:
    def __init__(self, status_text: str):
        self.status_text = status_text

    def __call__(self, command, repository):
        argv = list(command.argv)
        if argv[:3] == ["git", "status", "--porcelain=v1"]:
            return CommandResult(
                argv=argv,
                cwd=str(repository),
                returncode=0,
                stdout=self.status_text,
                stderr="",
                elapsed_seconds=0.0,
            )
        raise AssertionError(f"unexpected command: {argv}")


class ScopeParserRegressionTests(unittest.TestCase):
    def changed(self, status_text):
        orchestrator = AutonomousBuildOrchestrator(
            ".",
            executor=PorcelainScopeExecutor(status_text),
        )
        return orchestrator._changed_scope()

    def test_unstaged_modified_preserves_first_character(self):
        self.assertEqual(
            self.changed(" M phoenix/local_app/static/example.js\n"),
            ["phoenix/local_app/static/example.js"],
        )

    def test_staged_modified_preserves_first_character(self):
        self.assertEqual(
            self.changed("M  phoenix/local_app/static/example.js\n"),
            ["phoenix/local_app/static/example.js"],
        )

    def test_untracked_preserves_first_character(self):
        self.assertEqual(
            self.changed("?? phoenix/local_app/static/new.js\n"),
            ["phoenix/local_app/static/new.js"],
        )

    def test_rename_uses_destination_path(self):
        self.assertEqual(
            self.changed("R  oldname.js -> phoenix/newname.js\n"),
            ["phoenix/newname.js"],
        )

    def test_multiple_lines_preserve_first_line_prefix(self):
        self.assertEqual(
            self.changed(
                " M phoenix/a.py\n"
                "?? phoenix/b.py\n"
                "A  phoenix/c.py\n"
            ),
            ["phoenix/a.py", "phoenix/b.py", "phoenix/c.py"],
        )


if __name__ == "__main__":
    unittest.main()
