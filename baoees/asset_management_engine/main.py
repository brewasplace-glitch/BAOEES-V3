from datetime import datetime


class AssetManagementEngine:

    def __init__(self):
        self.asset_result = {}

    def prepare_asset_management_plan(
        self,
        project_result=None,
        as_built_result=None,
        contract_result=None,
        site_monitoring_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        as_built_result = as_built_result or {}
        contract_result = contract_result or {}
        site_monitoring_result = site_monitoring_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result)

        asset_register = self.build_asset_register(project_result, as_built_result)
        maintenance_plan = self.build_maintenance_plan()
        inspection_plan = self.build_inspection_plan()
        warranty_register = self.build_warranty_register(contract_result, as_built_result)
        maintenance_costs = self.build_maintenance_costs(project_result)
        lifecycle_risks = self.build_lifecycle_risks(validation_result, site_monitoring_result)
        digital_twin_handover = self.build_digital_twin_handover(as_built_result)

        self.asset_result = {
            "engine": "AssetManagementEngine",
            "version": "1.0",
            "status": "ASSET_MANAGEMENT_PLAN_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept beheer- en onderhoudsdossier",
            "project_basis": project_basis,
            "asset_register": asset_register,
            "maintenance_plan": maintenance_plan,
            "inspection_plan": inspection_plan,
            "warranty_register": warranty_register,
            "maintenance_costs": maintenance_costs,
            "lifecycle_risks": lifecycle_risks,
            "digital_twin_handover": digital_twin_handover,
            "warnings": self.build_warnings(as_built_result, validation_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Asset Management Engine v1.0 maakt een concept beheer- en onderhoudsplan. "
                "Voor werkelijk beheer moeten definitieve as-built gegevens, garanties, certificaten, "
                "inspecties, leveranciersinformatie en onderhoudsvoorschriften worden toegevoegd."
            )
        }

        return self.asset_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "management_phase": "concept beheer en onderhoud",
            "status": "CONCEPT"
        }

    def build_asset_register(self, project_result, as_built_result):
        return {
            "status": "ASSETREGISTER_AANGEMAAKT",
            "linked_as_built_status": as_built_result.get("status", "onbekend"),
            "assets": [
                {
                    "id": "AST-001",
                    "category": "fundering",
                    "name": "fundering en funderingsbalken",
                    "inspection_frequency": "5-jaarlijks / bij schade of zetting",
                    "maintenance_action": "visuele controle op scheurvorming en verzakking"
                },
                {
                    "id": "AST-002",
                    "category": "constructie",
                    "name": "hoofddraagconstructie",
                    "inspection_frequency": "jaarlijks visueel / 5-jaarlijks technisch",
                    "maintenance_action": "controle op scheuren, corrosie, vervorming en vocht"
                },
                {
                    "id": "AST-003",
                    "category": "dak",
                    "name": "dakconstructie en dakafwerking",
                    "inspection_frequency": "jaarlijks en na zware storm",
                    "maintenance_action": "controle dakbedekking, afwatering en aansluitingen"
                },
                {
                    "id": "AST-004",
                    "category": "riolering",
                    "name": "DWA/HWA leidingen en inspectieputten",
                    "inspection_frequency": "jaarlijks / bij verstopping",
                    "maintenance_action": "reinigen, doorspoelen en inspecteren"
                },
                {
                    "id": "AST-005",
                    "category": "terrein",
                    "name": "verharding, parkeerplaatsen en afwatering",
                    "inspection_frequency": "jaarlijks",
                    "maintenance_action": "controle op verzakking, afwatering en markering"
                }
            ]
        }

    def build_maintenance_plan(self):
        return {
            "status": "ONDERHOUDSPLAN_CONCEPT",
            "maintenance_tasks": [
                {
                    "task": "visuele gebouwinspectie",
                    "frequency": "jaarlijks",
                    "responsible": "beheerder"
                },
                {
                    "task": "dak en hemelwaterafvoer reinigen",
                    "frequency": "jaarlijks / na bladval",
                    "responsible": "onderhoudspartij"
                },
                {
                    "task": "riolering en inspectieputten controleren",
                    "frequency": "jaarlijks",
                    "responsible": "rioolbeheerder / onderhoudspartij"
                },
                {
                    "task": "terreinverharding en parkeerzones controleren",
                    "frequency": "jaarlijks",
                    "responsible": "beheerder"
                },
                {
                    "task": "constructieve controle bij schade of zetting",
                    "frequency": "incidentgestuurd",
                    "responsible": "constructeur"
                }
            ]
        }

    def build_inspection_plan(self):
        return {
            "status": "INSPECTIEPLAN_CONCEPT",
            "inspection_points": [
                "scheurvorming gevels en vloeren",
                "zetting of verzakking terrein",
                "vochtplekken of lekkages",
                "dakafwatering en HWA",
                "riolering en inspectieputten",
                "corrosie of aantasting constructie",
                "veiligheid en toegankelijkheid",
                "parkeer- en terreinmarkering"
            ],
            "inspection_reporting": [
                "datum inspectie",
                "inspecteur",
                "bevinding",
                "foto",
                "urgentie",
                "actiehouder",
                "deadline",
                "status"
            ]
        }

    def build_warranty_register(self, contract_result, as_built_result):
        return {
            "status": "GARANTIEREGISTER_CONCEPT",
            "linked_contract_status": contract_result.get("status", "onbekend"),
            "linked_as_built_status": as_built_result.get("status", "onbekend"),
            "warranties": [
                {
                    "id": "GAR-001",
                    "item": "constructieve werkzaamheden",
                    "period": "nader contractueel vast te leggen",
                    "start_date": None,
                    "end_date": None,
                    "document_reference": ""
                },
                {
                    "id": "GAR-002",
                    "item": "dak en waterdichting",
                    "period": "nader contractueel vast te leggen",
                    "start_date": None,
                    "end_date": None,
                    "document_reference": ""
                },
                {
                    "id": "GAR-003",
                    "item": "riolering en afwatering",
                    "period": "nader contractueel vast te leggen",
                    "start_date": None,
                    "end_date": None,
                    "document_reference": ""
                }
            ]
        }

    def build_maintenance_costs(self, project_result):
        project_type = project_result.get("project_type", "Bouw")
        annual_estimate_eur = 2500

        if project_type.lower() in ["bouw", "woning"]:
            annual_estimate_eur = 1800
        elif project_type.lower() in ["infra", "civiel"]:
            annual_estimate_eur = 3500

        return {
            "status": "ONDERHOUDSKOSTEN_INDICATIEF",
            "annual_maintenance_estimate_eur": annual_estimate_eur,
            "five_year_reserve_eur": annual_estimate_eur * 5,
            "ten_year_reserve_eur": annual_estimate_eur * 10,
            "note": "Bedragen zijn indicatief en moeten projectspecifiek worden geraamd."
        }

    def build_lifecycle_risks(self, validation_result, site_monitoring_result):
        risks = []

        validation_risks = validation_result.get("risk_check", {}).get("risks", [])
        monitoring_risks = site_monitoring_result.get("risk_monitoring", {}).get("risks_to_monitor", [])

        risks.extend(validation_risks)
        risks.extend(monitoring_risks)

        if not risks:
            risks.append("Geen kritieke beheer- en onderhoudsrisico’s geregistreerd.")

        return {
            "status": "LIFECYCLE_RISICO_ANALYSE_CONCEPT",
            "risks": risks,
            "mitigation": [
                "periodieke inspecties uitvoeren",
                "onderhoudslogboek bijhouden",
                "garantietermijnen bewaken",
                "kleine gebreken vroeg herstellen",
                "Digital Twin actueel houden"
            ]
        }

    def build_digital_twin_handover(self, as_built_result):
        return {
            "status": "DIGITAL_TWIN_BEHEEROVERDRACHT_CONCEPT",
            "linked_as_built_status": as_built_result.get("status", "onbekend"),
            "required_handover_data": [
                "as-built tekeningen",
                "assetregister",
                "onderhoudsplan",
                "inspectieplan",
                "garanties en certificaten",
                "opleverpunten",
                "fotoregister",
                "beheerlogboek"
            ]
        }

    def build_warnings(self, as_built_result, validation_result):
        warnings = []

        if as_built_result.get("status") != "AS_BUILT_PACKAGE_GEREED":
            warnings.append("As-built dossier is nog niet volledig gereed.")

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aandachtspunten die invloed kunnen hebben op beheer en onderhoud.")

        if not warnings:
            warnings.append("Geen kritieke beheerwaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "BEHEERADVIES_CONCEPT",
            "advice": (
                "Gebruik dit beheer- en onderhoudsdossier als basis voor de exploitatiefase. "
                "Werk het assetregister bij met definitieve leveranciersgegevens, garanties, "
                "inspectierapporten en onderhoudsinstructies."
            ),
            "next_steps": [
                "definitieve assets controleren",
                "garantiedata invullen",
                "onderhoudspartijen koppelen",
                "inspectiekalender maken",
                "onderhoudsbudget vaststellen",
                "Digital Twin in beheerstand zetten",
                "beheerlogboek openen"
            ]
        }

    def get_asset_result(self):
        return self.asset_result

    def run(self):
        print("Asset Management / Maintenance Engine actief")