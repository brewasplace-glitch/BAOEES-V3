"""Central numerical assertions for the Phoenix Engineering Kernel test suite."""

from __future__ import annotations

import math
from collections.abc import Sequence
from numbers import Real
from typing import Any


DEFAULT_REL_TOL = 1e-9
DEFAULT_ABS_TOL = 1e-12


def assert_float_close(
    testcase: Any,
    actual: Real,
    expected: Real,
    *,
    rel_tol: float = DEFAULT_REL_TOL,
    abs_tol: float = DEFAULT_ABS_TOL,
    msg: str | None = None,
) -> None:
    """Assert that two finite or infinite real numbers are numerically close."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        testcase.fail(msg or "Boolean values must use assertEqual/assertIs.")
    if not isinstance(actual, Real) or not isinstance(expected, Real):
        testcase.fail(
            msg
            or f"Numerical comparison requires real numbers, got "
               f"{type(actual).__name__} and {type(expected).__name__}."
        )

    actual_value = float(actual)
    expected_value = float(expected)

    if math.isnan(actual_value) or math.isnan(expected_value):
        testcase.fail(msg or f"NaN cannot be compared: {actual_value!r}, {expected_value!r}")

    if math.isclose(
        actual_value,
        expected_value,
        rel_tol=rel_tol,
        abs_tol=abs_tol,
    ):
        return

    delta = abs(actual_value - expected_value)
    testcase.fail(
        msg
        or (
            f"{actual_value!r} != {expected_value!r}; "
            f"delta={delta!r}, rel_tol={rel_tol!r}, abs_tol={abs_tol!r}"
        )
    )


def assert_numeric_sequence_close(
    testcase: Any,
    actual: Sequence[Real],
    expected: Sequence[Real],
    *,
    rel_tol: float = DEFAULT_REL_TOL,
    abs_tol: float = DEFAULT_ABS_TOL,
    msg: str | None = None,
) -> None:
    """Assert equal length and numerical closeness for two real-number sequences."""
    testcase.assertEqual(len(actual), len(expected), msg)
    for index, (actual_value, expected_value) in enumerate(zip(actual, expected)):
        assert_float_close(
            testcase,
            actual_value,
            expected_value,
            rel_tol=rel_tol,
            abs_tol=abs_tol,
            msg=msg or f"Numerical sequence differs at index {index}.",
        )
