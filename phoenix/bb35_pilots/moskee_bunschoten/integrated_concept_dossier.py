"""Generate the BB35 integrated concept dossier v2.0.2."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
_SIM_NOTICE = "CONCEPTSIMULATIE - NIET VOOR INDIENING OF UITVOERING"



def load_source_manifest_snapshot(
    snapshot_path: str | Path,
    source_root: str | Path,
) -> list[dict[str, Any]]:
    """Load a fixed source manifest and validate only the source inventory.

    The dossier content is driven by semantically parsed predecessor files.
    The fixed manifest prevents checkout line-ending or ZIP-container metadata
    from changing the generated dossier on another operating system.
    """
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    rows = [dict(item) for item in snapshot["files"]]
    expected = sorted(item["relative_path"] for item in rows)
    root = Path(source_root)
    actual = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        raise ValueError(
            "Source inventory differs from the v1.9.0 reference snapshot; "
            f"missing={missing}, unexpected={unexpected}"
        )
    return rows


class IntegratedConceptDossierEngine:
    VERSION = "2.0.2"

    def evaluate(
        self,
        *,
        simulation_summary: Mapping[str, Any],
        concept_register: Mapping[str, Any],
        gate_status: Mapping[str, Any],
        assumptions: list[dict[str, str]],
        handoffs: list[dict[str, str]],
        checks: list[dict[str, str]],
        req102_geometry: Mapping[str, Any],
        req103_structure: Mapping[str, Any],
        req104_foundation: Mapping[str, Any],
        req105_fire: Mapping[str, Any],
        req106_parking: Mapping[str, Any],
        req107_closure: Mapping[str, Any],
        req108_gap: Mapping[str, Any],
        source_files: list[dict[str, Any]],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_predecessors(
            simulation_summary=simulation_summary,
            concept_register=concept_register,
            gate_status=gate_status,
            checks=checks,
            req106_parking=req106_parking,
            req107_closure=req107_closure,
            source_files=source_files,
            config=config,
        )

        request_register = []
        for request_id in [
            "REQ-102", "REQ-103", "REQ-104", "REQ-105",
            "REQ-106", "REQ-107", "REQ-108",
        ]:
            source = concept_register["requests"][request_id]
            request_register.append({
                "request_id": request_id,
                "status": source["status"],
                "evidence_class": (
                    "AUTHORITATIVE_PROJECT_DECISION"
                    if request_id == "REQ-107"
                    else "CONCEPT_SIMULATION"
                ),
                "professional_evidence_required": request_id != "REQ-107",
                "submission_allowed": False,
            })

        drawing_register = [
            {
                "drawing_id": "DRW-001",
                "title": "Situatie en parkeercontext",
                "source_request": "REQ-102/REQ-106",
                "concept_status": "REGISTERED_SOURCE_DRAWING_OR_PLACEHOLDER",
                "professional_action": "Actualiseer schaal, perceel en 225 parkeerplaatsen.",
            },
            {
                "drawing_id": "DRW-002",
                "title": "Begane grond bestaand en nieuw",
                "source_request": "REQ-102",
                "concept_status": "CONCEPT_GEOMETRY_AVAILABLE",
                "professional_action": "Controleer maatvoering en aansluiting op bestaand.",
            },
            {
                "drawing_id": "DRW-003",
                "title": "Verdieping bestaand en nieuw",
                "source_request": "REQ-102",
                "concept_status": "CONCEPT_GEOMETRY_AVAILABLE",
                "professional_action": "Controleer maatvoering, functies en vide.",
            },
            {
                "drawing_id": "DRW-004",
                "title": "Gevelaanzichten",
                "source_request": "REQ-102",
                "concept_status": "SOURCE_DRAWING_REVIEW_REQUIRED",
                "professional_action": "Werk gevelwijziging en peilen vergunninggereed uit.",
            },
            {
                "drawing_id": "DRW-005",
                "title": "Doorsneden",
                "source_request": "REQ-102/REQ-103",
                "concept_status": "SOURCE_DRAWING_REVIEW_REQUIRED",
                "professional_action": "Toon hoogten, vloeren, dak en constructieve aansluiting.",
            },
            {
                "drawing_id": "DRW-006",
                "title": "Concept draagstructuur",
                "source_request": "REQ-103",
                "concept_status": "SIMULATED_SCHEME_ONLY",
                "professional_action": "Vervang door constructeursmodel en berekening.",
            },
            {
                "drawing_id": "DRW-007",
                "title": "Concept funderingsplan",
                "source_request": "REQ-104",
                "concept_status": "SIMULATED_FOUNDATION_ONLY",
                "professional_action": "Vervang na grondonderzoek en funderingsadvies.",
            },
            {
                "drawing_id": "DRW-008",
                "title": "Brandveiligheid en vluchtroutes",
                "source_request": "REQ-105",
                "concept_status": "CONCEPT_REVIEW_REQUIRED",
                "professional_action": "Laat uitgangsbreedten, loopafstanden en installaties toetsen.",
            },
        ]

        calculation_register = [
            {
                "calculation_id": "CALC-102-01",
                "title": "Geometrische basiscontrole",
                "request_id": "REQ-102",
                "concept_result": f"{req102_geometry['footprint_area_m2']} m2 footprint; {req102_geometry['gross_floor_area_m2']} m2 BVO",
                "status": "SIMULATION_ONLY",
            },
            {
                "calculation_id": "CALC-103-01",
                "title": "Concept draagstructuur en belastingafdracht",
                "request_id": "REQ-103",
                "concept_result": f"{req103_structure['column_count']} kolommen; synthetisch staalframe",
                "status": "SIMULATION_ONLY",
            },
            {
                "calculation_id": "CALC-104-01",
                "title": "Indicatieve funderingsdruk",
                "request_id": "REQ-104",
                "concept_result": f"{req104_foundation['indicative_average_contact_pressure_kpa']} kPa gemiddeld",
                "status": "SIMULATION_ONLY",
            },
            {
                "calculation_id": "CALC-105-01",
                "title": "Concept vluchtwegcapaciteit",
                "request_id": "REQ-105",
                "concept_result": f"{req105_fire['simulated_exit_count']} uitgangen van {req105_fire['simulated_exit_width_m_each']} m",
                "status": "SIMULATION_ONLY_NO_COMPLIANCE_CONCLUSION",
            },
            {
                "calculation_id": "CALC-105-02",
                "title": "Concept ventilatie-invoer",
                "request_id": "REQ-105",
                "concept_result": "Bezettingsgestuurde simulatie op wettelijk minimumniveau",
                "status": "SIMULATION_ONLY",
            },
            {
                "calculation_id": "CALC-106-01",
                "title": "Concept parkeerbalans",
                "request_id": "REQ-106",
                "concept_result": f"{req106_parking['confirmed_spaces']} plaatsen als projectleidersbasis",
                "status": "FIELD_VERIFICATION_PENDING",
            },
            {
                "calculation_id": "CALC-108-01",
                "title": "AERIUS aanlegfase invoermatrix",
                "request_id": "REQ-108",
                "concept_result": "Vijf fases; activiteitendata synthetisch of leeg",
                "status": "NO_AERIUS_CALCULATION_RUN",
            },
            {
                "calculation_id": "CALC-108-02",
                "title": "AERIUS gebruiksfase invoermatrix",
                "request_id": "REQ-108",
                "concept_result": "Bezetting en openingstijden gekoppeld; emissie-uitkomst ontbreekt",
                "status": "NO_AERIUS_CALCULATION_RUN",
            },
        ]

        blockers = []
        for item in config["professional_blockers"]:
            blockers.append({
                **item,
                "blocker_status": "OPEN_PROFESSIONAL_EVIDENCE_REQUIRED",
                "concept_available": True,
                "permit_ready_release_blocked": True,
            })

        replacement_plan = [
            {
                "sequence": index + 1,
                "request_id": item["request_id"],
                "replace_concept_with": item["required_evidence"],
                "responsible_role": item["responsible_role"],
                "acceptance_gate": "SIGNED_EVIDENCE_VALIDATED_AND_CHECKSUM_REGISTERED",
            }
            for index, item in enumerate(blockers)
        ]

        report = {
            "schema_version": "phoenix.bb35.integrated-concept-dossier/1.0",
            "engine_version": self.VERSION,
            "dossier_id": config["dossier_id"],
            "pilot_id": config["pilot_id"],
            "project_id": config["project_id"],
            "project_name": config["project_name"],
            "project_location": config["project_location"],
            "dossier_date": config["dossier_date"],
            "simulation_notice": config["simulation_notice"],
            "status": "INTEGRATED_CONCEPT_DOSSIER_GENERATED_REVIEW_READY",
            "project_scope": {
                "footprint_width_m": 10.0,
                "footprint_depth_m": 7.0,
                "footprint_area_m2": req102_geometry["footprint_area_m2"],
                "storeys": 2,
                "gross_floor_area_m2": req102_geometry["gross_floor_area_m2"],
            },
            "occupancy_program": req107_closure["occupancy_scenarios"],
            "opening_hours": req107_closure["opening_hours"],
            "parking_basis_spaces": req106_parking["confirmed_spaces"],
            "parking_basis_status": req106_parking["confirmation_status"],
            "previous_parking_hypothesis_spaces": req106_parking["superseded_spaces"],
            "req107_status": req107_closure["status"],
            "request_register": request_register,
            "drawing_register": drawing_register,
            "calculation_register": calculation_register,
            "assumptions": assumptions,
            "handoffs": handoffs,
            "consistency_checks": checks,
            "professional_blockers": blockers,
            "evidence_replacement_plan": replacement_plan,
            "source_files": source_files,
            "metrics": {
                "request_count": len(request_register),
                "concept_simulation_count": 6,
                "authoritative_request_count": 1,
                "drawing_register_count": len(drawing_register),
                "calculation_register_count": len(calculation_register),
                "assumption_count": len(assumptions),
                "handoff_count": len(handoffs),
                "consistency_check_count": len(checks),
                "professional_blocker_count": len(blockers),
                "source_file_count": len(source_files),
            },
            "gates": {
                "integrated_concept_dossier_generated": True,
                "concept_dossier_review_ready": True,
                "end_to_end_workflow_validated": True,
                "professional_evidence_still_required": True,
                "final_permit_ready_generation_allowed": False,
                "bb36_functional_validation_passed": True,
                "bb36_production_release_allowed": False,
            },
            "next_gate": (
                "Review and approve the concept dossier, then replace REQ-102, "
                "REQ-103, REQ-104, REQ-105, REQ-106 and REQ-108 simulations "
                "with validated professional evidence."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _validate_predecessors(
        *,
        simulation_summary: Mapping[str, Any],
        concept_register: Mapping[str, Any],
        gate_status: Mapping[str, Any],
        checks: list[dict[str, str]],
        req106_parking: Mapping[str, Any],
        req107_closure: Mapping[str, Any],
        source_files: list[dict[str, Any]],
        config: Mapping[str, Any],
    ) -> None:
        validations = {
            "simulation_passed": simulation_summary.get("status")
                == "FULL_CONCEPT_EVIDENCE_SIMULATION_RUN_PASSED",
            "dossier_allowed": bool(gate_status.get("concept_dossier_generation_allowed")),
            "eleven_checks": len(checks) == 11,
            "all_checks_passed": all(str(row.get("passed", "")).lower() == "true" for row in checks),
            "seven_requests": len(concept_register.get("requests", {})) == 7,
            "parking_225": req106_parking.get("confirmed_spaces") == 225,
            "parking_300_superseded": req106_parking.get("superseded_spaces") == 300,
            "req107_closed": req107_closure.get("status") == "CLOSED_PROJECT_LEADER_APPROVED",
            "six_blockers": len(config.get("professional_blockers", [])) == 6,
            "source_manifest": len(source_files) == 44,
            "bb36_functional": bool(gate_status.get("bb36_functional_validation_passed")),
            "bb36_production_locked": not bool(gate_status.get("bb36_production_release_allowed")),
        }
        failed = [name for name, passed in validations.items() if not passed]
        if failed:
            raise ValueError("Integrated dossier predecessor validation failed: " + ", ".join(failed))

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class IntegratedConceptDossierExporter:
    def export_all(self, report: Mapping[str, Any], output_dir: str | Path) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}

        paths["summary"] = self._json(root / "01_integrated_concept_dossier_summary.json", {
            key: value for key, value in report.items()
            if key not in {
                "request_register", "drawing_register", "calculation_register",
                "assumptions", "handoffs", "consistency_checks",
                "professional_blockers", "evidence_replacement_plan", "source_files",
            }
        })
        paths["dossier_md"] = self._markdown(
            root / "02_integrated_concept_dossier.md",
            self._integrated_markdown(report),
        )
        paths["dossier_html"] = self._html(
            root / "03_integrated_concept_dossier.html",
            report,
        )
        paths["management"] = self._markdown(
            root / "04_management_summary.md",
            self._management_summary(report),
        )
        paths["request_register"] = self._csv(
            root / "05_request_status_register.csv",
            report["request_register"],
            ["request_id", "status", "evidence_class", "professional_evidence_required", "submission_allowed"],
        )
        paths["drawing_register"] = self._csv(
            root / "06_drawing_register.csv",
            report["drawing_register"],
            ["drawing_id", "title", "source_request", "concept_status", "professional_action"],
        )
        paths["calculation_register"] = self._csv(
            root / "07_calculation_register.csv",
            report["calculation_register"],
            ["calculation_id", "title", "request_id", "concept_result", "status"],
        )
        paths["assumptions"] = self._csv(
            root / "08_assumptions_register.csv",
            report["assumptions"],
            ["assumption_id", "request_id", "description", "value", "status"],
        )
        paths["handoffs"] = self._csv(
            root / "09_cross_discipline_handoff_matrix.csv",
            report["handoffs"],
            ["from_request", "to_request", "data", "status"],
        )
        paths["checks"] = self._csv(
            root / "10_consistency_validation_register.csv",
            report["consistency_checks"],
            ["check_id", "description", "passed"],
        )
        paths["blockers"] = self._csv(
            root / "11_professional_blocker_register.csv",
            report["professional_blockers"],
            [
                "request_id", "discipline", "responsible_role", "required_evidence",
                "blocker_status", "concept_available", "permit_ready_release_blocked",
            ],
        )
        paths["replacement"] = self._csv(
            root / "12_evidence_replacement_plan.csv",
            report["evidence_replacement_plan"],
            ["sequence", "request_id", "replace_concept_with", "responsible_role", "acceptance_gate"],
        )
        paths["bb36"] = self._markdown(
            root / "13_BB36_functional_validation_report.md",
            self._bb36_report(report),
        )
        paths["gates"] = self._json(
            root / "14_release_gate_status.json",
            {
                "dossier_id": report["dossier_id"],
                "status": report["status"],
                "gates": report["gates"],
                "professional_blocker_count": report["metrics"]["professional_blocker_count"],
                "next_gate": report["next_gate"],
            },
        )
        paths["navigation"] = self._json(
            root / "15_dossier_navigation.json",
            {
                "primary_document": "03_integrated_concept_dossier.html",
                "printable_source": "02_integrated_concept_dossier.md",
                "registers": [
                    "05_request_status_register.csv",
                    "06_drawing_register.csv",
                    "07_calculation_register.csv",
                    "08_assumptions_register.csv",
                    "09_cross_discipline_handoff_matrix.csv",
                    "10_consistency_validation_register.csv",
                    "11_professional_blocker_register.csv",
                    "12_evidence_replacement_plan.csv",
                ],
                "validation": "13_BB36_functional_validation_report.md",
                "gate_status": "14_release_gate_status.json",
            },
        )
        paths["sources"] = self._csv(
            root / "16_source_manifest.csv",
            report["source_files"],
            ["relative_path", "size_bytes", "sha256", "source_class", "hash_mode"],
        )
        paths["approval"] = self._markdown(
            root / "17_review_and_approval_template.md",
            self._approval_template(report),
        )
        paths["transmittal"] = self._markdown(
            root / "18_concept_dossier_transmittal.md",
            self._transmittal(report),
        )
        paths["checksums"] = self._checksums(paths, root / "checksums.sha256")
        paths["dossier_zip"] = self._dossier(
            paths,
            root / "BB35_PILOT_1_INTEGRATED_CONCEPT_DOSSIER_v2_0_2.zip",
        )
        return paths

    @staticmethod
    def _management_summary(report: Mapping[str, Any]) -> str:
        scope = report["project_scope"]
        occ = report["occupancy_program"]
        return "\n".join([
            f"# Managementsamenvatting - {report['project_name']}",
            "",
            f"**{report['simulation_notice']}**",
            "",
            f"Dossier: `{report['dossier_id']}`  ",
            f"Locatie: {report['project_location']}  ",
            f"Status: `{report['status']}`",
            "",
            "## Projectbasis",
            "",
            f"- Uitbreiding: 10,0 x 7,0 m; {scope['footprint_area_m2']} m2 footprint.",
            f"- Twee bouwlagen; {scope['gross_floor_area_m2']} m2 bruto vloeroppervlak.",
            f"- Regulier toekomstig gebruik: {occ['regular']['future_persons']} personen.",
            f"- Vrijdaggebed toekomstig: {occ['friday_prayer']['future_persons']} personen.",
            f"- Bijzondere piek: {occ['special_peak']['maximum_persons']} personen, eenmaal per jaar.",
            f"- Parkeerbasis: {report['parking_basis_spaces']} plaatsen, door projectleider bevestigd; veldverificatie open.",
            "- REQ-107 is gesloten door de projectleider.",
            "",
            "## Resultaat van de conceptketen",
            "",
            "- REQ-102, 103, 104, 105, 106 en 108 zijn als conceptsimulatie geïntegreerd.",
            "- Elf van elf consistentiecontroles zijn geslaagd.",
            "- De end-to-end workflow en BB36-functionele validatie zijn geslaagd.",
            "- Het geïntegreerde conceptdossier is gereed voor review.",
            "",
            "## Beperkingen",
            "",
            "- Zes professionele bewijsblokkades blijven open.",
            "- Geen conceptresultaat mag voor vergunning, aanbesteding of uitvoering worden gebruikt.",
            "- Definitieve vergunningklare generatie en BB36-productievrijgave blijven geblokkeerd.",
            "",
        ])

    def _integrated_markdown(self, report: Mapping[str, Any]) -> str:
        scope = report["project_scope"]
        occ = report["occupancy_program"]
        lines = [
            f"# Geïntegreerd conceptdossier - {report['project_name']}",
            "",
            f"> **{report['simulation_notice']}**",
            "",
            f"Dossier-ID: `{report['dossier_id']}`  ",
            f"Project-ID: `{report['project_id']}`  ",
            f"Locatie: {report['project_location']}  ",
            f"Dossierdatum: {report['dossier_date']}  ",
            f"Status: `{report['status']}`",
            "",
            "## 1. Doel en leeswijzer",
            "",
            "Dit dossier bundelt de volledige conceptsimulatie van REQ-102 tot en met REQ-108. "
            "Het toont dat Phoenix de onderlinge gegevensoverdracht, controles, registers en release-gates kan uitvoeren. "
            "REQ-107 is een werkelijk projectbesluit; alle overige technische resultaten blijven simulaties.",
            "",
            "## 2. Project- en scopebasis",
            "",
            f"De gesimuleerde uitbreiding heeft een footprint van {scope['footprint_width_m']} x {scope['footprint_depth_m']} m, "
            f"oftewel {scope['footprint_area_m2']} m2. Met {scope['storeys']} bouwlagen bedraagt het bruto vloeroppervlak "
            f"{scope['gross_floor_area_m2']} m2.",
            "",
            "## 3. Vastgesteld gebruiks- en bezettingsprogramma",
            "",
            f"- Regulier: {occ['regular']['existing_persons']} bestaand en {occ['regular']['future_persons']} toekomstig.",
            f"- Vrijdaggebed: {occ['friday_prayer']['existing_persons']} bestaand en {occ['friday_prayer']['future_persons']} toekomstig.",
            f"- Bijzondere piek: {occ['special_peak']['maximum_persons']} personen, {occ['special_peak']['frequency_per_year']} keer per jaar.",
            f"- Status REQ-107: `{report['req107_status']}`.",
            "",
            "## 4. Integrale status REQ-102 tot en met REQ-108",
            "",
        ]
        for item in report["request_register"]:
            lines.append(
                f"### {item['request_id']}\n\n"
                f"Status: `{item['status']}`  \n"
                f"Bewijsklasse: `{item['evidence_class']}`  \n"
                f"Professioneel bewijs vereist: `{item['professional_evidence_required']}`  \n"
                f"Indiening toegestaan: `{item['submission_allowed']}`\n"
            )
        lines.extend([
            "## 5. REQ-102 - Geometrie en kadastrale basis",
            "",
            f"De conceptgeometrie gebruikt een lokale simulatiegrid en een rechthoek van {scope['footprint_width_m']} x {scope['footprint_depth_m']} m. "
            "Deze geometrie is geschikt voor workflowvalidatie, maar niet voor een vergunningstekening. Schaal, perceelgrenzen, "
            "coördinaten en aansluiting op het bestaande gebouw moeten professioneel worden bevestigd.",
            "",
            "## 6. REQ-103 - Constructieve conceptopname",
            "",
            "De simulatie bevat een synthetisch staalframeschema met negen kolomposities en een traceerbare belastingafdracht naar REQ-104. "
            "Het model bewijst de gegevensketen, niet de draagveiligheid. Een constructeur moet de bestaande constructie opnemen, "
            "de aansluiting nieuw-bestaand beoordelen en de definitieve berekening ondertekenen.",
            "",
            "## 7. REQ-104 - Geotechniek en fundering",
            "",
            "Het funderingsconcept gebruikt gesimuleerde bodemgegevens en een conceptuele strokenfundering. De berekende gemiddelde "
            "contactdruk is uitsluitend een systeemtest. Sonderingen, grondwatergegevens, zettingsbeoordeling en funderingsadvies ontbreken nog.",
            "",
            "## 8. REQ-105 - Bbl, brandveiligheid en installaties",
            "",
            "Het concept gebruikt het gezaghebbende bezettingsprogramma, geen keukenfunctie en het wettelijk minimumniveau. "
            "Vluchtwegen, uitgangsbreedten, ventilatie en installaties zijn als rekenketen getest. Er is bewust geen "
            "professionele Bbl- of brandveiligheidsconclusie afgegeven.",
            "",
            "## 9. REQ-106 - Parkeren",
            "",
            f"De actuele projectbasis bedraagt {report['parking_basis_spaces']} parkeerplaatsen in de directe omgeving. "
            f"De eerdere hypothese van {report['previous_parking_hypothesis_spaces']} plaatsen is vervallen. "
            "De 225 plaatsen moeten nog worden gelokaliseerd, juridisch geclassificeerd en tijdens representatieve momenten worden geteld. "
            "De conceptbalans is alleen bedoeld om de analyse- en rapportageflow te testen.",
            "",
            "## 10. REQ-107 - Gebruik en bezetting",
            "",
            "REQ-107 is geen simulatie. De projectleider heeft het bezettings- en gebruiksprogramma vastgesteld. "
            "Dit programma is als gezaghebbende invoer doorgegeven aan REQ-105, REQ-106 en REQ-108.",
            "",
            "## 11. REQ-108 - AERIUS",
            "",
            "De aanleg- en gebruiksfase zijn in vijf conceptfasen georganiseerd, waarbij de moskee tijdens de werkzaamheden in gebruik blijft. "
            "Materieel, draaiuren, brandstof, verkeer en afstanden zijn nog niet professioneel vastgesteld. Er is geen AERIUS-berekening "
            "uitgevoerd en geen depositieresultaat gegenereerd.",
            "",
            "## 12. Tekeningenregister",
            "",
        ])
        for item in report["drawing_register"]:
            lines.append(
                f"- **{item['drawing_id']} - {item['title']}**: `{item['concept_status']}`. {item['professional_action']}"
            )
        lines.extend(["", "## 13. Berekeningenregister", ""])
        for item in report["calculation_register"]:
            lines.append(
                f"- **{item['calculation_id']} - {item['title']}** ({item['request_id']}): {item['concept_result']} - `{item['status']}`."
            )
        lines.extend(["", "## 14. Aannames en gegevensoverdracht", ""])
        lines.append(
            f"Het dossier bevat {report['metrics']['assumption_count']} geregistreerde aannames en "
            f"{report['metrics']['handoff_count']} gecontroleerde overdrachten tussen disciplines. "
            "Simulatieaannames blijven herkenbaar en mogen niet worden gepromoveerd tot werkelijk projectbewijs."
        )
        lines.extend(["", "## 15. Consistentie en kwaliteitscontrole", ""])
        lines.append(
            f"Alle {report['metrics']['consistency_check_count']} controles zijn geslaagd. De controles bevestigen onder meer "
            "de 70/140 m2 scope, de overdracht van constructieve belasting naar fundering, toepassing van de bezetting, "
            "gebruik van 225 parkeerplaatsen, vervanging van 300 en het ontbreken van een verzonnen AERIUS-uitkomst."
        )
        lines.extend(["", "## 16. Open professionele bewijsblokkades", ""])
        for item in report["professional_blockers"]:
            lines.append(
                f"- **{item['request_id']} - {item['discipline']}**: {item['required_evidence']} "
                f"Verantwoordelijke rol: {item['responsible_role']}."
            )
        lines.extend([
            "",
            "## 17. BB36-validatie en release-gates",
            "",
            "De BB36-functionele validatie is geslaagd: Phoenix kan de conceptketen, controles, registers en dossierassemblage uitvoeren. "
            "De BB36-productievrijgave blijft vergrendeld totdat de zes conceptsimulaties door gevalideerd professioneel bewijs zijn vervangen.",
            "",
            "## 18. Conclusie en volgende stap",
            "",
            "Het geïntegreerde conceptdossier is gereed voor inhoudelijke review en vormt een gecontroleerde basis voor de externe adviseurs. "
            "Na review moet per blocker een ondertekend bewijsstuk worden ontvangen, gevalideerd, gehasht en gekoppeld. Pas daarna kan de "
            "vergunningklare eindgeneratie worden vrijgegeven.",
            "",
            f"Rapportfingerprint: `{report['report_fingerprint_sha256']}`",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _bb36_report(report: Mapping[str, Any]) -> str:
        return "\n".join([
            "# BB36 Functioneel validatierapport",
            "",
            f"**{report['simulation_notice']}**",
            "",
            "## Uitkomst",
            "",
            "- End-to-end workflow: GESLAAGD.",
            "- Geïntegreerde conceptdossiergeneratie: GESLAAGD.",
            "- Consistentiecontroles: 11 van 11 GESLAAGD.",
            "- REQ-107 projectleiderssluiting: GESLAAGD.",
            "- Parkeerbasis 225 en supersede 300: GESLAAGD.",
            "- Bescherming tegen verzonnen AERIUS-uitkomst: GESLAAGD.",
            "",
            "## Productiegate",
            "",
            "BB36 functionele validatie is geslaagd. BB36 productievrijgave blijft vergrendeld, omdat zes professionele "
            "bewijsblokkades openstaan. Dit is een bewuste kwaliteits- en aansprakelijkheidsgate en geen technische fout.",
            "",
        ])

    @staticmethod
    def _approval_template(report: Mapping[str, Any]) -> str:
        lines = [
            "# Review- en goedkeuringsformulier geïntegreerd conceptdossier",
            "",
            f"Dossier: `{report['dossier_id']}`",
            "",
            "## Projectleider",
            "",
            "Naam:",
            "",
            "Beoordeling conceptdossier:",
            "",
            "Datum:",
            "",
            "Handtekening / elektronische goedkeuring:",
            "",
            "## Disciplinebeoordelingen",
            "",
        ]
        for blocker in report["professional_blockers"]:
            lines.extend([
                f"### {blocker['request_id']} - {blocker['discipline']}",
                "",
                f"Verantwoordelijke rol: {blocker['responsible_role']}",
                "",
                "Naam beoordelaar:",
                "",
                "Ontvangen bewijsstukken:",
                "",
                "Conclusie / afwijkingen:",
                "",
                "Datum en handtekening:",
                "",
            ])
        return "\n".join(lines)

    @staticmethod
    def _transmittal(report: Mapping[str, Any]) -> str:
        return "\n".join([
            "# Begeleidende aanbiedingsnotitie conceptdossier",
            "",
            f"Betreft: {report['project_name']}",
            f"Dossier: {report['dossier_id']}",
            f"Locatie: {report['project_location']}",
            "",
            "Hierbij wordt het geïntegreerde conceptdossier aangeboden voor projectinterne review en voor voorbereiding van de "
            "professionele bewijsleveringen. Het dossier bevat simulaties en mag niet worden ingediend, aanbesteed of uitgevoerd.",
            "",
            "De volgende onderdelen moeten professioneel worden vervangen: REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 en REQ-108. "
            "REQ-107 is door de projectleider gesloten en geldt als gezaghebbende projectinvoer.",
            "",
            f"Parkeerbasis: {report['parking_basis_spaces']} plaatsen, veldverificatie nog vereist.",
            "",
        ])

    @staticmethod
    def _html(path: Path, report: Mapping[str, Any]) -> Path:
        def esc(value: Any) -> str:
            return html.escape(str(value))

        req_rows = "".join(
            "<tr>"
            f"<td>{esc(item['request_id'])}</td>"
            f"<td>{esc(item['status'])}</td>"
            f"<td>{esc(item['evidence_class'])}</td>"
            f"<td>{'Ja' if item['professional_evidence_required'] else 'Nee'}</td>"
            "</tr>"
            for item in report["request_register"]
        )
        drawing_rows = "".join(
            "<tr>"
            f"<td>{esc(item['drawing_id'])}</td>"
            f"<td>{esc(item['title'])}</td>"
            f"<td>{esc(item['concept_status'])}</td>"
            f"<td>{esc(item['professional_action'])}</td>"
            "</tr>"
            for item in report["drawing_register"]
        )
        calc_rows = "".join(
            "<tr>"
            f"<td>{esc(item['calculation_id'])}</td>"
            f"<td>{esc(item['title'])}</td>"
            f"<td>{esc(item['concept_result'])}</td>"
            f"<td>{esc(item['status'])}</td>"
            "</tr>"
            for item in report["calculation_register"]
        )
        blocker_rows = "".join(
            "<tr>"
            f"<td>{esc(item['request_id'])}</td>"
            f"<td>{esc(item['discipline'])}</td>"
            f"<td>{esc(item['required_evidence'])}</td>"
            f"<td>{esc(item['responsible_role'])}</td>"
            "</tr>"
            for item in report["professional_blockers"]
        )
        scope = report["project_scope"]
        content = f"""<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<title>Geïntegreerd conceptdossier {esc(report['dossier_id'])}</title>
<style>
@page{{size:A4;margin:18mm}} body{{font-family:Arial,Helvetica,sans-serif;color:#1f2933;max-width:1100px;margin:0 auto;line-height:1.45}}
header{{border-bottom:5px solid #243746;padding:28px 0 18px}} h1{{margin:0;font-size:30px}} h2{{border-bottom:2px solid #8aa0b2;padding-bottom:5px;margin-top:32px}}
.notice{{background:#fff3cd;border:2px solid #b7791f;padding:14px;font-weight:700;margin:20px 0}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}} .card{{border:1px solid #bcc7d1;padding:12px;background:#f7f9fb}}
table{{border-collapse:collapse;width:100%;margin:12px 0 24px;font-size:13px}} th,td{{border:1px solid #b7c1ca;padding:7px;vertical-align:top}} th{{background:#243746;color:white;text-align:left}}
.ok{{color:#176b3a;font-weight:700}} .blocked{{color:#9b2c2c;font-weight:700}} footer{{border-top:1px solid #aaa;margin-top:40px;padding:12px 0;font-size:12px}}
@media print{{body{{max-width:none}} a{{color:inherit;text-decoration:none}}}}
</style></head><body>
<header><div>PROJECT PHOENIX - BB35 PILOT 1</div><h1>Geïntegreerd conceptdossier</h1><p>{esc(report['project_name'])}<br>{esc(report['project_location'])}<br>Dossier {esc(report['dossier_id'])}</p></header>
<div class="notice">{esc(report['simulation_notice'])}</div>
<section><h2>Managementsamenvatting</h2><p>De volledige conceptketen REQ-102 tot en met REQ-108 is geïntegreerd. REQ-107 is door de projectleider gesloten. De overige zes requests bevatten conceptsimulaties en wachten op professioneel bewijs.</p>
<div class="grid"><div class="card"><b>Footprint</b><br>{scope['footprint_area_m2']} m2</div><div class="card"><b>BVO</b><br>{scope['gross_floor_area_m2']} m2</div><div class="card"><b>Parkeren</b><br>{report['parking_basis_spaces']} plaatsen</div><div class="card"><b>Blokkades</b><br>{report['metrics']['professional_blocker_count']}</div></div></section>
<section><h2>Release-status</h2><p class="ok">Conceptdossier reviewgereed; end-to-end workflow en BB36 functioneel gevalideerd.</p><p class="blocked">Definitieve vergunningklare generatie en BB36-productievrijgave blijven geblokkeerd.</p></section>
<section><h2>REQ-statusregister</h2><table><thead><tr><th>REQ</th><th>Status</th><th>Bewijsklasse</th><th>Professioneel bewijs</th></tr></thead><tbody>{req_rows}</tbody></table></section>
<section><h2>Tekeningenregister</h2><table><thead><tr><th>ID</th><th>Titel</th><th>Conceptstatus</th><th>Professionele actie</th></tr></thead><tbody>{drawing_rows}</tbody></table></section>
<section><h2>Berekeningenregister</h2><table><thead><tr><th>ID</th><th>Berekening</th><th>Conceptresultaat</th><th>Status</th></tr></thead><tbody>{calc_rows}</tbody></table></section>
<section><h2>Open professionele bewijsblokkades</h2><table><thead><tr><th>REQ</th><th>Discipline</th><th>Vereist bewijs</th><th>Rol</th></tr></thead><tbody>{blocker_rows}</tbody></table></section>
<section><h2>BB36</h2><p>Functionele validatie: <b class="ok">GESLAAGD</b>. Productievrijgave: <b class="blocked">VERGRENDELD</b>.</p></section>
<footer>Fingerprint: {esc(report['report_fingerprint_sha256'])}</footer>
</body></html>"""
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _json(path: Path, value: Any) -> Path:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _markdown(path: Path, text: str) -> Path:
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> Path:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\r\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    field: (
                        json.dumps(row.get(field), ensure_ascii=False, sort_keys=True)
                        if isinstance(row.get(field), (list, dict))
                        else row.get(field, "")
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
            for key, path in sorted(paths.items())
            if key not in {"checksums", "dossier_zip"}
        ]
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return destination

    @classmethod
    def _dossier(cls, paths: Mapping[str, Path], destination: Path) -> Path:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.comment = b""
            for key, source in sorted(paths.items()):
                if key == "dossier_zip":
                    continue
                archive.writestr(cls._canonical_info(source.name), source.read_bytes())
        return destination

    @staticmethod
    def _canonical_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = 20
        info.reserved = 0
        info.flag_bits = 0
        info.volume = 0
        info.internal_attr = 0
        info.external_attr = 0o100644 << 16
        info.extra = b""
        info.comment = b""
        return info
