# CalculiX MSYS2 Install and Rollback Recovery v5.4.2

v5.4.1 failed because the non-versioned MSYS2 `latest.exe.sha256` URL returned
HTTP 404. Its catch block then removed repository targets even though payload
copy had not started.

v5.4.2 uses:
- Windows Package Manager package `MSYS2.MSYS2` as primary route;
- the official HTTPS MSYS2 installer as fallback;
- valid Authenticode signature as the fallback trust gate;
- no request to the missing `.sha256` URL;
- repository rollback only after payload copy begins;
- preservation of `engines.py` on all external installation failures.

CalculiX remains installed through
`mingw-w64-x86_64-calculix-ccx`, followed by a real C3D8 DAT/FRD acceptance.
