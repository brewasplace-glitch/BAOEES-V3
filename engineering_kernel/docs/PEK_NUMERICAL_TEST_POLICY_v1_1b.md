# PEK Numerical Test Policy v1.1b

Version 1.1b repairs all remaining incompatible `assert_float_close` call sites
using an AST-based repository scan rather than hard-coded file and line edits.

Repairs are selected from the expected value:

- numeric tuple/list -> `assert_numeric_sequence_close`;
- string, bytes, boolean, integer or `None` -> `assertEqual`;
- scalar float -> remains `assert_float_close`;
- dynamic or unknown value -> remains unchanged.

A dedicated call-site checker now prevents future use of scalar float assertions
for explicit sequences or exact literals.
