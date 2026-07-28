# REQ-105 professional evidence submission

Discipline: Building regulations / fire / building services

Required document types:
- `bbl_compliance_report`
- `fire_safety_and_egress_design`
- `ventilation_and_installation_design`

Procedure:
1. Put signed professional files in the `evidence` subfolder.
2. Copy `submission_manifest_template.json` to `submission_manifest.json`.
3. Enter the exact SHA-256 of every evidence file.
4. Run the validation gate.
5. Resolve every critical finding.
6. After review, create `project_leader_decision.json` from the decision template.
7. Run the validation gate again.

Templates, examples, simulations and unsigned documents can never close the requirement.
