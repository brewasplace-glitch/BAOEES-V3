from datetime import datetime


class AsBuiltEngine:

    def __init__(self):
        self.as_built_result = {}

    def prepare_as_built_package(
        self,
        project_result=None,
        drawing_result=None,
        cad_result=None,
        contract_result=None,
        construction_execution_result=None,
        site_monitoring_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}
        contract_result = contract_result or {}
        construction_execution_result = construction_execution_result or {}
        site_monitoring_result = site_monitoring_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result)

        as_built_register = self.build_as_built_register(
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        delivery_file = self.build_delivery_file(
            contract_result=contract_result,
            site_monitoring_result=site_monitoring_result
        )

        revision_checklist = self.build_revision_checklist(
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        open_points = self.build_open_points_register(site_monitoring_result)
        certificates = self.build_certificates_register()
        inspection_evidence = self.build_inspection_evidence(site_monitoring_result)
        digital_twin_update = self.build_digital_twin_update()
        final_control = self.build_final_control(validation_result)

        self.as_built_result = {
            "engine": "AsBuiltEngine",
            "version": "1.0",
            "status": "AS_BUILT_PACKAGE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept as-built en opleverdossier",
            "project_basis": project_basis,
            "as_built_register": as_built_register,
            "delivery_file": delivery_file,
            "revision_checklist": revision_checklist,
            "open_points": open_points,
            "certificates": certificates,
            "inspection_evidence": inspection_evidence,
            "digital_twin_update": digital_twin_update,
            "final_control": final_control,
            "warnings": self.build_warnings(site_monitoring_result, validation_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze As-Built Engine v1.0 maakt een concept oplever- en revisiedossier. "
                "Werkelijke oplevering vereist definitieve revisietekeningen, inspecties, "
                "certificaten, garanties, goedkeuringen en ondertekende opleverdocumenten."
            )
        }

        return self.as_built_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "delivery_phase": "concept oplevering en as-built",
            "status": "CONCEPT"
        }

    def build_as_built_register(self, drawing_result, cad_result):
        return {
            "status": "AS_BUILT_REGISTER_AANGEMAAKT",
            "drawing_source": drawing_result.get("engine", "Drawing Export Engine"),
            "cad_source": cad_result.get("engine", "CAD Export Engine"),
            "required_as_built_items": [
                "situatietekening revisie",
                "plattegronden revisie",
                "funderingstekening revisie",
                "constructietekening revisie",
                "rioleringstekening revisie",
                "terrein- en parkeerinrichting revisie",
                "CAD/DXF revisiebestanden",
                "maatvoerings- en peilgegevens"
            ],
            "register_items": [
                {
                    "id": "AB-001",
                    "document": "as-built situatietekening",
                    "status": "TE_CONTROLEREN",
                    "revision": "concept",
                    "file_reference": ""
                },
                {
                    "id": "AB-002",
                    "document": "as-built plattegronden",
                    "status": "TE_CONTROLEREN",
                    "revision": "concept",
                    "file_reference": ""
                },
                {
                    "id": "AB-003",
                    "document": "as-built riolering en afwatering",
                    "status": "TE_CONTROLEREN",
                    "revision": "concept",
                    "file_reference": ""
                }
            ]
        }

    def build_delivery_file(self, contract_result, site_monitoring_result):
        return {
            "status": "OPLEVERDOSSIER_CONCEPT",
            "linked_contract_status": contract_result.get("status", "onbekend"),
            "linked_monitoring_status": site_monitoring_result.get("status", "onbekend"),
            "required_documents": [
                "opdrachtbrief / contract",
                "definitief bestek / werkbeschrijving",
                "revisietekeningen",
                "as-built CAD/DXF bestanden",
                "inspectieverslagen",
                "fotoregister",
                "openstaande puntenlijst",
                "garanties en certificaten",
                "opleverformulier",
                "Digital Twin export",
                "bronvermelding en auditlog"
            ]
        }

    def build_revision_checklist(self, drawing_result, cad_result):
        return {
            "status": "REVISIECHECKLIST_CONCEPT",
            "checks": [
                "alle wijzigingen verwerkt op tekening",
                "maatvoering gecontroleerd",
                "peilen en hoogtes gecontroleerd",
                "rioleringstracé gecontroleerd",
                "fundering en constructie gecontroleerd",
                "CAD/DXF-bestanden bijgewerkt",
                "laatste revisienummer ingevuld",
                "documentdatum en verantwoordelijke ingevuld"
            ],
            "drawing_status": drawing_result.get("status", "onbekend"),
            "cad_status": cad_result.get("status", "onbekend")
        }

    def build_open_points_register(self, site_monitoring_result):
        action_register = site_monitoring_result.get("action_register", {}).get("actions", [])

        open_points = []

        for index, action in enumerate(action_register, start=1):
            open_points.append({
                "id": f"OP-{index:03d}",
                "description": action.get("description", ""),
                "owner": action.get("owner", "nader te bepalen"),
                "status": action.get("status", "OPEN"),
                "deadline": action.get("due_date")
            })

        if not open_points:
            open_points.append({
                "id": "OP-001",
                "description": "Opleverpunten tijdens eindcontrole invullen.",
                "owner": "uitvoerder/opdrachtgever",
                "status": "OPEN",
                "deadline": None
            })

        return {
            "status": "OPENSTAANDE_PUNTEN_REGISTER_GEREED",
            "open_points": open_points
        }

    def build_certificates_register(self):
        return {
            "status": "CERTIFICATEN_REGISTER_AANGEMAAKT",
            "required_certificates": [
                "betonleveringsbonnen",
                "wapeningscontrole",
                "constructieve goedkeuring",
                "riolering inspectie",
                "materiaalcertificaten",
                "garantieverklaringen",
                "veiligheids-/keuringsrapporten",
                "opleververklaring"
            ],
            "certificate_items": [
                {
                    "id": "CERT-001",
                    "name": "betonleveringsbonnen",
                    "status": "TE_VERZAMELEN",
                    "file_reference": ""
                },
                {
                    "id": "CERT-002",
                    "name": "riolering inspectie",
                    "status": "TE_VERZAMELEN",
                    "file_reference": ""
                },
                {
                    "id": "CERT-003",
                    "name": "garantieverklaringen",
                    "status": "TE_VERZAMELEN",
                    "file_reference": ""
                }
            ]
        }

    def build_inspection_evidence(self, site_monitoring_result):
        evidence_items = site_monitoring_result.get("evidence_register", {}).get("evidence_items", [])
        required_evidence = site_monitoring_result.get("evidence_register", {}).get("required_evidence", [])

        return {
            "status": "INSPECTIE_BEWIJSREGISTER_CONCEPT",
            "evidence_items": evidence_items,
            "required_evidence": required_evidence,
            "extra_required_delivery_evidence": [
                "foto eindoplevering",
                "ondertekende opleverlijst",
                "revisietekeningen akkoord",
                "controle projectdossier compleet"
            ]
        }

    def build_digital_twin_update(self):
        return {
            "status": "DIGITAL_TWIN_OPLEVERUPDATE_CONCEPT",
            "required_updates": [
                "projectstatus wijzigen naar opgeleverd concept",
                "as-built tekeningen koppelen",
                "openstaande punten koppelen",
                "certificaten en garanties koppelen",
                "inspecties en bewijsstukken koppelen",
                "laatste revisiedata vastleggen",
                "projectexport vernieuwen"
            ]
        }

    def build_final_control(self, validation_result):
        return {
            "status": "EINDCONTROLE_CONCEPT",
            "linked_validation_status": validation_result.get("status", "onbekend"),
            "final_checks": [
                "alle verplichte opleverdocumenten aanwezig",
                "openstaande punten gecontroleerd",
                "revisietekeningen aanwezig",
                "garanties en certificaten aanwezig",
                "foto-/bewijsregister aanwezig",
                "Digital Twin bijgewerkt",
                "bronvermelding en auditlog aanwezig"
            ]
        }

    def build_warnings(self, site_monitoring_result, validation_result):
        warnings = []

        if site_monitoring_result.get("status") != "SITE_MONITORING_PLAN_GEREED":
            warnings.append("Site monitoring is niet volledig gereed; opleverdossier kan onvolledig zijn.")

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aandachtspunten die vóór oplevering moeten worden opgelost.")

        if not warnings:
            warnings.append("Geen kritieke opleverwaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "AS_BUILT_ADVIES_CONCEPT",
            "advice": (
                "Gebruik dit as-built pakket als basis voor oplevering. "
                "Werk het dossier bij met definitieve revisietekeningen, certificaten, "
                "foto’s, inspecties en ondertekende opleverdocumenten."
            ),
            "next_steps": [
                "revisietekeningen definitief maken",
                "openstaande punten afhandelen",
                "certificaten en garanties verzamelen",
                "opleverinspectie uitvoeren",
                "Digital Twin actualiseren",
                "opleverdossier exporteren",
                "project formeel afsluiten"
            ]
        }

    def get_as_built_result(self):
        return self.as_built_result

    def run(self):
        print("As-Built / Oplever Engine actief")