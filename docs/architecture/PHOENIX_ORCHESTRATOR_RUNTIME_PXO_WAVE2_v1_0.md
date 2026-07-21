# Phoenix Orchestrator Runtime — PXO Wave 2 v1.0

This wave turns the PXO dependency contract into an executable runtime shell.

It provides:

- an explicit adapter registry;
- execution of the first ready engine;
- strict ready → running → completed/failed transitions;
- mandatory adapter outputs and evidence;
- stop-on-first-error behavior;
- atomic JSON checkpoints;
- checkpoint SHA-256 integrity evidence;
- deterministic test adapter support;
- bounded run-until-blocked-or-complete execution.

PXO Runtime v1.0 does not yet launch external processes or cloud workers.
Discipline engines must be connected through explicit adapters in later waves.
No missing adapter is treated as successful work.
