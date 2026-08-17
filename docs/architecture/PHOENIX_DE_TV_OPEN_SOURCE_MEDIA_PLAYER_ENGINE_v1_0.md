# PROJECT PHOENIX DE TV OPEN-SOURCE MEDIA PLAYER ENGINE v1.0

Required baseline: `4908669b0e63eb2f37b690fea48a41ade9cfea9f`.

## Architecture change

DE TV no longer depends on the general Phoenix artifact carousel to serve presentation media.

A dedicated local media-player service runs on `127.0.0.1:8770` and safely serves only files under
approved Phoenix roots. Path traversal outside those roots is denied.

The official start screen mounts a dedicated player iframe. That player owns:

- presentation playback;
- previous / next;
- fullscreen;
- natural-language `toon ...` commands;
- image display and media-ready behavior.

PAT-002 uses only the four real IFC-derived Blender PNG presentation files.

## Open-source engine foundation

Phoenix provisions the Xibo Player SDK packages:

- `@xiboplayer/renderer` 0.7.23
- `@xiboplayer/proxy` 0.7.23

Xibo Player SDK is licensed AGPL-3.0-or-later. Phoenix records this dependency and keeps the integration
isolated under `phoenix/media_player/xibo_sdk`.

v1.0 deliberately keeps Phoenix project semantics and command mapping in a thin adapter while moving
media serving and player ownership out of the historical DE TV artifact browser. This is the migration
foundation for using Xibo's renderer/proxy capabilities instead of expanding Phoenix's legacy TV stack.

## Security

The local media server binds only to `127.0.0.1`.
Only project/runtime, outputs, and the player web directory are eligible roots.
No arbitrary filesystem path can be served.

Production release remains LOCKED.
