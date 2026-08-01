# Phoenix Permit Dossier Assembly, Document Control and Submission Package Engine v6.9.0

v6.9.0 assembles a controlled permit dossier from project-specific documents.

Core outputs:
- document register;
- revision register;
- dossier index;
- submission manifest;
- deterministic submission package ZIP;
- SHA-256 artifact manifest;
- Digital Twin dossier writeback;
- submission-readiness release gate.

Automatic authority submission is disabled. Submission-ready unlock requires
the upstream permit-evidence gate, all mandatory documents to exist, revisions
to be present, documents to be approved for submission, and professional
signoff to be approved.
