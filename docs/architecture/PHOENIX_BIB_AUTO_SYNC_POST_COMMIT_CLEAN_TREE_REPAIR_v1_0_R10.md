# PROJECT PHOENIX BIB AUTO-SYNC POST-COMMIT CLEAN-TREE REPAIR v1.0 R10

Baseline `6b08a98dc2a1fabfd3d5516aa2207107233bec15`.

R9 correctly canonicalized the managed Git root to `bib/PHOENIX_AUTO_SYNC`.
It stopped only because one new regression assumed a case-sensitive filesystem.
On Windows, a path spelled `BIB/...` can still resolve the actual `bib/...` directory.

R10 checks the actual directory-entry name instead of using a negative `Path.exists()`
assertion with different case. R10 also recovers only the known R9 installer-owned
leftovers before requiring a clean baseline and retrying the repair.
