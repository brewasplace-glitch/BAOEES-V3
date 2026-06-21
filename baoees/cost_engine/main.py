from datetime import datetime


class CostEngine:

    def __init__(self):
        self.cost_result = {}

    def estimate_costs(
        self,
        project_result=None,
        aaie_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        reporting_result=None,
        drawing_result=None,
        cad_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        reporting_result = reporting_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}

        project_basis = self.build_project_basis(project_result, aaie_result)

        construction_costs = self.calculate_construction_costs(
            project_basis=project_basis,
            geo_result=geo_result,
            structural_result=structural_result
        )

        engineering_costs = self.calculate_engineering_costs(
            project_basis=project_basis,
            permit_result=permit_result,
            reporting_result=reporting_result,
            drawing_result=drawing_result,
            cad_result=cad_result
        )

        risk_costs = self.calculate_risk_costs(
            project_basis=project_basis,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result
        )

        subtotal = (
            construction_costs["subtotal_construction_eur"]
            + engineering_costs["subtotal_engineering_eur"]
            + risk_costs["subtotal_risk_eur"]
        )

        uncertainty = self.calculate_uncertainty(project_basis, geo_result, structural_result)

        total_low = subtotal * (1 - uncertainty["low_margin_percent"] / 100)
        total_mid = subtotal
        total_high = subtotal * (1 + uncertainty["high_margin_percent"] / 100)

        self.cost_result = {
            "engine": "CostEngine",
            "version": "1.0",
            "status": "COST_ESTIMATE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve kostenraming",
            "currency": "EUR",
            "project_basis": project_basis,
            "construction_costs": construction_costs,
            "engineering_costs": engineering_costs,
            "risk_costs": risk_costs,
            "subtotal_eur": round(subtotal, 2),
            "uncertainty": uncertainty,
            "total_estimate": {
                "low_eur": round(total_low, 2),
                "mid_eur": round(total_mid, 2),
                "high_eur": round(total_high, 2)
            },
            "cost_per_m2": {
                "low_eur_m2": round(total_low / project_basis["gross_floor_area_m2"], 2),
                "mid_eur_m2": round(total_mid / project_basis["gross_floor_area_m2"], 2),
                "high_eur_m2": round(total_high / project_basis["gross_floor_area_m2"], 2)
            },
            "recommendation": self.build_recommendation(
                construction_costs=construction_costs,
                engineering_costs=engineering_costs,
                risk_costs=risk_costs,
                uncertainty=uncertainty
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze kostenraming is indicatief. Voor aanbesteding, financiering of formele besluitvorming "
                "is een projectspecifieke begroting met hoeveelhedenstaat, marktprijzen, offertes en risicoanalyse nodig."
            )
        }

        return self.cost_result

    def build_project_basis(self, project_result, aaie_result):
        gross_floor_area_m2 = project_result.get("gross_floor_area_m2")

        if gross_floor_area_m2 is None:
            gross_floor_area_m2 = aaie_result.get("gross_floor_area_m2", 200.0)

        try:
            gross_floor_area_m2 = float(gross_floor_area_m2)
        except ValueError:
            gross_floor_area_m2 = 200.0

        if gross_floor_area_m2 <= 0:
            gross_floor_area_m2 = 200.0

        project_type = project_result.get("project_type", "Bouw")
        country = project_result.get("country", "Onbekend")

        base_rate = self.get_base_rate(project_type, country)

        return {
            "project_type": project_type,
            "country": country,
            "gross_floor_area_m2": gross_floor_area_m2,
            "base_rate_eur_m2": base_rate,
            "source": "BAOEES Cost Engine default cost assumptions",
            "status": "AANNAME"
        }

    def get_base_rate(self, project_type, country):
        project_type_lower = str(project_type).lower()
        country_lower = str(country).lower()

        if "infra" in project_type_lower:
            base_rate = 650.0
        elif "civiel" in project_type_lower:
            base_rate = 900.0
        else:
            base_rate = 1200.0

        if "suriname" in country_lower:
            base_rate *= 0.85

        if "nederland" in country_lower or "netherlands" in country_lower:
            base_rate *= 1.15

        return round(base_rate, 2)

    def calculate_construction_costs(self, project_basis, geo_result, structural_result):
        area = project_basis["gross_floor_area_m2"]
        base_rate = project_basis["base_rate_eur_m2"]

        building_cost = area * base_rate

        foundation_cost = self.estimate_foundation_cost(area, geo_result)
        structural_surcharge = self.estimate_structural_surcharge(area, structural_result)
        site_cost = area * 75.0
        temporary_works = building_cost * 0.04

        subtotal = (
            building_cost
            + foundation_cost
            + structural_surcharge
            + site_cost
            + temporary_works
        )

        return {
            "building_cost_eur": round(building_cost, 2),
            "foundation_cost_eur": round(foundation_cost, 2),
            "structural_surcharge_eur": round(structural_surcharge, 2),
            "site_cost_eur": round(site_cost, 2),
            "temporary_works_eur": round(temporary_works, 2),
            "subtotal_construction_eur": round(subtotal, 2),
            "status": "CONSTRUCTIEKOSTEN_INDICATIEF"
        }

    def estimate_foundation_cost(self, area, geo_result):
        recommended = geo_result.get("recommended_foundation", {})
        foundation_type = recommended.get("selected_foundation_type", "strokenfundering")

        if foundation_type == "paalfundering":
            rate = 220.0
        elif foundation_type == "nader_geotechnisch_onderzoek":
            rate = 260.0
        else:
            rate = 110.0

        return area * rate

    def estimate_structural_surcharge(self, area, structural_result):
        warnings = structural_result.get("warnings", [])
        recommendation = structural_result.get("recommendation", {})
        status = recommendation.get("status", "")

        surcharge_rate = 0.0

        if status == "AANDACHTSPUNTEN":
            surcharge_rate += 90.0

        if len(warnings) >= 2:
            surcharge_rate += 60.0

        return area * surcharge_rate

    def calculate_engineering_costs(
        self,
        project_basis,
        permit_result,
        reporting_result,
        drawing_result,
        cad_result
    ):
        construction_reference = (
            project_basis["gross_floor_area_m2"]
            * project_basis["base_rate_eur_m2"]
        )

        design_engineering = construction_reference * 0.06
        permit_engineering = construction_reference * 0.025
        reporting_cost = 1750.0
        drawing_cost = 2500.0
        cad_cost = 2000.0
        project_management = construction_reference * 0.03

        if permit_result.get("status") not in [None, "", "PERMIT_STRATEGY_GEREED"]:
            permit_engineering *= 1.15

        if drawing_result.get("status") == "DRAWING_EXPORT_GEREED":
            drawing_cost *= 0.90

        if cad_result.get("status") == "CAD_EXPORT_GEREED":
            cad_cost *= 0.90

        subtotal = (
            design_engineering
            + permit_engineering
            + reporting_cost
            + drawing_cost
            + cad_cost
            + project_management
        )

        return {
            "design_engineering_eur": round(design_engineering, 2),
            "permit_engineering_eur": round(permit_engineering, 2),
            "reporting_cost_eur": round(reporting_cost, 2),
            "drawing_cost_eur": round(drawing_cost, 2),
            "cad_cost_eur": round(cad_cost, 2),
            "project_management_eur": round(project_management, 2),
            "subtotal_engineering_eur": round(subtotal, 2),
            "status": "ENGINEERINGKOSTEN_INDICATIEF"
        }

    def calculate_risk_costs(self, project_basis, geo_result, structural_result, permit_result):
        area = project_basis["gross_floor_area_m2"]
        base_cost = area * project_basis["base_rate_eur_m2"]

        geo_risk = self.estimate_geo_risk(base_cost, geo_result)
        structural_risk = self.estimate_structural_risk(base_cost, structural_result)
        permit_risk = self.estimate_permit_risk(base_cost, permit_result)
        market_risk = base_cost * 0.05

        subtotal = geo_risk + structural_risk + permit_risk + market_risk

        return {
            "geo_risk_eur": round(geo_risk, 2),
            "structural_risk_eur": round(structural_risk, 2),
            "permit_risk_eur": round(permit_risk, 2),
            "market_risk_eur": round(market_risk, 2),
            "subtotal_risk_eur": round(subtotal, 2),
            "status": "RISICOKOSTEN_INDICATIEF"
        }

    def estimate_geo_risk(self, base_cost, geo_result):
        warnings = geo_result.get("warnings", [])
        recommendation = geo_result.get("recommended_foundation", {})
        foundation_type = recommendation.get("selected_foundation_type", "")

        risk_percent = 0.04

        if foundation_type == "paalfundering":
            risk_percent += 0.06

        if foundation_type == "nader_geotechnisch_onderzoek":
            risk_percent += 0.10

        if len(warnings) >= 2:
            risk_percent += 0.04

        return base_cost * risk_percent

    def estimate_structural_risk(self, base_cost, structural_result):
        warnings = structural_result.get("warnings", [])
        recommendation = structural_result.get("recommendation", {})
        status = recommendation.get("status", "")

        risk_percent = 0.03

        if status == "AANDACHTSPUNTEN":
            risk_percent += 0.05

        if len(warnings) >= 2:
            risk_percent += 0.03

        return base_cost * risk_percent

    def estimate_permit_risk(self, base_cost, permit_result):
        status = permit_result.get("status", "")
        risk_percent = 0.03

        if status not in ["PERMIT_STRATEGY_GEREED", ""]:
            risk_percent += 0.03

        return base_cost * risk_percent

    def calculate_uncertainty(self, project_basis, geo_result, structural_result):
        low_margin = 10.0
        high_margin = 20.0

        if geo_result.get("recommended_foundation", {}).get("selected_foundation_type") == "paalfundering":
            high_margin += 10.0

        if structural_result.get("recommendation", {}).get("status") == "AANDACHTSPUNTEN":
            high_margin += 10.0

        if project_basis["status"] == "AANNAME":
            high_margin += 5.0

        return {
            "low_margin_percent": low_margin,
            "high_margin_percent": high_margin,
            "status": "INDICATIEVE_ONZEKERHEID"
        }

    def build_recommendation(self, construction_costs, engineering_costs, risk_costs, uncertainty):
        highest_cost_item = max(
            [
                ("construction", construction_costs["subtotal_construction_eur"]),
                ("engineering", engineering_costs["subtotal_engineering_eur"]),
                ("risk", risk_costs["subtotal_risk_eur"])
            ],
            key=lambda item: item[1]
        )

        return {
            "status": "KOSTENADVIES_CONCEPT",
            "main_cost_driver": highest_cost_item[0],
            "advice": (
                "Gebruik deze raming als eerste conceptbudget. "
                "Werk de raming later uit met hoeveelheden, eenheidsprijzen, offertes en risicoreservering."
            ),
            "next_steps": [
                "hoeveelhedenstaat genereren",
                "materiaal- en arbeidstarieven projectspecifiek maken",
                "fundering en constructie definitief dimensioneren",
                "offertes of marktprijzen toevoegen",
                "risicodossier en onzekerheidsmarge actualiseren"
            ],
            "uncertainty_band": (
                f"-{uncertainty['low_margin_percent']}% / +{uncertainty['high_margin_percent']}%"
            )
        }

    def get_cost_result(self):
        return self.cost_result

    def run(self):
        print("Cost Estimate Engine actief")