"""Repair incorrectly migrated PEK numerical assertion call sites."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _is_exact_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (str, bytes, bool, int, type(None)))
        and not isinstance(node.value, float)
    )


def _is_numeric_sequence_literal(node: ast.AST) -> bool:
    if not isinstance(node, (ast.Tuple, ast.List)):
        return False
    if not node.elts:
        return False
    return all(
        isinstance(element, ast.Constant)
        and isinstance(element.value, (int, float))
        and not isinstance(element.value, bool)
        for element in node.elts
    )


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _absolute(offsets: list[int], line: int, column: int) -> int:
    return offsets[line - 1] + column


def repair_file(path: Path) -> tuple[int, int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    offsets = _line_offsets(source)
    replacements: list[tuple[int, int, str]] = []
    sequence_repairs = 0
    exact_repairs = 0

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "assert_float_close":
            continue
        if len(node.args) < 3:
            continue

        testcase = ast.get_source_segment(source, node.args[0])
        actual = ast.get_source_segment(source, node.args[1])
        expected = ast.get_source_segment(source, node.args[2])
        if testcase is None or actual is None or expected is None:
            raise RuntimeError(f"Could not read assertion call in {path}.")

        replacement: str | None = None

        if _is_numeric_sequence_literal(node.args[2]):
            replacement = (
                f"assert_numeric_sequence_close({testcase}, {actual}, {expected}"
            )
            for keyword in node.keywords:
                value = ast.get_source_segment(source, keyword.value)
                replacement += f", {keyword.arg}={value}"
            replacement += ")"
            sequence_repairs += 1

        elif _is_exact_literal(node.args[2]):
            if node.keywords:
                message = None
                for keyword in node.keywords:
                    if keyword.arg == "msg":
                        message = ast.get_source_segment(source, keyword.value)
                replacement = f"{testcase}.assertEqual({actual}, {expected}"
                if message is not None:
                    replacement += f", {message}"
                replacement += ")"
            else:
                replacement = f"{testcase}.assertEqual({actual}, {expected})"
            exact_repairs += 1

        if replacement is None:
            continue

        start = _absolute(offsets, node.lineno, node.col_offset)
        end = _absolute(offsets, node.end_lineno, node.end_col_offset)
        replacements.append((start, end, replacement))

    if not replacements:
        return 0, 0

    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]

    if sequence_repairs:
        single = (
            "from engineering_kernel.tests.numeric_assertions "
            "import assert_float_close\n"
        )
        combined = (
            "from engineering_kernel.tests.numeric_assertions "
            "import assert_float_close, assert_numeric_sequence_close\n"
        )
        if single in source and combined not in source:
            source = source.replace(single, combined, 1)

    path.write_text(source, encoding="utf-8", newline="\n")
    return sequence_repairs, exact_repairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-root", required=True)
    args = parser.parse_args()

    tests_root = Path(args.tests_root).resolve()
    total_sequence = 0
    total_exact = 0
    changed_files = 0

    for path in sorted(tests_root.glob("test_*.py")):
        sequence_repairs, exact_repairs = repair_file(path)
        if sequence_repairs or exact_repairs:
            changed_files += 1
            total_sequence += sequence_repairs
            total_exact += exact_repairs
            print(
                f"Repaired {path}: "
                f"{sequence_repairs} sequence, {exact_repairs} exact"
            )

    print(
        "Numeric assertion call-site repair complete: "
        f"{total_sequence} sequence repair(s), "
        f"{total_exact} exact repair(s), "
        f"{changed_files} file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
