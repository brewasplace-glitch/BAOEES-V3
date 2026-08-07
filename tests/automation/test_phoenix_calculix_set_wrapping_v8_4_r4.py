import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "runners" / "PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("phoenix_structural_solver_input_v8_3_r4", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runner: {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPhoenixCalculixSetWrappingV84R4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()

    def test_91_ids_are_wrapped_to_maximum_16_entries(self):
        lines = self.runner._calculix_id_lines(range(1, 92))
        self.assertEqual(len(lines), 6)
        self.assertTrue(all(len(line.split(",")) <= 16 for line in lines))

        flattened = [
            int(value.strip())
            for line in lines
            for value in line.split(",")
            if value.strip()
        ]
        self.assertEqual(flattened, list(range(1, 92)))

    def test_exact_16_ids_remain_on_one_line(self):
        lines = self.runner._calculix_id_lines(range(1, 17))
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0].split(",")), 16)

    def test_17_ids_are_split_across_two_lines(self):
        lines = self.runner._calculix_id_lines(range(1, 18))
        self.assertEqual([len(line.split(",")) for line in lines], [16, 1])

    def test_validator_accepts_wrapped_91_id_set(self):
        lines = ["*NSET, NSET=NALL"]
        lines.extend(self.runner._calculix_id_lines(range(1, 92)))
        self.runner._validate_calculix_data_line_width(lines)

    def test_validator_rejects_17_entry_data_record(self):
        bad_line = ", ".join(str(value) for value in range(1, 18))
        with self.assertRaisesRegex(ValueError, "17 entries"):
            self.runner._validate_calculix_data_line_width(
                ["*NSET, NSET=NALL", bad_line]
            )

    def test_v83_nall_writer_uses_wrapping_helper(self):
        source = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "lines.extend(_calculix_id_lines(node_tags[n] for n in sorted(nodes)))",
            source,
        )
        self.assertNotIn(
            'lines.append(", ".join(str(node_tags[n]) for n in sorted(nodes)))',
            source,
        )
        self.assertIn("_validate_calculix_data_line_width(lines)", source)


if __name__ == "__main__":
    unittest.main()