# PROJECT PHOENIX 4.41 — LOW-RISK AUTONOMOUS MAINLINE PROMOTION v1.0

Installation baseline: `df600d70b453152baa70ee28876605149dc65a27`

Only existing PHOENIX LOW-risk candidates may be promoted. A verified full backup receipt for the exact baseline is mandatory. Candidates must be exactly one commit ahead, use `auto/lowrisk-low-*`, change only allowed LOW-risk `.md`, `.txt` or `.json` files, contain only add/modify statuses, and pass `git diff --check`.

Primary promotion mechanism: native Git `merge --ff-only`. Push is normal non-force. MEDIUM, HIGH and CRITICAL remain blocked.

The backup gate creates a full filesystem snapshot plus `git bundle create --all` and verifies the bundle. Default backup root: `C:\PXBK`.


## FIX R3 — BIB governance side-effect awareness

The interrupted candidate can contain the intended LOW-risk mutation plus
deterministic BIB auto-sync files written by the existing pre-commit governance
hook.

FIX R3 permits only these exact governance side-effect paths:

- `bib/PHOENIX_AUTO_SYNC/BIB_BASELINE.md`
- `bib/PHOENIX_AUTO_SYNC/BIB_CURRENT_STATE.json`
- `bib/PHOENIX_AUTO_SYNC/BIB_DISCOVERED_KNOWLEDGE_ROOTS.json`
- `bib/PHOENIX_AUTO_SYNC/BIB_GIT_HISTORY.jsonl`
- `bib/PHOENIX_AUTO_SYNC/BIB_KNOWLEDGE_FALLBACK.jsonl`
- `bib/PHOENIX_AUTO_SYNC/BIB_MANIFEST.json`
- `bib/PHOENIX_AUTO_SYNC/BIB_SYNC_EVIDENCE.txt`
- `bib/PHOENIX_AUTO_SYNC/README.md`

At least one normal LOW-risk mutation remains mandatory. Governance files do
not widen the normal LOW-risk roots. Unknown BIB paths, source-code changes,
deletes, renames, excessive file sizes, malformed JSON/JSONL, multiple candidate
commits, or non-fast-forward ancestry remain hard blockers.

## FIX R4 — PowerShell 5.1 parser-safe source gate

FIX R3 stopped before execution because its ff-only source-gate regex used C-style `\"` quote escaping. FIX R4 uses a single-quoted PowerShell literal with `.Contains()` instead. The baseline remains `df600d70b453152baa70ee28876605149dc65a27`.


## FIX R5 — explicit UTF-8 Git subprocess decoding on Windows

FIX R4 reached candidate content validation and then failed before mainline
mutation because Python's default Windows text decoding used cp1252 for
`git show`. A valid UTF-8 byte sequence containing byte `0x9d` could therefore
raise `UnicodeDecodeError`.

FIX R5 makes promoter Git subprocess output explicitly UTF-8 with strict
decoding. A regression test writes U+011D (`ĝ`), whose UTF-8 representation is
`C4 9D`, into an allowed governance JSON file and proves that validation and
promotion succeed.

The expected pre-promotion baseline remains `df600d70b453152baa70ee28876605149dc65a27`.
