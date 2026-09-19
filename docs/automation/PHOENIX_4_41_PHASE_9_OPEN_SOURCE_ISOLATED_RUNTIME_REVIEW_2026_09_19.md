# PROJECT PHOENIX 4.41 — Phase 9 Open-Source Isolation Review

Reviewed: 2026-09-19

## Primary — Podman Machine

Podman is open source under Apache-2.0. On Windows it runs the container engine
inside a Linux virtual machine using WSL 2 or Hyper-V. Phase 9 admits it only
when the active connection reports rootless operation and the requested image
already exists locally under an exact `sha256` digest.

The execution command enforces `--pull=never`, `--network=none`, a read-only root
filesystem, all capabilities dropped, no-new-privileges, PID/memory/CPU limits,
an unprivileged user and no host mounts.

Sources:

- https://github.com/containers/podman
- https://podman-desktop.io/docs/installation/windows-install
- https://docs.podman.io/en/latest/markdown/podman-run.1.html

Decision: **CONDITIONAL ADMISSION**. Any missing prerequisite fails closed.

## Fallback — Windows Sandbox

Windows Sandbox is not open source, but it is an operating-system isolation
feature and is retained as the Windows fallback after the open-source option.
The generated `.wsb` configuration disables networking, clipboard, printers,
audio input, video input and vGPU; enables ProtectedClient; maps candidate input
and the Python runtime read-only; and maps only an ephemeral evidence directory
outside the repository as writable.

Source:

- https://learn.microsoft.com/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file

Decision: **CONDITIONAL ADMISSION**. `WindowsSandbox.exe` and a mappable local
Python runtime must already exist.

## Rejected as security boundaries

- RestrictedPython: defense-in-depth language restriction, not an OS sandbox.
- Microsoft MXC preview: upstream warnings do not justify treating its profiles
  as a security boundary.
- Native host subprocess: no boundary between candidate code and Phoenix.

## Phase-9 conclusion

Candidate execution is conditional and fail-closed. No dependency installation,
Windows feature activation, image pull or network access is performed by the
Phase-9 cycle. Successful execution never activates an engine automatically.
