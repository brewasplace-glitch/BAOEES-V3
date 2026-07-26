"""Restricted syntax validator for executable BB17 rule expressions."""

from __future__ import annotations

import ast


class UnsafeRuleDefinition(ValueError):
    pass


_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.List,
    ast.Tuple,
)

_ALLOWED_FUNCTIONS = {
    "value",
    "exists",
    "count",
    "not_empty",
    "all_have",
    "unique",
    "equals",
    "references_exist",
    "positive_or_empty",
    "nonnegative_or_empty",
    "relationships_valid",
    "param",
}


def validate_expression(expression: str) -> None:
    if not isinstance(expression, str) or not expression.strip():
        raise UnsafeRuleDefinition("Rule expression must not be empty.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeRuleDefinition(f"Invalid expression syntax: {exc.msg}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeRuleDefinition(
                f"Unsupported expression syntax: {type(node).__name__}"
            )
        if isinstance(node, ast.Name) and node.id not in _ALLOWED_FUNCTIONS:
            raise UnsafeRuleDefinition(f"Unknown rule helper: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise UnsafeRuleDefinition("Only direct helper calls are allowed.")
            if node.func.id not in _ALLOWED_FUNCTIONS:
                raise UnsafeRuleDefinition(
                    f"Function is not allowed: {node.func.id}"
                )
            if node.keywords:
                raise UnsafeRuleDefinition(
                    "Keyword arguments are not allowed in rule expressions."
                )
