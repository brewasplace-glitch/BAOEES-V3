# Phoenix Package Manager v1.0.0

## Purpose

PPM is the permanent installation engine for Project Phoenix packages.

Future updates use a `.phx` ZIP package containing:

- `manifest.json`;
- `payload/`;
- optional package evidence.

## Guarantees

- normal package installation starts only from a clean repository;
- paths are validated before use;
- shell execution is disabled;
- syntax and declared tests run before commit;
- both Git diff checks are mandatory;
- commit and push occur only after all checks pass;
- the final repository must be clean.

## Recovery

This release includes a one-time standalone recovery bootstrap for the
interrupted BB1 installers. The bootstrap executes directly from the extracted
package and does not import uninstalled repository modules.
