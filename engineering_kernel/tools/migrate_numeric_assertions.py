"""Type-aware migration for PEK unittest numerical assertions."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


FLOAT_IMPORT = (
    "from engineering_kernel.tests.numeric_assertions "
    "import assert_float_close, assert_numeric_sequence_close\n"
)


def _is_float_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, float)
        and not isinstance(node.value, bool)
    )


def _is_exact_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(
        node.value, (str, bytes, bool, int, type(None))
    ) and not _is_float_literal(node)


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


def _contains_float_literal(node: ast.AST) -> bool:
    return any(_is_float_literal(child) for child in ast.walk(node))


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _absolute(offsets: list[int], line: int, column: int) -> int:
    return offsets[line - 1] + column


def _replacement_kind(left: ast.AST, right: ast.AST) -> str | None:
    # Exact literal expectations remain exact, even when the evaluated expression
    # internally contains float literals.
    if _is_exact_literal(right):
        return None

    if _is_numeric_sequence_literal(right):
        return "sequence"

    # Scalar migration is only safe when the expected side is explicitly float.
    if _is_float_literal(right):
        return "scalar"

    # Preserve unknown or composite types rather than guessing.
    return None


def migrate_file(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    offsets = _line_offsets(source)
    replacements: list[tuple[int, int, str]] = []
    needs_import = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "assertEqual":
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "self":
            continue
        if len(node.args) not in (2, 3) or node.keywords:
            continue

        kind = _replacement_kind(node.args[0], node.args[1])
        if kind is None:
            continue

        first = ast.get_source_segment(source, node.args[0])
        second = ast.get_source_segment(source, node.args[1])
        if first is None or second is None:
            raise RuntimeError(f"Could not read assertion arguments in {path}.")

        helper = (
            "assert_numeric_sequence_close"
            if kind == "sequence"
            else "assert_float_close"
        )
        replacement = f"{helper}(self, {first}, {second}"
        if len(node.args) == 3:
            third = ast.get_source_segment(source, node.args[2])
            replacement += f", msg={third}"
        replacement += ")"

        start = _absolute(offsets, node.lineno, node.col_offset)
        end = _absolute(offsets, node.end_lineno, node.end_col_offset)
        replacements.append((start, end, replacement))
        needs_import = True

    if not replacements:
        return 0

    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]

    if needs_import and FLOAT_IMPORT not in source:
        old_import = (
            "from engineering_kernel.tests.numeric_assertions "
            "import assert_float_close\n"
        )
        if old_import in source:
            source = source.replace(old_import, FLOAT_IMPORT, 1)
        else:
            lines = source.splitlines(keepends=True)
            insert_at = 0
            if lines and lines[0].startswith("#!"):
                insert_at = 1
            while insert_at < len(lines) and (
                lines[insert_at].startswith("#")
                or not lines[insert_at].strip()
            ):
                insert_at += 1
            if insert_at < len(lines) and lines[insert_at].startswith("from __future__ import"):
                insert_at += 1
                while insert_at < len(lines) and not lines[insert_at].strip():
                    insert_at += 1
            lines.insert(insert_at, FLOAT_IMPORT)
            source = "".join(lines)

    path.write_text(source, encoding="utf-8", newline="\n")
    return len(replacements)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-root", required=True)
    args = parser.parse_args()

    tests_root = Path(args.tests_root).resolve()
    total = 0
    changed_files = 0

    for path in sorted(tests_root.glob("test_*.py")):
        count = migrate_file(path)
        if count:
            changed_files += 1
            total += count
            print(f"Migrated {count} assertion(s): {path}")

    print(
        f"Type-aware numeric assertion migration complete: "
        f"{total} assertion(s), {changed_files} file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
