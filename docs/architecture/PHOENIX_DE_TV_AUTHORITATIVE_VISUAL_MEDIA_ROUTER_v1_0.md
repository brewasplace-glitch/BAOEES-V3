# PROJECT PHOENIX DE TV AUTHORITATIVE VISUAL MEDIA ROUTER v1.0

Required baseline:

`86c474d5a96660198d142fed1b80cf4c55622e51`

## Problem

The previous DE TV stack could generate and open real PAT-002 Blender renders, but runtime navigation
still fell through to legacy broad artifact lists. As a result:

- PRESENTATIE could show legacy schematic walkthrough/drive-through HTML;
- VORIGE/VOLGENDE could land on JSON manifests and adapter results;
- exact visual paths could be interpreted as natural-language commands;
- older document-level handlers could override later semantic routing.

## Authority model

This pack adds one final DE TV runtime controller loaded after all existing TV layers.

For `PHOENIX-PAT-002`, the authoritative visual catalog contains exactly four current presentation
artifacts:

1. `phoenix_exterior_front.png`
2. `phoenix_exterior_rear.png`
3. `phoenix_bird_view.png`
4. `phoenix_interior_cutaway.png`

Legacy BIM-Lite walkthrough, drive-through and auto-video HTML are deliberately excluded from this
authoritative PAT-002 presentation catalog. They remain repository evidence but are no longer the
primary architectural presentation.

## Runtime ownership

The router listens at `window` capture phase for:

- PRESENTATIE;
- VORIGE;
- VOLGENDE;
- TOON;
- Enter in the TV command input.

When the active project has an authoritative catalog, handled events call `preventDefault()` and
`stopImmediatePropagation()`. This prevents older document-level DE TV handlers from reprocessing a
command or moving into the broad technical artifact list.

## Command contract

For PAT-002:

- `toon ontwerp` -> exterior front;
- `toon exterieur` -> exterior front;
- `toon variant B` -> exterior front;
- `toon 3D` -> exterior front presentation render;
- `toon interieur` -> interior cutaway;
- `toon vogelvlucht` -> bird view;
- `toon achterzijde` / `toon achtergevel` -> exterior rear.

Exact known visual paths are also accepted, with or without the `toon ` prefix.

## Presentation behavior

PRESENTATIE starts with the first authoritative visual and advances every seven seconds.
VORIGE and VOLGENDE use the same four-item catalog.

Technical artifacts are never part of this catalog.

The existing exact-artifact bridge may internally traverse its historical index to locate the requested
file. During that operation the TV stage is masked with `Visuele output laden...`, so intermediate
JSON/evidence artifacts cannot become presentation content.

## Scope

v1.0 gives PAT-002 an explicit authoritative visual catalog. Other projects are not silently assigned a
catalog until their visual-output contracts are defined.

IFC remains authoritative geometry. Blender PNG files remain presentation evidence. Production release
remains LOCKED.
