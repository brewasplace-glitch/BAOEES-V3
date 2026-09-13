# PHOENIX 4.41 — Startscreen Idle Stability + Non-Intrusive CAD Observer v1.0

Baseline: `5facd3b88c4e5d4ddcc23b4ad67f09738d937eb6`

## Proven symptom

After DXF and DWG became functional in DE TV, the Phoenix start screen still
flickered and made switching/opening other Windows programs difficult.

## Root-cause candidate removed

The DE TV bridge previously installed a permanent MutationObserver on
`document.documentElement` with:

- `childList: true`
- `subtree: true`
- `characterData: true`

Every mutation scheduled a complete `activate()` pass, which rescanned the full
document, repaired text, synchronized version labels, rechecked CAD controls and
performed a health request. A 15-second permanent health interval also remained
active when Phoenix was hidden.

## Repair

- full-document text/version repair runs once at bootstrap;
- no permanent characterData observation;
- MutationObserver is childList-only and exists only for short bounded
  bootstrap/navigation windows;
- observer disconnects immediately after CAD controls are mounted or when its
  time window expires;
- relevant navigation clicks/popstate/hashchange/pageshow may briefly re-arm it;
- health uses a 60-second timeout chain, not setInterval;
- health and observer activity stop while `document.hidden` is true;
- no focus/foreground activation is introduced;
- working DXF/DWG rendering, hard-mount, CORS and LibreCAD fallback are untouched.

## Open-source-first review

`dom-mutations` (MIT) and `mutation-summary` (Apache-2.0) were reviewed. Both
ultimately wrap MutationObserver. Phoenix therefore uses the browser-native
MutationObserver and Page Visibility APIs directly to avoid adding a dependency
for a narrow lifecycle fix.
