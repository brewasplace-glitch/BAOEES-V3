# Phoenix Construction Progress, Site Records, NCR, Handover and As-Built Engine v7.2.0

v7.2.0 adds controlled construction completion and handover management.

Core capabilities:
- construction progress register;
- daily site records;
- photo/site evidence register;
- NCR register and corrective-action traceability;
- change/deviation register;
- punch-list register;
- commissioning register;
- as-built document register;
- handover document register;
- completion and handover matrix;
- Digital Twin handover writeback;
- SHA-256 artifact manifest.

Automatic handover release is disabled. Completion/handover unlock requires the
upstream field-release gate, no open critical NCRs, closure of mandatory NCR and
punch items, passed mandatory commissioning, complete verified final as-built
and handover documents, and professional completion release.
