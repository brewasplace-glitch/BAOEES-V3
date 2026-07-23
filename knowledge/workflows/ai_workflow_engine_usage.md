# AI Workflow Engine Usage

A Phoenix AI workflow consists of:

- a project context;
- ordered capabilities;
- explicit dependencies;
- optional conditions;
- bounded retries;
- assumptions;
- evidence;
- decision records.

Workflow steps should remain small, deterministic where practical, and
individually testable. External engineering engines are invoked through adapters,
not embedded directly into workflow definitions.
