# PEK Numerical Test Policy v1.0

## Purpose

The Phoenix Engineering Kernel uses IEEE-754 floating-point arithmetic.
Mathematically equivalent decimal results can therefore differ in their final
binary digits. Exact equality is unsuitable for calculated engineering values.

## Mandatory rules

- `assertEqual` is prohibited when either comparison expression contains a
  floating-point literal.
- Scalar numerical results use `assert_float_close`.
- Numerical sequences use `assert_numeric_sequence_close`.
- Default tolerances are `rel_tol=1e-9` and `abs_tol=1e-12`.
- Kernel calculations are not rounded to make tests pass.
- Reporting and UI layers may apply explicit presentation rounding.
- Integers, strings, booleans, enums and metadata retain exact equality.

## Enforcement

`check_numeric_test_policy.py` scans the complete PEK test suite and fails the
build when unsafe floating-point equality is introduced.

`migrate_numeric_assertions.py` performs a syntax-aware migration of existing
`unittest.TestCase.assertEqual` float assertions while preserving the original
calculation and expected value.
