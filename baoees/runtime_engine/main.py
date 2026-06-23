from datetime import datetime


class RuntimeEngine:

    def __init__(self):
        self.runtime_result = {}

    def create_runtime_log(
        self,
        project_result=None,
        engine_results=None,
        digital_twin_data=None
    ):
        project_result = project_result or {}
        engine_results = engine_results or {}
        digital_twin_data = digital_twin_data or {}

        project_basis = self.build_project_basis(project_result)
        engine_sequence = self.build_engine_sequence(engine_results)
        status_summary = self.build_status_summary(engine_results)
        runtime_checks = self.build_runtime_checks(engine_results, digital_twin_data)
        error_handling_plan = self.build_error_handling_plan()
        autonomous_mode = self.build_autonomous_mode()
        next_runtime_steps = self.build_next_runtime_steps(status_summary)

        self.runtime_result = {
            "engine": "RuntimeEngine",
            "version": "1.0",
            "status": "RUNTIME_ORCHESTRATION_LOG_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept runtime en orchestration",
            "project_basis": project_basis,
            "engine_sequence": engine_sequence,
            "status_summary": status_summary,
            "runtime_checks": runtime_checks,
            "error_handling_plan": error_handling_plan,
            "autonomous_mode": autonomous_mode,
            "next_runtime_steps": next_runtime_steps,
            "warnings": self.build_warnings(status_summary),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Runtime Engine v1.0 maakt een conceptuele runtime- en orchestration-log. "
                "Voor volledige autonome uitvoering zijn echte taakwachtrijen, foutafhandeling, "
                "statusopslag, rollback, validatie en logging per engine nodig."
            )
        }

        return self.runtime_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "runtime_phase": "concept autonome workflow-aansturing",
            "status": "CONCEPT"
        }

    def build_engine_sequence(self, engine_results):
        sequence = []

        for index, key in enumerate(engine_results.keys(), start=1):
            result = engine_results.get(key, {})
            sequence.append({
                "order": index,
                "engine_key": key,
                "engine_name": result.get("engine", key),
                "status": result.get("status", "onbekend"),
                "executed": True if result else False
            })

        return {
            "status": "ENGINE_SEQUENCE_GEREGISTREERD",
            "total_engines": len(sequence),
            "sequence": sequence
        }

    def build_status_summary(self, engine_results):
        total = len(engine_results)
        completed = 0
        unknown = 0
        warning = 0

        statuses = {}

        for key, result in engine_results.items():
            status = result.get("status", "onbekend")
            statuses[key] = status

            if status == "onbekend":
                unknown += 1
            elif "GEREED" in status or "ANALYSIS" in status or "PLAN" in status:
                completed += 1
            else:
                warning += 1

        if total == 0:
            completion_percent = 0
        else:
            completion_percent = round((completed / total) * 100, 1)

        if completion_percent >= 90:
            runtime_status = "RUNTIME_FLOW_GOED"
        elif completion_percent >= 70:
            runtime_status = "RUNTIME_FLOW_MET_AANDACHTSPUNTEN"
        else:
            runtime_status = "RUNTIME_FLOW_ONVOLLEDIG"

        return {
            "status": "ENGINE_STATUS_SUMMARY_GEREED",
            "runtime_status": runtime_status,
            "total_engines": total,
            "completed_engines": completed,
            "unknown_status_engines": unknown,
            "warning_status_engines": warning,
            "completion_percent": completion_percent,
            "engine_statuses": statuses
        }

    def build_runtime_checks(self, engine_results, digital_twin_data):
        objects = digital_twin_data.get("objects", [])
        sources = digital_twin_data.get("sources", [])

        checks = [
            {
                "check": "projectanalyse gestart",
                "status": "OK" if engine_results.get("project") else "TE_CONTROLEREN"
            },
            {
                "check": "Digital Twin bevat objecten",
                "status": "OK" if len(objects) > 0 else "TE_CONTROLEREN"
            },
            {
                "check": "STEE bronregistratie aanwezig",
                "status": "OK" if engine_results.get("stee") else "TE_CONTROLEREN"
            },
            {
                "check": "QA/QC controle aanwezig",
                "status": "OK" if engine_results.get("validation") else "TE_CONTROLEREN"
            },
            {
                "check": "projectexport aanwezig",
                "status": "OK" if engine_results.get("project_export") else "TE_CONTROLEREN"
            },
            {
                "check": "oplever- en beheerfase aanwezig",
                "status": "OK" if engine_results.get("asset_management") else "TE_CONTROLEREN"
            }
        ]

        return {
            "status": "RUNTIME_CHECKS_GEREED",
            "digital_twin_object_count": len(objects),
            "digital_twin_source_count": len(sources),
            "checks": checks
        }

    def build_error_handling_plan(self):
        return {
            "status": "FOUTAFHANDELING_CONCEPT",
            "rules": [
                {
                    "error_type": "missing_input",
                    "action": "AAIE inschakelen om ontbrekende gegevens als aanname te markeren"
                },
                {
                    "error_type": "engine_failure",
                    "action": "engine-status op FOUT zetten en workflow niet definitief vrijgeven"
                },
                {
                    "error_type": "validation_warning",
                    "action": "waarschuwing opnemen in QA/QC en projectdossier"
                },
                {
                    "error_type": "missing_source",
                    "action": "STEE bronregistratie aanvullen of bron als ontbrekend markeren"
                },
                {
                    "error_type": "export_failure",
                    "action": "export opnieuw proberen en fout opnemen in runtime-log"
                }
            ]
        }

    def build_autonomous_mode(self):
        return {
            "status": "AUTONOMOUS_MODE_CONCEPT",
            "mode": "semi-autonoom / volledig autonoom voorbereid",
            "supported_modes": [
                "assistentmodus",
                "semi-autonoom",
                "volledig autonoom met QA/QC-blokkades"
            ],
            "control_points": [
                "na projectanalyse",
                "na ontwerpvarianten",
                "na constructie/geotechniek",
                "na vergunningstrategie",
                "na kosten/planning",
                "na bestek/contract",
                "voor uitvoering",
                "voor oplevering"
            ]
        }

    def build_next_runtime_steps(self, status_summary):
        return {
            "status": "VOLGENDE_RUNTIME_STAPPEN_CONCEPT",
            "runtime_status": status_summary.get("runtime_status"),
            "next_steps": [
                "engine-resultaten standaardiseren",
                "centrale pipeline-configuratie maken",
                "runtime-log exporteren naar projectmap",
                "foutafhandeling per engine afdwingen",
                "QA/QC-blokkades koppelen aan workflow",
                "autonome modus instelbaar maken vanaf startscherm",
                "projectanalyse laten draaien via Runtime Engine in plaats van losse core-aanroep"
            ]
        }

    def build_warnings(self, status_summary):
        warnings = []

        if status_summary.get("completion_percent", 0) < 90:
            warnings.append("Niet alle engines lijken volledig gereed volgens de runtime-statussamenvatting.")

        if status_summary.get("unknown_status_engines", 0) > 0:
            warnings.append("Een of meer engines hebben een onbekende status.")

        if not warnings:
            warnings.append("Geen kritieke runtimewaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "RUNTIME_ADVIES_CONCEPT",
            "advice": (
                "Gebruik deze Runtime Engine als centrale controlelaag boven de BAOEES workflow. "
                "De volgende stap is om alle engine-aanroepen via één gestandaardiseerde pipeline "
                "te laten lopen met logging, foutafhandeling en QA/QC-blokkades."
            ),
            "next_steps": [
                "runtime pipeline-configuratie toevoegen",
                "engine-statusmodel standaardiseren",
                "fouten en waarschuwingen centraal loggen",
                "workflow automatisch stoppen bij kritieke QA/QC-fouten",
                "runtime-log toevoegen aan projectexport",
                "autonome modus koppelen aan startscherm"
            ]
        }

    def get_runtime_result(self):
        return self.runtime_result

    def run(self):
        print("Runtime / Orchestration Engine actief")