# Project Phoenix v8.4 â€” CalculiX Set Line Wrap FIXED R4 Masterpack v1.0

## Purpose

PHOENIX-PAT-001 reached the real CalculiX executable but LC-G stopped with exit code 201.

Runtime evidence identified the parser error:

`*ERROR in splitline: there should not be more than 16 entries in a line`

The generated v8.3 deck wrote the complete `*NSET, NSET=NALL` set of 91 node IDs on one data line.

## R4 correction

R4 changes the v8.3 CalculiX deck writer so that set data is emitted in deterministic chunks of at most 16 entries per line.

The correction is intentionally generic:

- `_calculix_id_lines(...)` wraps arbitrary set IDs to the CalculiX entry limit.
- `NALL` uses the shared wrapping helper.
- `_validate_calculix_data_line_width(...)` rejects any generated CalculiX data record containing more than 16 comma-separated entries.
- Regression coverage includes 16, 17 and 91 IDs.
- Existing v8.3 and v8.4 structural/CalculiX tests remain part of the installer gate.
- The full Phoenix regression suite remains mandatory before commit and push.

## Safety / release behavior

This fix does not enable:

- automatic code-compliance claims;
- automatic professional approval;
- for-construction release;
- production release.

Those gates remain controlled by the existing evidence and release framework.

## Expected PAT result

After installation, rerun PHOENIX-PAT-001 with `GECERTIFICEERD` unchecked.

The immediate acceptance target is that LC-G no longer fails because `NALL` exceeds the CalculiX 16-entry data-line limit. Any subsequent solver, engineering, QA/QC, or desired-output blocker must remain explicit and must not be bypassed.