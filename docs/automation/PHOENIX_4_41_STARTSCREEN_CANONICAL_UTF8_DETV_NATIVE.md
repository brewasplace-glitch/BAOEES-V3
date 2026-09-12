# PHOENIX 4.41 — Official Startscreen Canonicalization + UTF-8 Repair + Native DE TV CAD

## Baseline

`b1da9593850c9cf9a500c0200e810d5986a5000f`

## Problem proven by visual test

The browser is serving `/start-v3/` from:

`phoenix/local_app/static/official_start_v3_0/index.html`

The page still displays PHOENIX 3.0.2 / START v3.0.2 branding and multiple
mojibake sequences such as `ðŸŽ¤`. The CAD bridge works, but its controls were
rendered as floating buttons at the bottom-right instead of being native DE TV
controls.

## Repair

1. Treat the actually served `official_start_v3_0/index.html` as the canonical
   current shell rather than inventing an unproven route.
2. Repair mojibake in the canonical start directory with `ftfy.fix_encoding`.
3. Use charset-normalizer only as a decoding fallback when a source file is not
   valid UTF-8.
4. Write repaired files as UTF-8 without BOM.
5. Canonicalize visible PHOENIX 3.x start branding to PHOENIX 4.41.
6. Add cache-busting to the CAD bridge script reference.
7. Replace floating CAD controls with controls mounted inside the DE TV panel.
8. Add a runtime text-node sanitizer for labels generated after initial page load.
9. Preserve the existing CAD sidecar, LibreCAD, LibreDWG and ezdxf stack.

## Safety

The build does not change structural release status, engineering evidence, or
construction-release gates.


## FIX R1 — scoped floating-toolbar verification

The first real run successfully repaired the canonical start screen from 40 known
mojibake markers to zero and changed the visible PHOENIX 3.x branding to
PHOENIX 4.41.

The run then stopped on a false-positive verifier. It searched the entire native
CAD bridge for `position:fixed`, while the full-screen CAD modal is intentionally
fixed. Only the old floating CAD toolbar is prohibited.

FIX R1 scopes the CSS gate specifically to the `#phoenix-cad-toolbar` block:
- `position:fixed` is forbidden for the toolbar;
- `position:static!important` is required for the toolbar;
- the CAD modal may remain fixed.
