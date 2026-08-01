# Phoenix Detailed Architectural Wall Schedule Test Path Alignment Recovery v6.6.3

## Confirmed failure

The v6.6.2 wall-schedule implementation passed the real pre-payload generation.
Four newly added tests then failed because they referenced `RUNNER`, while the
existing test module defined the runner path as `X`.

## Recovery

v6.6.3 normalizes the test module to these canonical aliases:

- `ROOT = R`;
- `RUNNER = X`.

All existing tests remain intact. Two additional guard tests verify that the
aliases exist and resolve to the actual repository runner.

The wall schedule schema, coordinate export, deterministic host-space
serialization, strict CSV validation, detailed architectural engine and
release gates are unchanged.
