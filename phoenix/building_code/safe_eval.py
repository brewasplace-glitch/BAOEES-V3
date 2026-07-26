"""Restricted expression evaluator for BB17 rules."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Callable, Mapping


class UnsafeRuleExpression(ValueError):
    """Raised when a rule expression contains unsupported syntax."""


_MISSING = object()


@dataclass(slots=True)
class ModelQuery:
    model: Mapping[str, Any]
    parameters: Mapping[str, Any]

    def value(self, path: str, default: Any = None) -> Any:
        current: Any = self.model
        if not path:
            return current
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return default
        return current

    def exists(self, path: str) -> bool:
        return self.value(path, _MISSING) is not _MISSING

    def count(self, path: str) -> int:
        target = self.value(path, ())
        try:
            return len(target)
        except TypeError:
            return 0

    def not_empty(self, path: str) -> bool:
        target = self.value(path, _MISSING)
        if target is _MISSING or target is None:
            return False
        if isinstance(target, str):
            return bool(target.strip())
        try:
            return len(target) > 0
        except TypeError:
            return True

    def all_have(self, path: str, key: str) -> bool:
        collection = self.value(path, ())
        if not isinstance(collection, list):
            return False
        return all(
            isinstance(item, Mapping)
            and key in item
            and item[key] not in (None, "")
            for item in collection
        )

    def unique(self, path: str, key: str) -> bool:
        collection = self.value(path, ())
        if not isinstance(collection, list):
            return False
        values: list[Any] = []
        for item in collection:
            if not isinstance(item, Mapping) or key not in item:
                return False
            values.append(item[key])
        try:
            return len(values) == len(set(values))
        except TypeError:
            return False

    def equals(self, path: str, expected: Any) -> bool:
        return self.value(path, _MISSING) == expected

    def references_exist(
        self,
        source_path: str,
        source_key: str,
        target_path: str,
        target_key: str,
        allow_empty: bool = False,
    ) -> bool:
        sources = self.value(source_path, ())
        targets = self.value(target_path, ())
        if not isinstance(sources, list) or not isinstance(targets, list):
            return False
        target_values = {
            item.get(target_key)
            for item in targets
            if isinstance(item, Mapping) and target_key in item
        }
        for source in sources:
            if not isinstance(source, Mapping) or source_key not in source:
                return False
            reference = source.get(source_key)
            if allow_empty and reference in (None, ""):
                continue
            if reference not in target_values:
                return False
        return True

    def positive_or_empty(self, path: str, key: str) -> bool:
        collection = self.value(path, ())
        if not isinstance(collection, list):
            return False
        for item in collection:
            if not isinstance(item, Mapping):
                return False
            number = item.get(key)
            if number in (None, ""):
                continue
            if isinstance(number, bool) or not isinstance(number, (int, float)) or number <= 0:
                return False
        return True

    def nonnegative_or_empty(self, path: str, key: str) -> bool:
        collection = self.value(path, ())
        if not isinstance(collection, list):
            return False
        for item in collection:
            if not isinstance(item, Mapping):
                return False
            number = item.get(key)
            if number in (None, ""):
                continue
            if isinstance(number, bool) or not isinstance(number, (int, float)) or number < 0:
                return False
        return True

    def relationships_valid(self) -> bool:
        known_ids: set[Any] = set()
        for path in ("levels", "spaces", "elements"):
            collection = self.value(path, ())
            if not isinstance(collection, list):
                return False
            for item in collection:
                if isinstance(item, Mapping) and "id" in item:
                    known_ids.add(item["id"])
        relationships = self.value("relationships", ())
        if not isinstance(relationships, list):
            return False
        return all(
            isinstance(item, Mapping)
            and item.get("source_id") in known_ids
            and item.get("target_id") in known_ids
            and bool(str(item.get("type", "")).strip())
            for item in relationships
        )

    def param(self, name: str, default: Any = None) -> Any:
        return self.parameters.get(name, default)


_ALLOWED = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Call, ast.Name, ast.Load, ast.Constant,
    ast.List, ast.Tuple,
)


class SafeExpressionEvaluator:
    """Evaluate only whitelisted helper calls and boolean comparisons."""

    def __init__(self, model: Mapping[str, Any], parameters: Mapping[str, Any] | None = None) -> None:
        query = ModelQuery(model, parameters or {})
        self.functions: dict[str, Callable[..., Any]] = {
            "value": query.value,
            "exists": query.exists,
            "count": query.count,
            "not_empty": query.not_empty,
            "all_have": query.all_have,
            "unique": query.unique,
            "equals": query.equals,
            "references_exist": query.references_exist,
            "positive_or_empty": query.positive_or_empty,
            "nonnegative_or_empty": query.nonnegative_or_empty,
            "relationships_valid": query.relationships_valid,
            "param": query.param,
        }

    def evaluate(self, expression: str) -> bool:
        if not expression or not expression.strip():
            raise UnsafeRuleExpression("Rule expression must not be empty.")
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise UnsafeRuleExpression(f"Invalid rule syntax: {exc.msg}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED):
                raise UnsafeRuleExpression(
                    f"Unsupported expression syntax: {type(node).__name__}"
                )
            if isinstance(node, ast.Name) and node.id not in self.functions:
                raise UnsafeRuleExpression(f"Unknown rule function: {node.id}")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in self.functions:
                    raise UnsafeRuleExpression("Only registered helper calls are allowed.")
                if node.keywords:
                    raise UnsafeRuleExpression("Keyword arguments are not allowed.")
        result = eval(
            compile(tree, "<bb17-rule>", "eval"),
            {"__builtins__": {}},
            dict(self.functions),
        )
        if not isinstance(result, bool):
            raise UnsafeRuleExpression("Rule expression must evaluate to boolean.")
        return result
