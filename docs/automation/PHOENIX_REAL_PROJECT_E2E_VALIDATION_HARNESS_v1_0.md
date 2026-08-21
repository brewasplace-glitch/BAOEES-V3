# PROJECT PHOENIX — REAL-PROJECT END-TO-END VALIDATION HARNESS v1.0

## Bound baseline
`project-phoenix` @ `791be38ebcccea67f019f0a716c6691c98745ed4`

## Goal
Prepare the next real-project validation phase without silently choosing a project and
without weakening the current Phoenix release locks.

## Browser visual-evidence stack
Primary: **Playwright** (Apache-2.0). Evidence target: screenshots, video, trace,
console and network information.

Fallback: **Selenium WebDriver** (Apache-2.0). Use when Playwright is unavailable or
cannot drive the installed browser.

The harness installer only detects these backends. It does not auto-install either one.

## Validation chain prepared
1. Visual-stability evidence from the official start screen.
2. Explicit real-project identity.
3. A-E architectural variants.
4. Recommended variant.
5. Authoritative IFC.
6. FreeCAD processing.
7. Blender visual output.
8. DE TV project-scoped visual route.
9. Drawing-viewer evidence.
10. Real CalculiX execution when structural scope applies.
11. Raw solver evidence.
12. Normalized results.
13. Reports and delivery manifest.
14. BIB currentness.
15. Final SHA-256 evidence manifest.

## Hard visual gates
JSON does not count as visual proof. Blank images fail. Visual artifacts must be
project-scoped, and a viewer route must resolve to the actual underlying artifact.

## Release
Passing this harness or later E2E validation does not unlock production or
FOR CONSTRUCTION. Those remain locked under Phoenix release governance.
