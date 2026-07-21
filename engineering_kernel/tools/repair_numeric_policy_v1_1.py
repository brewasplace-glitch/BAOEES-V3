"""Repair unsafe v1.0 migrations before applying Numerical Test Policy v1.1."""

from __future__ import annotations

import argparse
from pathlib import Path


REPAIRS = {
    "test_foundation_wave1.py": [
        (
            "assert_float_close(self, distribute_load_equally(300.0, 3), (100.0, 100.0, 100.0))",
            "assert_numeric_sequence_close(self, distribute_load_equally(300.0, 3), (100.0, 100.0, 100.0))",
        ),
    ],
    "test_geometry_wave1.py": [
        (
            "assert_float_close(self, normalize_vector_2d((3,4)), (0.6,0.8))",
            "assert_numeric_sequence_close(self, normalize_vector_2d((3,4)), (0.6,0.8))",
        ),
    ],
    "test_loads_wave1.py": [
        (
            "assert_float_close(self, load_vector(load), (10.0, 0.0, 0.0))",
            "assert_numeric_sequence_close(self, load_vector(load), (10.0, 0.0, 0.0))",
        ),
        (
            "assert_float_close(self, sum_load_vectors([a, b]), (3.0, 4.0, 0.0))",
            "assert_numeric_sequence_close(self, sum_load_vectors([a, b]), (3.0, 4.0, 0.0))",
        ),
    ],
    "test_materials_wave1.py": [
        (
            'assert_float_close(self, classify_material(masonry_material("M", 1800, 5000, 10, 0.5)), "masonry")',
            'self.assertEqual(classify_material(masonry_material("M", 1800, 5000, 10, 0.5)), "masonry")',
        ),
    ],
    "test_structural_wave1.py": [
        (
            "assert_float_close(self, reactions, (20.0, 20.0))",
            "assert_numeric_sequence_close(self, reactions, (20.0, 20.0))",
        ),
    ],
}


def ensure_sequence_import(content: str) -> str:
    single = (
        "from engineering_kernel.tests.numeric_assertions "
        "import assert_float_close\n"
    )
    combined = (
        "from engineering_kernel.tests.numeric_assertions "
        "import assert_float_close, assert_numeric_sequence_close\n"
    )
    if combined in content:
        return content
    if single in content:
        return content.replace(single, combined, 1)
    raise RuntimeError("Expected numeric assertion import was not found.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-root", required=True)
    args = parser.parse_args()

    tests_root = Path(args.tests_root).resolve()
    repairs = 0

    for filename, replacements in REPAIRS.items():
        path = tests_root / filename
        if not path.exists():
            raise FileNotFoundError(path)
        content = path.read_text(encoding="utf-8")
        sequence_needed = False

        for old, new in replacements:
            if new in content:
                continue
            if old not in content:
                raise RuntimeError(f"Expected v1.0 migration not found in {path}: {old}")
            content = content.replace(old, new, 1)
            repairs += 1
            if "assert_numeric_sequence_close" in new:
                sequence_needed = True

        if sequence_needed:
            content = ensure_sequence_import(content)

        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Repaired: {path}")

    print(f"Numerical Test Policy v1.1 repair complete: {repairs} repair(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
