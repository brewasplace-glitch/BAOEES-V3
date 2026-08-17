# PROJECT PHOENIX DE TV VISUAL-ONLY PRESENTATION + JSON SUPPRESSION REPAIR v1.0

Baseline: `9af2f4e407846d630a269fd6af69664ca78d0550`

## Problem

PAT-002 real Blender rendering is already operational. However, DE TV's legacy `PRESENTATIE` action
can still use the broad artifact carousel. That carousel contains technical files such as presentation
manifests, JSON state, evidence and adapter results.

This causes a visual artifact to appear briefly and then technical JSON to become the visible TV item.

## Repair

This repair adds a visual-only presentation controller loaded after the existing strict presentation
contract and PAT-002 Blender activation.

For `PHOENIX-PAT-002`, the core presentation begins with the real IFC-derived Blender artifacts:

1. exterior front;
2. exterior rear;
3. bird view;
4. interior cutaway.

Checked presentation outputs may then be appended when they resolve to visual media.

Technical artifacts are excluded, including JSON, text, logs, CSV/XML and manifest/evidence/state files.

## Internal carousel traversal

The existing exact-artifact bridge may internally step through the legacy artifact list while finding
a requested file. During that internal seek, the TV stage is masked and displays `Visuele output laden…`.
Therefore intermediate JSON/evidence artifacts cannot flash on screen.

## Authority

IFC remains authoritative geometry. Blender output remains presentation evidence. Production release stays LOCKED.
