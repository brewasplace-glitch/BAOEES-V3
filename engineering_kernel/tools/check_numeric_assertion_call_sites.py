"""Validate that PEK numerical assertion helpers receive compatible types."""

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
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "assert_float_close":
                continue
            if len(node.args) < 3:
                continue

            expected = node.args[2]
            if _is_numeric_sequence_literal(expected):
                violations.append(
                    f"{path}:{node.lineno}: assert_float_close used for numeric sequence"
                )
            elif _is_exact_literal(expected):
                violations.append(
                    f"{path}:{node.lineno}: assert_float_close used for exact literal"
                )

    if violations:
        print("PEK Numerical Assertion Call-Site Check FAILED")
        for violation in violations:
            print(f"  {violation}")
        return 1

    print("PEK Numerical Assertion Call-Site Check PASSED")
    print("Incompatible assert_float_close call sites: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
