# PEK Numerical Test Policy v1.1a

This maintenance release corrects the policy checker.

The v1.1 checker inspected float literals anywhere inside an `assertEqual`
expression. That incorrectly rejected exact string comparisons when the
calculation itself accepted floating-point inputs.

The checker now inspects only the expected value:

- explicit float expectation: rejected;
- explicit numeric tuple/list expectation: rejected;
- string, integer, boolean, bytes or `None` expectation: allowed;
- dynamic or unknown expectation: left exact.

Dedicated checker regression tests prevent recurrence.
