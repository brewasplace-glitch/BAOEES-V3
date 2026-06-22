from datetime import datetime


class SiteMonitoringEngine:

    def __init__(self):
        self.monitoring_result = {}

    def create_monitoring_plan(
        self,
        project_result=None,
        planning_result=None,
        construction_execution_result=None,
        contract_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        planning_result = planning_result or {}
        construction_execution_result = construction_execution_result or {}
        contract_result = contract_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result)

        progress_framework = self.build_progress_framework(
            planning_result=planning_result,
            construction_execution_result=construction_execution_result
        )

        daily_report_template = self.build_daily_report_template(project_result)

        monitoring_checklist = self.build_monitoring_checklist(
            construction_execution_result=construction_execution_result
        )

        deviation_register = self.build_deviation_register()
        action_register = self.build_action_register(validation_result)
        evidence_register = self.build_evidence_register()
        progress_vs_planning = self.build_progress_vs_planning(planning_result)
        risk_monitoring = self.build_risk_monitoring(
            construction_execution_result=construction_execution_result,
            validation_result=validation_result
        )
        delivery_monitoring = self.build_delivery_monitoring(contract_result)

        self.monitoring_result = {
            "engine": "SiteMonitoringEngine",
            "version": "1.0",
            "status": "SITE_MONITORING_PLAN_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept bouwplaatsbewaking en voortgangsmonitor",
            "project_basis": project_basis,
            "progress_framework": progress_framework,
            "daily_report_template": daily_report_template,
            "monitoring_checklist": monitoring_checklist,
            "deviation_register": deviation_register,
            "action_register": action_register,
            "evidence_register": evidence_register,
            "progress_vs_planning": progress_vs_planning,
            "risk_monitoring": risk_monitoring,
            "delivery_monitoring": delivery_monitoring,
            "warnings": self.build_warnings(construction_execution_result, planning_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Site Monitoring Engine v1.0 maakt een concept-monitoringsplan. "
                "Werkelijke bouwplaatsbewaking vereist actuele dagrapporten, inspecties, foto's, "
                "metingen, veiligheidsregistraties en goedkeuringen door bevoegde personen."
            )
        }

        return self.monitoring_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "monitoring_phase": "concept uitvoering en bouwplaatsbewaking",
            "status": "CONCEPT"
        }

    def build_progress_framework(self, planning_result, construction_execution_result):
        phases = construction_execution_result.get("execution_phasing", {}).get("phases", [])

        progress_items = []

        for phase in phases:
            progress_items.append({
                "phase": phase.get("phase"),
                "title": phase.get("title"),
                "planned_progress_percent": 0,
                "actual_progress_percent": 0,
                "status": "NIET_GESTART",
                "open_actions": [],
                "notes": ""
            })

        return {
            "status": "VOORTGANGSKADER_GEREED",
            "linked_planning_status": planning_result.get("status", "onbekend"),
            "linked_execution_status": construction_execution_result.get("status", "onbekend"),
            "progress_items": progress_items,
            "overall_progress_percent": 0,
            "overall_status": "NIET_GESTART"
        }

    def build_daily_report_template(self, project_result):
        return {
            "status": "DAGRAPPORT_TEMPLATE_GEREED",
            "template": {
                "project_name": project_result.get("project_name", "Onbekend project"),
                "report_date": None,
                "weather": "",
                "site_manager": "",
                "personnel_on_site": [],
                "equipment_on_site": [],
                "work_performed": [],
                "deliveries": [],
                "inspections": [],
                "incidents_or_safety_notes": [],
                "deviations": [],
                "photos_or_evidence": [],
                "open_actions": [],
                "signature": ""
            }
        }

    def build_monitoring_checklist(self, construction_execution_result):
        quality_controls = construction_execution_result.get("quality_controls", {}).get("controls", [])
        inspections = construction_execution_result.get("inspection_moments", {}).get("inspections", [])

        return {
            "status": "MONITORING_CHECKLIST_GEREED",
            "quality_controls": quality_controls,
            "inspection_moments": inspections,
            "standard_daily_checks": [
                "bouwplaatsveiligheid gecontroleerd",
                "toegang en logistieke route vrij",
                "werkzaamheden conform planning",
                "maatvoering en peilen gecontroleerd indien relevant",
                "materialen en leveringen geregistreerd",
                "afwijkingen vastgelegd",
                "foto’s/bewijs toegevoegd",
                "openstaande acties bijgewerkt"
            ]
        }

    def build_deviation_register(self):
        return {
            "status": "AFWIJKINGENREGISTER_AANGEMAAKT",
            "deviations": [
                {
                    "id": "DEV-001",
                    "date": None,
                    "phase": "",
                    "description": "",
                    "impact": "",
                    "responsible_party": "",
                    "corrective_action": "",
                    "status": "OPEN"
                }
            ],
            "note": "Register is voorbereid; afwijkingen worden tijdens uitvoering toegevoegd."
        }

    def build_action_register(self, validation_result):
        risks = validation_result.get("risk_check", {}).get("risks", [])

        actions = []

        for index, risk in enumerate(risks, start=1):
            actions.append({
                "id": f"ACT-{index:03d}",
                "source": "Validation Engine",
                "description": risk,
                "owner": "nader te bepalen",
                "due_date": None,
                "status": "OPEN"
            })

        if not actions:
            actions.append({
                "id": "ACT-001",
                "source": "Site Monitoring Engine",
                "description": "Dagelijkse voortgang en kwaliteit registreren.",
                "owner": "uitvoerder",
                "due_date": None,
                "status": "OPEN"
            })

        return {
            "status": "ACTIEREGISTER_GEREED",
            "actions": actions
        }

    def build_evidence_register(self):
        return {
            "status": "BEWIJSREGISTER_AANGEMAAKT",
            "evidence_items": [
                {
                    "id": "EV-001",
                    "type": "foto",
                    "date": None,
                    "phase": "",
                    "description": "",
                    "file_reference": "",
                    "linked_object": "",
                    "status": "TE_VULLEN"
                }
            ],
            "required_evidence": [
                "foto bouwplaatsinrichting",
                "foto grondslag fundering",
                "foto wapening vóór betonstort",
                "foto betonstort",
                "foto riolering vóór aanvullen",
                "foto terreinverharding",
                "foto opleverpunten",
                "ondertekende opleverlijst"
            ]
        }

    def build_progress_vs_planning(self, planning_result):
        return {
            "status": "PLANNING_VOORTGANG_VERGELIJKING_CONCEPT",
            "linked_planning_status": planning_result.get("status", "onbekend"),
            "comparison_fields": [
                "geplande startdatum",
                "werkelijke startdatum",
                "geplande einddatum",
                "verwachte einddatum",
                "vertraging in dagen",
                "oorzaak vertraging",
                "maatregel"
            ],
            "current_delay_days": 0,
            "current_delay_status": "GEEN_VERTRAGING_GEREGISTREERD"
        }

    def build_risk_monitoring(self, construction_execution_result, validation_result):
        execution_risks = construction_execution_result.get("execution_risks", {}).get("risks", [])
        validation_risks = validation_result.get("risk_check", {}).get("risks", [])

        risks = execution_risks + validation_risks

        if not risks:
            risks = ["Geen kritieke risico’s geregistreerd bij start monitoring."]

        return {
            "status": "RISICOMONITORING_CONCEPT",
            "risks_to_monitor": risks,
            "monitoring_actions": [
                "risico’s dagelijks beoordelen",
                "maatregelen koppelen aan verantwoordelijke",
                "impact op planning en kosten registreren",
                "kritieke afwijkingen direct escaleren",
                "Digital Twin bijwerken met risicostatus"
            ]
        }

    def build_delivery_monitoring(self, contract_result):
        delivery_requirements = contract_result.get("delivery_requirements", {}).get("requirements", [])

        return {
            "status": "OPLEVERMONITORING_CONCEPT",
            "linked_contract_status": contract_result.get("status", "onbekend"),
            "delivery_requirements": delivery_requirements,
            "delivery_checklist": [
                "openstaande puntenlijst bijgewerkt",
                "revisiegegevens verzameld",
                "kwaliteitsbewijzen toegevoegd",
                "foto’s en inspectieverslagen toegevoegd",
                "Digital Twin geactualiseerd",
                "projectdossier compleet"
            ]
        }

    def build_warnings(self, construction_execution_result, planning_result):
        warnings = []

        if construction_execution_result.get("status") != "EXECUTION_PLAN_GEREED":
            warnings.append("Uitvoeringsplan is nog niet gereed; monitoring is daardoor beperkt.")

        if planning_result.get("status") != "PLANNING_GEREED":
            warnings.append("Planning is nog niet volledig gereed; voortgangsvergelijking is indicatief.")

        if not warnings:
            warnings.append("Geen kritieke monitoringwaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "MONITORING_ADVIES_CONCEPT",
            "advice": (
                "Gebruik dit monitoringsplan als basis voor bouwplaatsbewaking. "
                "Registreer dagelijks voortgang, afwijkingen, foto’s, acties en risico’s."
            ),
            "next_steps": [
                "dagrapportage activeren",
                "foto- en bewijsregistratie koppelen",
                "voortgang per fase bijhouden",
                "afwijkingenregister dagelijks bijwerken",
                "planning vergelijken met werkelijke voortgang",
                "Digital Twin periodiek actualiseren",
                "opleverdossier voorbereiden"
            ]
        }

    def get_monitoring_result(self):
        return self.monitoring_result

    def run(self):
        print("Site Monitoring / Progress Engine actief")