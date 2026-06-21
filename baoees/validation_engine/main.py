from datetime import datetime


class ValidationEngine:

    def __init__(self):
        self.validation_result = {}

    def validate_project(
        self,
        project_result=None,
        aaie_result=None,
        variant_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        reporting_result=None,
        export_result=None,
        document_result=None,
        drawing_result=None,
        cad_result=None,
        cost_result=None,
        planning_result=None,
        traffic_parking_result=None,
        drainage_result=None,
        aerius_result=None,
        gis_result=None,
        stee_result=None,
        workflow_result=None,
        digital_twin_data=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        variant_result = variant_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        reporting_result = reporting_result or {}
        export_result = export_result or {}
        document_result = document_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}
        cost_result = cost_result or {}
        planning_result = planning_result or {}
        traffic_parking_result = traffic_parking_result or {}
        drainage_result = drainage_result or {}
        aerius_result = aerius_result or {}
        gis_result = gis_result or {}
        stee_result = stee_result or {}
        workflow_result = workflow_result or {}
        digital_twin_data = digital_twin_data or {}

        engine_results = {
            "project_analyzer": project_result,
            "aaie": aaie_result,
            "variant_engine": variant_result,
            "geo_engine": geo_result,
            "structural_engine": structural_result,
            "permit_engine": permit_result,
            "reporting_engine": reporting_result,
            "project_export_engine": export_result,
            "document_export_engine": document_result,
            "drawing_export_engine": drawing_result,
            "cad_export_engine": cad_result,
            "cost_engine": cost_result,
            "planning_engine": planning_result,
            "traffic_parking_engine": traffic_parking_result,
            "drainage_sewerage_engine": drainage_result,
            "aerius_engine": aerius_result,
            "gis_map_engine": gis_result,
            "stee": stee_result,
            "workflow_engine": workflow_result
        }

        completeness = self.check_completeness(engine_results)
        status_check = self.check_statuses(engine_results)
        warning_check = self.collect_warnings(engine_results)
        consistency_check = self.check_consistency(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            cost_result=cost_result,
            planning_result=planning_result,
            traffic_parking_result=traffic_parking_result,
            drainage_result=drainage_result,
            aerius_result=aerius_result,
            gis_result=gis_result,
            digital_twin_data=digital_twin_data
        )
        risk_check = self.assess_project_risks(
            warning_check=warning_check,
            consistency_check=consistency_check,
            geo_result=geo_result,
            structural_result=structural_result,
            traffic_parking_result=traffic_parking_result,
            drainage_result=drainage_result,
            aerius_result=aerius_result,
            gis_result=gis_result
        )

        quality_score = self.calculate_quality_score(
            completeness=completeness,
            status_check=status_check,
            warning_check=warning_check,
            consistency_check=consistency_check,
            risk_check=risk_check
        )

        go_no_go = self.build_go_no_go_advice(
            quality_score=quality_score,
            risk_check=risk_check,
            completeness=completeness,
            status_check=status_check
        )

        self.validation_result = {
            "engine": "ValidationEngine",
            "version": "1.0",
            "status": "VALIDATION_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "automatische QA/QC controle",
            "completeness": completeness,
            "status_check": status_check,
            "warning_check": warning_check,
            "consistency_check": consistency_check,
            "risk_check": risk_check,
            "quality_score": quality_score,
            "go_no_go_advice": go_no_go,
            "recommendation": self.build_recommendation(
                quality_score=quality_score,
                go_no_go=go_no_go,
                risk_check=risk_check
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Validation & QA/QC Engine voert een automatische controle uit op volledigheid, "
                "statussen, waarschuwingen en interne consistentie. Dit vervangt geen menselijke "
                "eindcontrole door bevoegde deskundigen."
            )
        }

        return self.validation_result

    def check_completeness(self, engine_results):
        required_engines = list(engine_results.keys())

        missing_engines = []
        available_engines = []

        for engine_name, result in engine_results.items():
            if not result:
                missing_engines.append(engine_name)
            else:
                available_engines.append(engine_name)

        total = len(required_engines)
        available = len(available_engines)

        if total == 0:
            completeness_percent = 0
        else:
            completeness_percent = available / total * 100

        if completeness_percent == 100:
            status = "VOLLEDIG"
        elif completeness_percent >= 85:
            status = "BIJNA_VOLLEDIG"
        else:
            status = "ONVOLLEDIG"

        return {
            "required_engine_count": total,
            "available_engine_count": available,
            "missing_engine_count": len(missing_engines),
            "available_engines": available_engines,
            "missing_engines": missing_engines,
            "completeness_percent": round(completeness_percent, 1),
            "status": status
        }

    def check_statuses(self, engine_results):
        status_rows = []
        not_ready = []

        positive_keywords = [
            "GEREED",
            "BEREKEND",
            "AANGEMAAKT",
            "VOORBEREID"
        ]

        for engine_name, result in engine_results.items():
            status = result.get("status", "GEEN_STATUS") if result else "ONTBREEKT"

            is_ready = any(keyword in str(status) for keyword in positive_keywords)

            status_rows.append({
                "engine": engine_name,
                "status": status,
                "ready": is_ready
            })

            if not is_ready:
                not_ready.append({
                    "engine": engine_name,
                    "status": status
                })

        if not not_ready:
            overall_status = "ALLE_ENGINES_GEREED"
        elif len(not_ready) <= 2:
            overall_status = "KLEINE_AANDACHTSPUNTEN"
        else:
            overall_status = "MEERDERE_ENGINES_NIET_GEREED"

        return {
            "overall_status": overall_status,
            "not_ready_count": len(not_ready),
            "not_ready": not_ready,
            "engine_statuses": status_rows
        }

    def collect_warnings(self, engine_results):
        warning_rows = []
        total_warnings = 0
        critical_warning_count = 0

        critical_keywords = [
            "voldoet indicatief niet",
            "parkeer tekort",
            "hoog",
            "kritieke",
            "AERIUS",
            "Natura 2000",
            "grondwater",
            "fundering vraagt",
            "vergunningrisico"
        ]

        for engine_name, result in engine_results.items():
            warnings = []

            if isinstance(result, dict):
                if isinstance(result.get("warnings"), list):
                    warnings.extend(result.get("warnings"))

                if isinstance(result.get("permit_warnings"), list):
                    warnings.extend(result.get("permit_warnings"))

            engine_critical_count = 0

            for warning in warnings:
                warning_text = str(warning)
                is_critical = any(
                    keyword.lower() in warning_text.lower()
                    for keyword in critical_keywords
                )

                if is_critical:
                    engine_critical_count += 1

            total_warnings += len(warnings)
            critical_warning_count += engine_critical_count

            warning_rows.append({
                "engine": engine_name,
                "warning_count": len(warnings),
                "critical_warning_count": engine_critical_count,
                "warnings": warnings
            })

        if critical_warning_count == 0 and total_warnings <= 5:
            status = "WAARSCHUWINGEN_LAAG"
        elif critical_warning_count <= 3:
            status = "WAARSCHUWINGEN_MIDDEL"
        else:
            status = "WAARSCHUWINGEN_HOOG"

        return {
            "status": status,
            "total_warnings": total_warnings,
            "critical_warning_count": critical_warning_count,
            "warnings_by_engine": warning_rows
        }

    def check_consistency(
        self,
        project_result,
        geo_result,
        structural_result,
        cost_result,
        planning_result,
        traffic_parking_result,
        drainage_result,
        aerius_result,
        gis_result,
        digital_twin_data
    ):
        issues = []

        project_country = project_result.get("country")
        geo_country = geo_result.get("country")
        structural_country = structural_result.get("country")

        if geo_country and project_country and geo_country != project_country:
            issues.append("Land in Geo Engine wijkt af van projectgegevens.")

        if structural_country and project_country and structural_country != project_country:
            issues.append("Land in Structural Engine wijkt af van projectgegevens.")

        recommended_foundation = geo_result.get("recommended_foundation", {}).get(
            "selected_foundation_type"
        )

        structural_foundation = structural_result.get("foundation_assessment", {}).get(
            "recommended_foundation_type"
        )

        if recommended_foundation and structural_foundation:
            if recommended_foundation != structural_foundation:
                issues.append("Funderingsadvies Geo Engine en Structural Engine wijkt af.")

        cost_basis = cost_result.get("project_basis", {})
        planning_basis = planning_result.get("project_basis", {})

        cost_area = cost_basis.get("gross_floor_area_m2")
        planning_area = planning_basis.get("gross_floor_area_m2")

        if cost_area and planning_area:
            try:
                if abs(float(cost_area) - float(planning_area)) > 1:
                    issues.append("Vloeroppervlak in Cost Engine en Planning Engine wijkt af.")
            except ValueError:
                issues.append("Vloeroppervlak kon niet consistent worden gecontroleerd.")

        parking_status = traffic_parking_result.get("parking_balance", {}).get("status", "")
        if "TEKORT" in parking_status:
            issues.append("Parkeerbalans geeft indicatief tekort aan.")

        drainage_status = drainage_result.get("storage_and_infiltration", {}).get("status", "")
        if "AANDACHTSPUNT" in drainage_status:
            issues.append("Afwatering/infiltratie geeft aandachtspunt aan.")

        natura_status = gis_result.get("distance_checks", {}).get("status", "")
        aerius_status = aerius_result.get("status", "")

        if aerius_status and not natura_status:
            issues.append("AERIUS-resultaat aanwezig, maar GIS/Natura afstandscontrole ontbreekt.")

        dt_objects = digital_twin_data.get("objects", [])
        if isinstance(dt_objects, list) and len(dt_objects) < 5:
            issues.append("Digital Twin bevat weinig objecten; controleer of alle resultaten zijn toegevoegd.")

        if not issues:
            status = "CONSISTENTIE_OK"
        elif len(issues) <= 3:
            status = "CONSISTENTIE_AANDACHTSPUNTEN"
        else:
            status = "CONSISTENTIE_RISICO"

        return {
            "status": status,
            "issue_count": len(issues),
            "issues": issues
        }

    def assess_project_risks(
        self,
        warning_check,
        consistency_check,
        geo_result,
        structural_result,
        traffic_parking_result,
        drainage_result,
        aerius_result,
        gis_result
    ):
        risks = []

        geo_recommendation = geo_result.get("recommended_foundation", {}).get(
            "selected_foundation_type"
        )

        if geo_recommendation in ["paalfundering", "nader_geotechnisch_onderzoek"]:
            risks.append({
                "domain": "geotechniek",
                "risk": "Funderingsrisico of aanvullend geotechnisch onderzoek nodig.",
                "level": "middel"
            })

        structural_status = structural_result.get("recommendation", {}).get("status")
        if structural_status == "AANDACHTSPUNTEN":
            risks.append({
                "domain": "constructie",
                "risk": "Constructieve aandachtspunten aanwezig.",
                "level": "middel"
            })

        parking_status = traffic_parking_result.get("parking_balance", {}).get("status", "")
        if "TEKORT" in parking_status:
            risks.append({
                "domain": "verkeer en parkeren",
                "risk": "Indicatief parkeer tekort.",
                "level": "hoog"
            })

        drainage_status = drainage_result.get("storage_and_infiltration", {}).get("status", "")
        if "GRONDWATER_HOOG" in drainage_status:
            risks.append({
                "domain": "riolering en afwatering",
                "risk": "Infiltratie mogelijk beperkt door hoge grondwaterstand.",
                "level": "middel"
            })

        aerius_warnings = aerius_result.get("permit_warnings", [])
        if len(aerius_warnings) >= 2:
            risks.append({
                "domain": "stikstof / AERIUS",
                "risk": "Stikstofwaarschuwingen aanwezig.",
                "level": "middel"
            })

        gis_coordinates = gis_result.get("coordinates", {})
        if gis_coordinates.get("status") == "COORDINATEN_PLACEHOLDER":
            risks.append({
                "domain": "GIS / locatie",
                "risk": "Exacte coördinaten ontbreken nog.",
                "level": "laag"
            })

        if warning_check.get("critical_warning_count", 0) > 3:
            risks.append({
                "domain": "algemeen",
                "risk": "Meerdere kritieke waarschuwingen aanwezig.",
                "level": "hoog"
            })

        if consistency_check.get("issue_count", 0) > 3:
            risks.append({
                "domain": "consistentie",
                "risk": "Meerdere inconsistenties tussen engines.",
                "level": "hoog"
            })

        high_count = len([risk for risk in risks if risk["level"] == "hoog"])
        medium_count = len([risk for risk in risks if risk["level"] == "middel"])
        low_count = len([risk for risk in risks if risk["level"] == "laag"])

        if high_count > 0:
            status = "PROJECTRISICO_HOOG"
        elif medium_count > 0:
            status = "PROJECTRISICO_MIDDEL"
        else:
            status = "PROJECTRISICO_LAAG"

        return {
            "status": status,
            "risk_count": len(risks),
            "high_risk_count": high_count,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "risks": risks
        }

    def calculate_quality_score(
        self,
        completeness,
        status_check,
        warning_check,
        consistency_check,
        risk_check
    ):
        score = 100.0

        missing_count = completeness.get("missing_engine_count", 0)
        not_ready_count = status_check.get("not_ready_count", 0)
        critical_warning_count = warning_check.get("critical_warning_count", 0)
        consistency_issue_count = consistency_check.get("issue_count", 0)
        high_risk_count = risk_check.get("high_risk_count", 0)
        medium_risk_count = risk_check.get("medium_risk_count", 0)

        score -= missing_count * 5
        score -= not_ready_count * 4
        score -= critical_warning_count * 3
        score -= consistency_issue_count * 4
        score -= high_risk_count * 10
        score -= medium_risk_count * 5

        score = max(0, min(100, score))

        if score >= 85:
            quality_level = "GOED"
        elif score >= 70:
            quality_level = "VOLDOENDE_MET_AANDACHTSPUNTEN"
        elif score >= 50:
            quality_level = "MATIG"
        else:
            quality_level = "ONVOLDOENDE"

        return {
            "score": round(score, 1),
            "quality_level": quality_level,
            "status": "PROJECTKWALITEIT_BEREKEND"
        }

    def build_go_no_go_advice(
        self,
        quality_score,
        risk_check,
        completeness,
        status_check
    ):
        score = quality_score.get("score", 0)
        high_risk_count = risk_check.get("high_risk_count", 0)
        missing_count = completeness.get("missing_engine_count", 0)
        not_ready_count = status_check.get("not_ready_count", 0)

        if score >= 85 and high_risk_count == 0 and missing_count == 0:
            decision = "GO"
            advice = "Projectoutput is geschikt als conceptpakket voor verdere uitwerking."
        elif score >= 70 and high_risk_count == 0:
            decision = "GO_MET_AANDACHTSPUNTEN"
            advice = "Projectoutput is bruikbaar, maar aandachtspunten moeten vóór formele indiening worden gecontroleerd."
        elif score >= 50:
            decision = "NO_GO_EERST_HERSTELLEN"
            advice = "Projectoutput bevat te veel aandachtspunten. Los eerst ontbrekende data en risico’s op."
        else:
            decision = "NO_GO"
            advice = "Projectoutput is onvoldoende betrouwbaar voor vervolgstap."

        if missing_count > 0:
            advice += " Er ontbreken nog engine-resultaten."

        if not_ready_count > 0:
            advice += " Niet alle engines hebben een gereed-status."

        return {
            "decision": decision,
            "advice": advice,
            "status": "GO_NO_GO_ADVIES_GEREED"
        }

    def build_recommendation(self, quality_score, go_no_go, risk_check):
        return {
            "status": "QA_QC_ADVIES_CONCEPT",
            "summary": (
                f"Projectkwaliteitsscore: {quality_score['score']} / 100 "
                f"({quality_score['quality_level']}). Besluit: {go_no_go['decision']}."
            ),
            "next_steps": [
                "controleer alle hoge risico’s",
                "vervang placeholders door projectspecifieke gegevens",
                "controleer geotechniek met echte sondering",
                "controleer constructie met definitieve normberekening",
                "controleer parkeren, water, AERIUS en GIS met officiële bronnen",
                "werk rapporten en tekeningen op definitief niveau uit",
                "laat formele stukken controleren door bevoegd deskundige"
            ],
            "risk_count": risk_check.get("risk_count", 0)
        }

    def get_validation_result(self):
        return self.validation_result

    def run(self):
        print("Validation & QA/QC Engine actief")