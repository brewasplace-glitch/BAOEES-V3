"""Enforce PEK Numerical Test Policy v1.1 with type-aware expectations."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _is_float_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, float)
        and not isinstance(node.value, bool)
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


def _requires_tolerant_comparison(expected: ast.AST) -> bool:
    """Return True only when the expected value is explicitly numerical."""
    return _is_float_literal(expected) or _is_numeric_sequence_literal(expected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-root", required=True)
    args = parser.parse_args()

    tests_root = Path(args.tests_root).resolve()
    violations: list[str] = []

    for path in sorted(tests_root.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "assertEqual":
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "self":
                continue
            if len(node.args) < 2:
                continue

            expected = node.args[1]
            if _requires_tolerant_comparison(expected):
                violations.append(
                    f"{path}:{node.lineno}: assertEqual cannot be used for "
                    "explicit float or numeric-sequence expectations"
                )

    if violations:
        print("PEK Numerical Test Policy FAILED")
        for violation in violations:
            print(f"  {violation}")
        return 1

    print("PEK Numerical Test Policy PASSED")
    print("Unsafe explicit float equality assertions: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
