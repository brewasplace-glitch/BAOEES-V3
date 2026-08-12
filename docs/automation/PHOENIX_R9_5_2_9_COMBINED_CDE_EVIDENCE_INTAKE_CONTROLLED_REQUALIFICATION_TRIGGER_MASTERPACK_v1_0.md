# PROJECT PHOENIX — R9.5.2.9 Combined C/D/E Evidence Intake & Controlled Requalification Trigger

## Doel

R9.5.2.9 maakt van de resterende R9.5-professionele evidence één praktisch intakepunt.

Het combineert:

- Package C — seismic scope & criteria;
- Package D — weak-storey screening professional review;
- Package E — independent alternate-load-path evidence.

De runtime-intake wordt gelezen uit:

`workspace/inputs/structural/r9_5_remaining_evidence_combined_intake_REQUIRED.json`

of uit een equivalente `package_inputs`-structuur die al in de runtime-context aanwezig is.

## Belangrijk architectuurprincipe

R9.5.2.9 keurt niets goed.

De runtimevolgorde wordt:

1. R9.5.2.9 normaliseert de gecombineerde C/D/E input;
2. Package E R9.5.2.5 valideert zijn eigen onafhankelijke evidence;
3. Package C R9.5.2.6 valideert seismic scope en criteria;
4. Package D R9.5.2.7 valideert de weak-storey review;
5. R9.5.2.8 consolideert de gevalideerde resultaten;
6. alleen indien C/D/E expliciet eligible zijn, mag R9.5.2.8 de bestaande controlled R9.5 requalification aanroepen.

R9.5.2.9 zelf kan nooit `ELIGIBLE_FOR_LATER_R9_5_PROMOTION` toekennen.

## Package C intake

Behouden worden onder andere:

- `seismic_applicability_status`
- `reference_type`
- `reference`
- `source_record_id`
- `professional_scope_reviewed`
- `scope_review_reference`
- `criteria_if_applicable`

Numerieke criteria blijven leeg totdat een traceerbare professionele bron ze werkelijk levert.

## Package D intake

Behouden worden:

- `screening_proxy_accepted_for_candidate_gate`
- `screening_proxy_review_reference`
- `reviewer_scope`
- `review_status`

Geen reviewstatus of acceptance wordt automatisch gegenereerd.

## Package E intake

Behouden worden:

- `independent_engineering_evidence_reference`
- `repository_relative_source_file`
- `sha256`
- `independent_review_status`
- `independent_review_reference`
- `independently_verified_alternate_path`
- `acceptance_criterion_and_traceability`

Interne screening blijft onvoldoende voor independent evidence.

## Veiligheidsgrenzen

- geen automatische seismic applicability;
- geen verzonnen numerieke criteria;
- geen automatische weak-storey proxy acceptance;
- geen gefabriceerde independent evidence;
- geen revieweridentiteit verzinnen;
- geen automatische professional approval;
- geen automatische code-compliance claim;
- geen automatische succesvolle R9.5 qualification;
- Production blijft LOCKED;
- FOR-CONSTRUCTION blijft LOCKED.

## Installer

Vereist baseline:

`80ec01b456707e7dcef0a8e327e9cf0819d73b38`

De installer voert parserpreflight, syntaxvalidatie, dedicated tests, R9.5.2.2 compatibility,
C/D/E/R9.5.2.8 impacttests, volledige suite-aware regressie, root-smoke tests,
test-output cleanup, diff-check, safety assertions, secret scan, scope-gate, commit/push
en local/remote clean-verificatie uit.

Bij de eerste fout volgt rollback naar de baseline.

PAT-001 wordt niet opnieuw uitgevoerd.
