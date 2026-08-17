# PROJECT PHOENIX DE TV DIRECT AUTHORITATIVE PNG RENDER BRIDGE + RESPONSIVE CONTROL BAR REPAIR v1.0

Baseline: `8e9c49234ca4558583e84edfff4b5f8432d9e830`.

This repair addresses the two observed post-router defects together:

1. PAT-002 routing reaches the correct Blender visual but DE TV can remain masked at `Visuele output laden...`.
2. The enlarged TV stage can push PRESENTATIE / VORIGE / VOLGENDE / command controls below the browser viewport.

The final TV layer directly renders the four authoritative PAT-002 Blender PNG files into the TV stage.
It keeps the existing exact-artifact bridge only as a compatibility fallback. The stage height is calculated
from the current browser viewport with reserved space for the controls, and recalculated on resize/fullscreen.

PAT-002 presentation remains limited to exterior front, exterior rear, bird view and interior cutaway.
JSON, manifests, evidence and legacy schematic presentation HTML are not presentation media.
IFC remains authoritative geometry. Production release remains LOCKED.
