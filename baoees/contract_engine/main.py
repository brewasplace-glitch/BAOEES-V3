from datetime import datetime


class ContractEngine:

    def __init__(self):
        self.contract_result = {}

    def prepare_contract_package(
        self,
        project_result=None,
        cost_result=None,
        planning_result=None,
        quantity_result=None,
        specification_result=None,
        tender_result=None,
        validation_result=None,
        drawing_result=None,
        cad_result=None
    ):
        project_result = project_result or {}
        cost_result = cost_result or {}
        planning_result = planning_result or {}
        quantity_result = quantity_result or {}
        specification_result = specification_result or {}
        tender_result = tender_result or {}
        validation_result = validation_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}

        project_basis = self.build_project_basis(project_result)

        contract_strategy = self.build_contract_strategy(
            cost_result=cost_result,
            tender_result=tender_result,
            validation_result=validation_result
        )

        scope_of_work = self.build_scope_of_work(
            specification_result=specification_result,
            quantity_result=quantity_result
        )

        contract_documents = self.build_contract_documents(
            specification_result=specification_result,
            quantity_result=quantity_result,
            tender_result=tender_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        payment_schedule = self.build_payment_schedule(cost_result)
        change_order_rules = self.build_change_order_rules()
        risk_allocation = self.build_risk_allocation(validation_result)
        delivery_requirements = self.build_delivery_requirements(planning_result)
        contract_check = self.build_contract_check(
            tender_result=tender_result,
            specification_result=specification_result,
            validation_result=validation_result
        )
        award_letter = self.build_award_letter(project_basis, contract_strategy)

        self.contract_result = {
            "engine": "ContractEngine",
            "version": "1.0",
            "status": "CONTRACT_PACKAGE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept contract- en opdrachtpakket",
            "project_basis": project_basis,
            "contract_strategy": contract_strategy,
            "scope_of_work": scope_of_work,
            "contract_documents": contract_documents,
            "payment_schedule": payment_schedule,
            "change_order_rules": change_order_rules,
            "risk_allocation": risk_allocation,
            "delivery_requirements": delivery_requirements,
            "contract_check": contract_check,
            "award_letter": award_letter,
            "warnings": self.build_warnings(contract_check, validation_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Contract Engine v1.0 maakt een concept-contractpakket. "
                "Voor ondertekening moeten juridische voorwaarden, aansprakelijkheid, "
                "verzekeringen, garanties, planning, prijs en scope door opdrachtgever, "
                "aannemer en juridisch/technisch deskundigen worden gecontroleerd."
            )
        }

        return self.contract_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "contract_phase": "concept opdrachtvorming",
            "status": "CONCEPT"
        }

    def build_contract_strategy(self, cost_result, tender_result, validation_result):
        estimated_value = cost_result.get("total_estimate", {}).get("mid_eur", 0)
        tender_strategy = tender_result.get("tender_strategy", {}).get(
            "recommended_strategy",
            "nog niet bepaald"
        )
        readiness = tender_result.get("tender_strategy", {}).get(
            "readiness",
            "onbekend"
        )
        qa_decision = validation_result.get("go_no_go_advice", {}).get(
            "decision",
            "onbekend"
        )

        if estimated_value <= 75000:
            contract_type = "eenvoudige opdrachtbrief met bijlagen"
        elif estimated_value <= 250000:
            contract_type = "aannemingsovereenkomst met technische bijlagen"
        else:
            contract_type = "uitgebreide aannemingsovereenkomst / projectcontract"

        return {
            "status": "CONTRACTSTRATEGIE_CONCEPT",
            "recommended_contract_type": contract_type,
            "linked_tender_strategy": tender_strategy,
            "estimated_contract_value_eur": estimated_value,
            "tender_readiness": readiness,
            "qa_qc_decision": qa_decision,
            "note": "Contractstrategie is indicatief en moet juridisch en projectspecifiek worden gecontroleerd."
        }

    def build_scope_of_work(self, specification_result, quantity_result):
        chapters = specification_result.get("chapters", [])
        summary_items = quantity_result.get("boq_summary", {}).get("main_quantities", [])

        scope_items = []

        for chapter in chapters:
            scope_items.append({
                "chapter": chapter.get("chapter"),
                "title": chapter.get("title"),
                "status": chapter.get("status", "CONCEPT")
            })

        return {
            "status": "SCOPE_OF_WORK_CONCEPT",
            "scope_chapters": scope_items,
            "linked_boq_items": summary_items,
            "main_scope": [
                "uitvoeren van werkzaamheden volgens concept-bestek",
                "leveren en verwerken van materialen volgens hoeveelhedenstaat",
                "uitvoeren volgens tekeningen en CAD/BIM-output",
                "coördineren van planning, veiligheid en omgeving",
                "opleveren van revisiegegevens en projectdossier"
            ]
        }

    def build_contract_documents(
        self,
        specification_result,
        quantity_result,
        tender_result,
        drawing_result,
        cad_result
    ):
        return {
            "status": "CONTRACTDOCUMENTENLIJST_GEREED",
            "documents": [
                {
                    "name": "Opdrachtbrief / contract",
                    "required": True,
                    "source": "Contract Engine"
                },
                {
                    "name": "Concept bestek / werkbeschrijving",
                    "required": True,
                    "source": specification_result.get("engine", "Specification Engine")
                },
                {
                    "name": "Hoeveelhedenstaat",
                    "required": True,
                    "source": quantity_result.get("engine", "Quantity Engine")
                },
                {
                    "name": "Aanbestedings-/offertepakket",
                    "required": True,
                    "source": tender_result.get("engine", "Tender Engine")
                },
                {
                    "name": "Tekeningenregister",
                    "required": True,
                    "source": drawing_result.get("engine", "Drawing Export Engine")
                },
                {
                    "name": "CAD/DXF-bestanden",
                    "required": False,
                    "source": cad_result.get("engine", "CAD Export Engine")
                },
                {
                    "name": "Planning",
                    "required": True,
                    "source": "Planning Engine"
                },
                {
                    "name": "Kostenraming / prijsstaat",
                    "required": True,
                    "source": "Cost Estimate Engine"
                },
                {
                    "name": "QA/QC-rapport",
                    "required": True,
                    "source": "Validation Engine"
                }
            ]
        }

    def build_payment_schedule(self, cost_result):
        total = cost_result.get("total_estimate", {}).get("mid_eur", 0)

        return {
            "status": "BETALINGSSCHEMA_CONCEPT",
            "estimated_total_eur": total,
            "payment_terms": [
                {
                    "term": "Termijn 1",
                    "description": "Start werk / mobilisatie",
                    "percent": 10,
                    "amount_eur": round(total * 0.10, 2)
                },
                {
                    "term": "Termijn 2",
                    "description": "Grondwerk en fundering gereed",
                    "percent": 25,
                    "amount_eur": round(total * 0.25, 2)
                },
                {
                    "term": "Termijn 3",
                    "description": "Constructie / ruwbouw gereed",
                    "percent": 30,
                    "amount_eur": round(total * 0.30, 2)
                },
                {
                    "term": "Termijn 4",
                    "description": "Riolering, terrein en afbouw hoofdzaken gereed",
                    "percent": 25,
                    "amount_eur": round(total * 0.25, 2)
                },
                {
                    "term": "Termijn 5",
                    "description": "Oplevering en goedkeuring dossier",
                    "percent": 10,
                    "amount_eur": round(total * 0.10, 2)
                }
            ],
            "note": "Betalingsschema is indicatief en moet contractueel worden afgestemd."
        }

    def build_change_order_rules(self):
        return {
            "status": "MEER_MINDERWERK_REGELS_CONCEPT",
            "rules": [
                "meerwerk alleen uitvoeren na schriftelijke opdracht",
                "minderwerk verrekenen op basis van overeengekomen eenheidsprijzen",
                "afwijkingen in bodemgesteldheid afzonderlijk melden en vastleggen",
                "wijzigingen in tekeningen alleen volgens formele revisieprocedure",
                "prijsconsequenties en planningseffecten vooraf schriftelijk vastleggen",
                "mondelinge opdrachten zijn niet leidend zonder schriftelijke bevestiging"
            ]
        }

    def build_risk_allocation(self, validation_result):
        risks = validation_result.get("risk_check", {}).get("risks", [])

        return {
            "status": "RISICOVERDELING_CONCEPT",
            "risks_from_validation": risks,
            "allocation": [
                {
                    "risk": "maatvoering en revisies",
                    "owner": "opdrachtgever en adviseur tot definitieve stukken; aannemer controleplicht bij uitvoering"
                },
                {
                    "risk": "bodem en fundering",
                    "owner": "nader te bepalen na definitief geotechnisch onderzoek"
                },
                {
                    "risk": "uitvoeringsmethode",
                    "owner": "aannemer"
                },
                {
                    "risk": "vergunningvoorwaarden",
                    "owner": "opdrachtgever / adviseur, tenzij uitvoeringsgerelateerd"
                },
                {
                    "risk": "hoeveelheden",
                    "owner": "contractueel vast te leggen: verrekenbaar of lumpsum"
                }
            ]
        }

    def build_delivery_requirements(self, planning_result):
        return {
            "status": "OPLEVERVOORWAARDEN_CONCEPT",
            "requirements": [
                "werk uitvoeren volgens laatste goedgekeurde tekeningen",
                "opleveren inclusief revisietekeningen en projectdossier",
                "afwijkingen en herstelpunten vastleggen in opleverlijst",
                "garanties, certificaten en bewijsstukken toevoegen aan dossier",
                "bronvermelding en auditlog behouden in projectmap",
                "Digital Twin bijwerken met definitieve opleverinformatie"
            ],
            "linked_planning_status": planning_result.get("status", "onbekend")
        }

    def build_contract_check(self, tender_result, specification_result, validation_result):
        checks = []

        if tender_result.get("status") == "TENDER_PACKAGE_GEREED":
            checks.append("Tenderpakket aanwezig")
        else:
            checks.append("Tenderpakket ontbreekt of is niet gereed")

        if specification_result.get("status") == "SPECIFICATION_GEREED":
            checks.append("Concept-bestek aanwezig")
        else:
            checks.append("Concept-bestek ontbreekt of is niet gereed")

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision", "onbekend")
        checks.append(f"QA/QC beslissing: {qa_decision}")

        if qa_decision in ["GO", "GO_MET_AANDACHTSPUNTEN"]:
            readiness = "CONTRACT_CONCEPT_GEREED"
        else:
            readiness = "CONTRACT_NOG_NIET_GEREED"

        return {
            "status": "CONTRACTCONTROLE_GEREED",
            "readiness": readiness,
            "checks": checks
        }

    def build_award_letter(self, project_basis, contract_strategy):
        return {
            "status": "OPDRACHTBRIEF_CONCEPT",
            "subject": f"Concept opdrachtverlening - {project_basis['project_name']}",
            "body": (
                f"Geachte heer/mevrouw,\n\n"
                f"Hierbij ontvangt u de concept-opdrachtverlening voor het project "
                f"'{project_basis['project_name']}' te {project_basis['location']}.\n\n"
                f"De werkzaamheden worden uitgevoerd op basis van het contracttype: "
                f"{contract_strategy['recommended_contract_type']}.\n\n"
                f"De contractstukken bestaan uit de opdrachtbrief, het bestek/de werkbeschrijving, "
                f"de hoeveelhedenstaat, tekeningen, planning, prijsstaat en relevante projectbijlagen.\n\n"
                f"Voor ondertekening moeten scope, prijs, planning, risicoverdeling, garanties en "
                f"contractvoorwaarden definitief worden gecontroleerd.\n\n"
                f"Met vriendelijke groet,\n"
                f"BAOEES / Brewster Engineering"
            )
        }

    def build_warnings(self, contract_check, validation_result):
        warnings = []

        if contract_check.get("readiness") != "CONTRACT_CONCEPT_GEREED":
            warnings.append("Contractpakket is nog niet gereed voor formele opdrachtverlening.")

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aan dat herstel nodig is vóór contractvorming.")

        if not warnings:
            warnings.append("Geen kritieke contractwaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "CONTRACTADVIES_CONCEPT",
            "advice": (
                "Gebruik dit contractpakket als conceptbasis voor opdrachtverlening. "
                "Laat de contractstukken juridisch en technisch controleren vóór ondertekening."
            ),
            "next_steps": [
                "definitieve aannemer of opdrachtnemer selecteren",
                "prijs en scope vastleggen",
                "contractvoorwaarden toevoegen",
                "verzekeringen en garanties controleren",
                "betalingsschema definitief maken",
                "contract laten controleren",
                "opdrachtbrief ondertekenen"
            ]
        }

    def get_contract_result(self):
        return self.contract_result

    def run(self):
        print("Contract / Agreement Engine actief")