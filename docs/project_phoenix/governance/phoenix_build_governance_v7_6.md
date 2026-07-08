# Project Phoenix Build Governance v7.6

Deze specificatie legt de Brewster Engineering Wizard werkwijze vast als standaard voor Project Phoenix.

## Hoofdregels

- no_major_step_without_user_go: True
- preferred_delivery: downloadbare PowerShell update/patch scripts
- avoid_manual_python_paste: True
- one_task_one_script_one_test_one_commit: True
- always_test_before_commit: True
- always_end_with_git_status: True
- target_end_state: nothing to commit, working tree clean
- backup_before_replace: True
- rollback_or_restore_guidance_required: True

## Repositorybeleid

- Hoofdrepository: PROJECT-PHOENIX
- Branch: project-phoenix
- Engine-laag: apps/brewster_engineering_wizard/

## Roadmap

- Aantal sporen: 10
- Aantal concrete taken: 200
- Voortgang: 5.5%

## Volgende veilige GO-stap

- Taak: S01-002
- Titel: Automated cleanup helper
- Doel: Bouw of documenteer 'Automated cleanup helper' als gecontroleerde Phoenix-bouwtaak binnen spoor S01.
- Commit: feat: add automated cleanup helper (S01-002)

## Sporen

- S01 — Stabilisatie & automatisering
- S02 — Hoofdscherm / GUI / dashboards
- S03 — Project Intake + aannames + projectcontext
- S04 — Digital Twin + Knowledge Graph
- S05 — Geotechniek + fundering + constructie
- S06 — Infra: wegen, parkeren, riolering, waterbouw
- S07 — Vergunningen: BOPA, Omgevingsvergunning, AERIUS
- S08 — Kosten, planning, aanbesteding
- S09 — Rapporten, tekeningen, CAD/BIM/export
- S10 — Installatie, updates, documentatie, handleidingen
