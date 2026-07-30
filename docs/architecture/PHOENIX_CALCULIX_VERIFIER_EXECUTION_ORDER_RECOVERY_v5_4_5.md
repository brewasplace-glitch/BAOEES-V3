# CalculiX Verifier Execution Order Recovery v5.4.5

MSYS2 and CalculiX 2.23-1 are already installed. v5.4.4 failed because it
invoked the package verifier through a repository-relative path before the
payload had been copied into the repository.

v5.4.5 invokes the verifier directly from the extracted installer payload,
keeps the repository untouched during external package verification, and only
then copies the payload. Real C3D8, DAT, FRD, detector, commit, push and clean
synchronization gates remain mandatory.
