# Phoenix Architectural Defensive Writer Test Alignment Recovery v6.5.2

## Confirmed failure

The defensive directory logic in v6.5.1 was present, but one unit test searched
for a formatted source fragment containing a literal escaped newline. The test
therefore failed even though the implementation was correct.

## Recovery

v6.5.2 uses Python AST analysis instead of source formatting assumptions.

The tests now verify semantically that:

- `svg_plan` calls `path.parent.mkdir(...)`;
- `svg_elevation` calls `path.parent.mkdir(...)`;
- `svg_section` calls `path.parent.mkdir(...)`;
- `generate_freecad` calls `output.mkdir(...)`;
- `generate_ifc` calls `output.mkdir(...)`;
- required generated artifacts are checked for existence and non-zero size.

The architectural generator, release gates and professional-approval rules are
unchanged.
