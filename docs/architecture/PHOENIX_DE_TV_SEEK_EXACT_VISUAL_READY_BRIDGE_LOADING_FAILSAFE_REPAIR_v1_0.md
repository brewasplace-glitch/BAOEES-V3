# PROJECT PHOENIX DE TV SEEK-EXACT VISUAL-READY BRIDGE + LOADING FAILSAFE REPAIR v1.0

Baseline: `1564c2b9b4c00c9af3e7c4a3ef2c495f51fbc195`.

The previous direct-PNG repair guessed HTTP artifact endpoints. The observed Phoenix runtime remained at
`Visuele output laden...`, proving that those guessed endpoints are not the authoritative delivery path.

This repair removes all guessed direct HTTP artifact URLs. It uses the already proven
`seekExactArtifact(path)` bridge exclusively.

The TV stage stays hidden during internal legacy-index traversal. A MutationObserver plus polling waits
until actual visual DOM content (image, canvas, video, iframe, SVG/object/embed, or rendered background)
exists. The loading mask is released only after that visual-ready gate passes.

Both the seek operation and the visual-ready wait have hard timeouts. Therefore the TV cannot remain
permanently stuck on `Visuele output laden...`.

The normal TV stage is also capped lower so the control row remains inside the browser viewport.

PAT-002 remains limited to the four real IFC-derived Blender PNG presentation artifacts.
IFC remains authoritative geometry. Production release remains LOCKED.
