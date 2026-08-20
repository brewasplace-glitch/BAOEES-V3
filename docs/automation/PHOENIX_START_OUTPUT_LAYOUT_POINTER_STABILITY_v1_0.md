# PROJECT PHOENIX — STARTSCREEN OUTPUT LAYOUT + POINTER STABILITY v1.0

## Baseline
Branch `project-phoenix`, exact HEAD `9dc0c4179b648e4589149aac36a0cb89d7e8b9cf`.

## User-facing change
On the official `/start-v3/` screen:
- `AUTONOME PHOENIX-FLOW` is placed beside `MIJN STANDAARD`;
- both choices are grouped directly beneath `GEWENSTE OUTPUT`;
- the pair remains responsive and stacks only on narrow screens.

## Pointer/flicker stabilization
The patch is intentionally additive. It adds no mousemove/pointermove listeners and no
MutationObserver. On fine-pointer devices it removes hover geometry/filter animation
from interactive cards while retaining color/background/border/opacity feedback.
The placement helper is finite and uses recursive `setTimeout`, stopping immediately
after the two output cards are positioned.

## Integration boundaries
DE TV player/mount files are not modified. Existing start-screen authentication and
architectural orchestration integration contracts are regression checked.

## Open-source-first review
Primary reference: Volt Bootstrap 5 Dashboard (MIT, vanilla JavaScript).
Alternative reference: Gentelella v4 (MIT, vanilla JavaScript).
Decision: no new runtime dependency. The required change is smaller and safer as native
HTML/CSS/DOM integration inside the existing Phoenix start screen.

Release status remains `CONCEPT ONLY / NOT FOR CONSTRUCTION`.
