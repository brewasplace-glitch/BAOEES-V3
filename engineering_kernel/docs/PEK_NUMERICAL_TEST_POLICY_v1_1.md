# PEK Numerical Test Policy v1.1

Version 1.1 makes the migration process type-aware.

## Migration decisions

- Expected scalar float: `assert_float_close`.
- Expected numeric tuple/list: `assert_numeric_sequence_close`.
- Expected string, boolean, integer, bytes or `None`: retain `assertEqual`.
- Unknown or dynamic expected type: retain `assertEqual`.

The key safety rule is that the migrator must not infer a scalar numerical type
from float literals that merely occur inside the calculation expression.

Version 1.1 also repairs the six unsafe v1.0 migrations discovered by the full
regression suite and adds dedicated migrator regression tests.
