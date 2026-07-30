# CalculiX MSYS2 Mirror and Retry Recovery v5.4.3

MSYS2 and the CalculiX package selection succeeded, but several redirected
third-party mirrors timed out. This recovery temporarily restricts pacman to
the official primary HTTPS server:

- `https://repo.msys2.org/mingw/$arch/`
- `https://repo.msys2.org/msys/$arch/`

The original mirrorlists are backed up. Existing package cache and partial
downloads remain available. Database refresh is retried three times and the
CalculiX package transaction five times, with fifteen seconds between attempts.

Repository rollback remains disabled before payload copy. A real C3D8 solve
with DAT and FRD output is still mandatory before commit and push.
