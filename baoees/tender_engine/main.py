from datetime import datetime


class TenderEngine:

    def __init__(self):
        self.tender_result = {}

    def prepare_tender_package(
        self,
        project_result=None,
        cost_result=None,
        planning_result=None,
        quantity_result=None,
        specification_result=None,
        validation_result=None,
        drawing_result=None,
        cad_result=None
    ):
        project_result = project_result or {}
        cost_result = cost_result or {}
        planning_result = planning_result or {}
        quantity_result = quantity_result or {}
        specification_result = specification_result or {}
        validation_result = validation_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}

        project_basis = self.build_project_basis(project_result)

        tender_strategy = self.build_tender_strategy(
            project_basis=project_basis,
            cost_result=cost_result,
            validation_result=validation_result
        )

        document_list = self.build_document_list(
            quantity_result=quantity_result,
            specification_result=specification_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        tender_planning = self.build_tender_planning(planning_result)
        award_criteria = self.build_award_criteria(project_basis)
        bidder_requirements = self.build_bidder_requirements(project_basis)
        risk_and_contract_points = self.build_risk_and_contract_points(validation_result)
        evaluation_matrix = self.build_evaluation_matrix(award_criteria)
        request_letter = self.build_request_letter(project_basis, tender_strategy)

        self.tender_result = {
            "engine": "TenderEngine",
            "version": "1.0",
            "status": "TENDER_PACKAGE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept aanbestedings- en offertepakket",
            "project_basis": project_basis,
            "tender_strategy": tender_strategy,
            "document_list": document_list,
            "tender_planning": tender_planning,
            "award_criteria": award_criteria,
            "bidder_requirements": bidder_requirements,
            "risk_and_contract_points": risk_and_contract_points,
            "evaluation_matrix": evaluation_matrix,
            "request_letter": request_letter,
            "warnings": self.build_warnings(validation_result, specification_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Tender Engine v1.0 maakt een concept-aanbestedingspakket. "
                "Voor formele aanbesteding moeten juridische voorwaarden, contractvorm, "
                "selectiecriteria en gunningscriteria door opdrachtgever en deskundigen worden gecontroleerd."
            )
        }

        return self.tender_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "status": "CONCEPT"
        }

    def build_tender_strategy(self, project_basis, cost_result, validation_result):
        total_mid = cost_result.get("total_estimate", {}).get("mid_eur", 0)
        quality_score = validation_result.get("quality_score", {}).get("score", 0)

        if total_mid <= 75000:
            strategy = "meervoudig onderhandse offerteaanvraag"
            bidder_count = 3
        elif total_mid <= 250000:
            strategy = "meervoudig onderhandse aanbesteding"
            bidder_count = 3
        else:
            strategy = "formele aanbesteding / projectgerichte selectie"
            bidder_count = 5

        if quality_score < 70:
            readiness = "NIET_GEREED_VOOR_AANBESTEDING"
        elif quality_score < 85:
            readiness = "GEREED_MET_AANDACHTSPUNTEN"
        else:
            readiness = "GEREED_VOOR_CONCEPT_AANBESTEDING"

        return {
            "status": "AANBESTEDINGSSTRATEGIE_CONCEPT",
            "recommended_strategy": strategy,
            "recommended_bidder_count": bidder_count,
            "estimated_project_value_eur": total_mid,
            "readiness": readiness,
            "note": "Strategie is indicatief en moet worden afgestemd op opdrachtgever, regelgeving en contractvorm."
        }

    def build_document_list(self, quantity_result, specification_result, drawing_result, cad_result):
        return {
            "status": "DOCUMENTENLIJST_GEREED",
            "documents": [
                {
                    "name": "Projectomschrijving",
                    "required": True,
                    "source": "Project Analyzer / Reporting Engine"
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
                    "name": "Kostenraming",
                    "required": True,
                    "source": "Cost Estimate Engine"
                },
                {
                    "name": "Planning",
                    "required": True,
                    "source": "Planning Engine"
                },
                {
                    "name": "Tekeningenregister",
                    "required": True,
                    "source": drawing_result.get("engine", "Drawing Export Engine")
                },
                {
                    "name": "CAD/DXF bestanden",
                    "required": False,
                    "source": cad_result.get("engine", "CAD Export Engine")
                },
                {
                    "name": "QA/QC rapport",
                    "required": True,
                    "source": "Validation Engine"
                }
            ]
        }

    def build_tender_planning(self, planning_result):
        return {
            "status": "AANBESTEDINGSPLANNING_CONCEPT",
            "steps": [
                {
                    "step": "Aanbestedingsstukken gereedmaken",
                    "duration_days": 3
                },
                {
                    "step": "Uitnodiging/offerteaanvraag verzenden",
                    "duration_days": 1
                },
                {
                    "step": "Vragenronde",
                    "duration_days": 7
                },
                {
                    "step": "Nota van inlichtingen",
                    "duration_days": 3
                },
                {
                    "step": "Inschrijftermijn",
                    "duration_days": 14
                },
                {
                    "step": "Beoordeling inschrijvingen",
                    "duration_days": 5
                },
                {
                    "step": "Gunningsadvies",
                    "duration_days": 3
                },
                {
                    "step": "Contractvorming",
                    "duration_days": 7
                }
            ],
            "linked_project_planning_status": planning_result.get("status", "onbekend")
        }

    def build_award_criteria(self, project_basis):
        return {
            "status": "GUNNINGSCRITERIA_CONCEPT",
            "criteria": [
                {
                    "criterion": "Prijs",
                    "weight_percent": 45,
                    "description": "Laagste realistische inschrijfsom op basis van volledige scope."
                },
                {
                    "criterion": "Kwaliteit en aanpak",
                    "weight_percent": 25,
                    "description": "Plan van aanpak, uitvoeringsmethode en risicobeheersing."
                },
                {
                    "criterion": "Planning",
                    "weight_percent": 15,
                    "description": "Haalbare planning en beschikbaarheid."
                },
                {
                    "criterion": "Duurzaamheid / hinderbeperking",
                    "weight_percent": 10,
                    "description": "Beperking emissies, afval, transport en omgevingshinder."
                },
                {
                    "criterion": "Ervaring en referenties",
                    "weight_percent": 5,
                    "description": "Relevante ervaring met vergelijkbare projecten."
                }
            ]
        }

    def build_bidder_requirements(self, project_basis):
        return {
            "status": "INSCHRIJVINGSEISEN_CONCEPT",
            "requirements": [
                "inschrijver moet aantoonbare ervaring hebben met vergelijkbare werkzaamheden",
                "inschrijver controleert alle hoeveelheden en tekeningen vóór inschrijving",
                "inschrijver vermeldt afwijkingen, uitsluitingen en aannames expliciet",
                "inschrijver levert planning, prijsstaat en plan van aanpak aan",
                "inschrijver houdt rekening met vergunningvoorwaarden en veiligheidsvoorschriften",
                "inschrijver bezoekt indien nodig de projectlocatie vóór inschrijving"
            ]
        }

    def build_risk_and_contract_points(self, validation_result):
        risks = validation_result.get("risk_check", {}).get("risks", [])

        contract_points = [
            "meer- en minderwerk alleen na schriftelijke opdracht",
            "onvoorziene bodemomstandigheden apart verrekenen",
            "wijzigingen in vergunningseisen apart beoordelen",
            "definitieve hoeveelheden gaan voor indicatieve hoeveelheden",
            "laatste revisie van tekeningen en bestek is leidend"
        ]

        return {
            "status": "RISICO_CONTRACTPUNTEN_CONCEPT",
            "risks_from_validation": risks,
            "contract_points": contract_points
        }

    def build_evaluation_matrix(self, award_criteria):
        rows = []

        for criterion in award_criteria.get("criteria", []):
            rows.append({
                "criterion": criterion["criterion"],
                "weight_percent": criterion["weight_percent"],
                "score_bidder_1": None,
                "score_bidder_2": None,
                "score_bidder_3": None,
                "notes": ""
            })

        return {
            "status": "BEOORDELINGSMATRIX_CONCEPT",
            "matrix": rows,
            "score_scale": "0-10",
            "note": "Scores moeten na ontvangst van inschrijvingen worden ingevuld."
        }

    def build_request_letter(self, project_basis, tender_strategy):
        return {
            "status": "OFFERTEAANVRAAG_CONCEPT",
            "subject": f"Offerteaanvraag - {project_basis['project_name']}",
            "body": (
                f"Geachte heer/mevrouw,\n\n"
                f"Namens de opdrachtgever verzoeken wij u een aanbieding uit te brengen voor het project "
                f"'{project_basis['project_name']}' te {project_basis['location']}.\n\n"
                f"De aanvraag betreft een {tender_strategy['recommended_strategy']} op basis van de bijgevoegde "
                f"projectomschrijving, concept-bestek, hoeveelhedenstaat, tekeningen en planning.\n\n"
                f"Wij verzoeken u uw aanbieding te voorzien van prijsopgave, planning, plan van aanpak, "
                f"eventuele uitsluitingen en aandachtspunten.\n\n"
                f"Met vriendelijke groet,\n"
                f"BAOEES / Brewster Engineering"
            )
        }

    def build_warnings(self, validation_result, specification_result):
        warnings = []

        decision = validation_result.get("go_no_go_advice", {}).get("decision")

        if decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aan dat het project nog niet volledig aanbestedingsgereed is.")

        spec_status = specification_result.get("status")
        if spec_status != "SPECIFICATION_GEREED":
            warnings.append("Concept-bestek is nog niet gereed of ontbreekt.")

        if not warnings:
            warnings.append("Geen kritieke aanbestedingswaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "AANBESTEDINGSADVIES_CONCEPT",
            "advice": (
                "Gebruik dit tenderpakket als basis voor offerteaanvraag of aanbesteding. "
                "Controleer voor verzending alle contractvoorwaarden, hoeveelheden, tekeningen en risico’s."
            ),
            "next_steps": [
                "definitieve aanbestedingsvorm kiezen",
                "te benaderen partijen selecteren",
                "offerteaanvraag verzenden",
                "vragenronde organiseren",
                "inschrijvingen beoordelen",
                "gunningsadvies opstellen",
                "contractstukken definitief maken"
            ]
        }

    def get_tender_result(self):
        return self.tender_result

    def run(self):
        print("Tender / Procurement Engine actief")