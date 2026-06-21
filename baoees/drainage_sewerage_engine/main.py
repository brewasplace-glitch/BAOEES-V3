from datetime import datetime
import math


class DrainageSewerageEngine:

    def __init__(self):
        self.drainage_result = {}

    def design_drainage_and_sewerage(
        self,
        project_result=None,
        aaie_result=None,
        geo_result=None,
        structural_result=None,
        traffic_parking_result=None,
        cost_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        traffic_parking_result = traffic_parking_result or {}
        cost_result = cost_result or {}

        project_basis = self.build_project_basis(project_result, aaie_result)

        rainwater_result = self.calculate_rainwater_discharge(project_basis)
        storage_result = self.calculate_storage_and_infiltration(
            project_basis=project_basis,
            rainwater_result=rainwater_result,
            geo_result=geo_result
        )
        foul_water_result = self.calculate_foul_water_discharge(project_basis)
        pipe_design = self.design_pipe_system(
            project_basis=project_basis,
            rainwater_result=rainwater_result,
            foul_water_result=foul_water_result
        )
        drainage_layout = self.create_drainage_layout(
            project_basis=project_basis,
            pipe_design=pipe_design
        )
        permit_warnings = self.build_permit_warnings(
            project_basis=project_basis,
            rainwater_result=rainwater_result,
            storage_result=storage_result,
            foul_water_result=foul_water_result,
            pipe_design=pipe_design
        )

        self.drainage_result = {
            "engine": "DrainageSewerageEngine",
            "version": "1.0",
            "status": "DRAINAGE_SEWERAGE_DESIGN_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatief riolerings- en afwateringsontwerp",
            "project_basis": project_basis,
            "rainwater_discharge": rainwater_result,
            "storage_and_infiltration": storage_result,
            "foul_water_discharge": foul_water_result,
            "pipe_design": pipe_design,
            "drainage_layout": drainage_layout,
            "permit_warnings": permit_warnings,
            "recommendation": self.build_recommendation(
                storage_result=storage_result,
                pipe_design=pipe_design,
                permit_warnings=permit_warnings
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Drainage & Sewerage Engine v1.0 maakt een indicatief ontwerp. "
                "Voor definitief ontwerp zijn lokale neerslagdata, waterschapseisen, "
                "gemeentelijke aansluitvoorwaarden, peilen, maaiveldhoogtes en hydraulische berekeningen nodig."
            )
        }

        return self.drainage_result

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

        roof_area_m2 = gross_floor_area_m2 * 0.55
        paved_area_m2 = gross_floor_area_m2 * 0.45
        green_area_m2 = gross_floor_area_m2 * 0.30

        project_type = project_result.get("project_type", "Bouw")
        country = project_result.get("country", "Onbekend")

        return {
            "project_type": project_type,
            "country": country,
            "gross_floor_area_m2": round(gross_floor_area_m2, 2),
            "roof_area_m2": round(roof_area_m2, 2),
            "paved_area_m2": round(paved_area_m2, 2),
            "green_area_m2": round(green_area_m2, 2),
            "impervious_area_m2": round(roof_area_m2 + paved_area_m2, 2),
            "design_rainfall_l_s_ha": self.get_design_rainfall(country),
            "runoff_coefficient_roof": 0.95,
            "runoff_coefficient_pavement": 0.85,
            "persons_equivalent": self.estimate_persons_equivalent(project_type, gross_floor_area_m2),
            "status": "AANNAME"
        }

    def get_design_rainfall(self, country):
        country_lower = str(country).lower()

        if "suriname" in country_lower:
            return 180.0

        if "nederland" in country_lower or "netherlands" in country_lower:
            return 120.0

        return 140.0

    def estimate_persons_equivalent(self, project_type, area):
        text = str(project_type).lower()

        if "woning" in text or "bouw" in text:
            return max(4, round(area / 35))

        if "kantoor" in text:
            return max(5, round(area / 20))

        if "infra" in text:
            return 2

        return max(4, round(area / 30))

    def calculate_rainwater_discharge(self, project_basis):
        rainfall_l_s_ha = project_basis["design_rainfall_l_s_ha"]

        roof_area_ha = project_basis["roof_area_m2"] / 10000
        paved_area_ha = project_basis["paved_area_m2"] / 10000

        roof_discharge_l_s = (
            rainfall_l_s_ha
            * roof_area_ha
            * project_basis["runoff_coefficient_roof"]
        )

        paved_discharge_l_s = (
            rainfall_l_s_ha
            * paved_area_ha
            * project_basis["runoff_coefficient_pavement"]
        )

        total_discharge_l_s = roof_discharge_l_s + paved_discharge_l_s

        return {
            "method": "Q = r x A x C",
            "design_rainfall_l_s_ha": rainfall_l_s_ha,
            "roof_discharge_l_s": round(roof_discharge_l_s, 2),
            "paved_discharge_l_s": round(paved_discharge_l_s, 2),
            "total_rainwater_discharge_l_s": round(total_discharge_l_s, 2),
            "status": "HWA_AFVOER_BEREKEND_INDICATIEF"
        }

    def calculate_storage_and_infiltration(self, project_basis, rainwater_result, geo_result):
        impervious_area_m2 = project_basis["impervious_area_m2"]

        storage_mm = 60.0
        country = project_basis.get("country", "")

        if "suriname" in str(country).lower():
            storage_mm = 80.0

        required_storage_m3 = impervious_area_m2 * storage_mm / 1000

        groundwater_level = (
            geo_result.get("groundwater", {}).get("design_groundwater_level_m", -0.50)
        )

        recommended_infiltration = True
        infiltration_status = "INFILTRATIE_MOGELIJK_INDICATIEF"

        if groundwater_level > -0.70:
            recommended_infiltration = False
            infiltration_status = "INFILTRATIE_AANDACHTSPUNT_GRONDWATER_HOOG"

        infiltration_area_m2 = required_storage_m3 / 0.30

        return {
            "storage_requirement_mm": storage_mm,
            "required_storage_m3": round(required_storage_m3, 2),
            "design_groundwater_level_m": groundwater_level,
            "recommended_infiltration": recommended_infiltration,
            "indicative_infiltration_area_m2": round(infiltration_area_m2, 2),
            "storage_options": [
                "infiltratiekrat",
                "wadi",
                "waterbergende fundering",
                "vertraagde afvoer naar gemeentelijk stelsel",
                "open water of retentievoorziening"
            ],
            "status": infiltration_status
        }

    def calculate_foul_water_discharge(self, project_basis):
        persons = project_basis["persons_equivalent"]

        wastewater_l_person_day = 120.0
        peak_factor = 3.0

        daily_wastewater_l_day = persons * wastewater_l_person_day
        average_discharge_l_s = daily_wastewater_l_day / (24 * 3600)
        peak_discharge_l_s = average_discharge_l_s * peak_factor

        return {
            "persons_equivalent": persons,
            "wastewater_l_person_day": wastewater_l_person_day,
            "daily_wastewater_l_day": round(daily_wastewater_l_day, 1),
            "average_discharge_l_s": round(average_discharge_l_s, 3),
            "peak_factor": peak_factor,
            "peak_foul_water_discharge_l_s": round(peak_discharge_l_s, 3),
            "status": "DWA_AFVOER_BEREKEND_INDICATIEF"
        }

    def design_pipe_system(self, project_basis, rainwater_result, foul_water_result):
        hwa_flow_l_s = rainwater_result["total_rainwater_discharge_l_s"]
        dwa_flow_l_s = foul_water_result["peak_foul_water_discharge_l_s"]

        hwa_diameter_mm = self.select_pipe_diameter(
            flow_l_s=hwa_flow_l_s,
            pipe_type="HWA"
        )

        dwa_diameter_mm = self.select_pipe_diameter(
            flow_l_s=dwa_flow_l_s,
            pipe_type="DWA"
        )

        combined_system_allowed = False

        country = project_basis.get("country", "")
        if "suriname" in str(country).lower():
            combined_system_allowed = True

        return {
            "system_type": "gescheiden stelsel HWA/DWA",
            "combined_system_allowed_indicative": combined_system_allowed,
            "hwa_pipe_diameter_mm": hwa_diameter_mm,
            "dwa_pipe_diameter_mm": dwa_diameter_mm,
            "minimum_slope_hwa_percent": 0.5,
            "minimum_slope_dwa_percent": 1.0,
            "inspection_chamber_spacing_m": 30,
            "status": "LEIDINGDIMENSIES_BEREKEND_INDICATIEF"
        }

    def select_pipe_diameter(self, flow_l_s, pipe_type):
        if pipe_type == "DWA":
            if flow_l_s <= 1.0:
                return 110
            if flow_l_s <= 3.0:
                return 125
            if flow_l_s <= 6.0:
                return 160
            return 200

        if flow_l_s <= 2.0:
            return 110
        if flow_l_s <= 5.0:
            return 125
        if flow_l_s <= 12.0:
            return 160
        if flow_l_s <= 25.0:
            return 200
        return 250

    def create_drainage_layout(self, project_basis, pipe_design):
        roof_area = project_basis["roof_area_m2"]
        paved_area = project_basis["paved_area_m2"]

        number_of_roof_downpipes = max(2, math.ceil(roof_area / 80))
        number_of_yard_drains = max(1, math.ceil(paved_area / 150))
        number_of_inspection_chambers = max(2, math.ceil(project_basis["gross_floor_area_m2"] / 150))

        return {
            "layout_status": "CONCEPT_LAYOUT",
            "roof_downpipes": number_of_roof_downpipes,
            "yard_drains_or_gullies": number_of_yard_drains,
            "inspection_chambers": number_of_inspection_chambers,
            "main_hwa_route": "dakafvoer naar infiltratie/berging of vertraagde afvoer",
            "main_dwa_route": "sanitaire lozing naar gemeentelijk vuilwaterriool of septic/IBA indien geen aansluiting",
            "recommended_pipe_materials": [
                "PVC SN8",
                "PP inspectieputten",
                "betonnen kolken bij terreinverharding"
            ],
            "drawing_requirements": [
                "leidingtracé HWA",
                "leidingtracé DWA",
                "putten en kolken",
                "afschot en diameters",
                "aansluitpunt gemeentelijk stelsel",
                "bergings- of infiltratievoorziening"
            ],
            "pipe_design_reference": pipe_design
        }

    def build_permit_warnings(
        self,
        project_basis,
        rainwater_result,
        storage_result,
        foul_water_result,
        pipe_design
    ):
        warnings = []

        if storage_result["status"] == "INFILTRATIE_AANDACHTSPUNT_GRONDWATER_HOOG":
            warnings.append(
                "Grondwaterstand is hoog. Infiltratievoorziening moet nader worden gecontroleerd."
            )

        if rainwater_result["total_rainwater_discharge_l_s"] > 10:
            warnings.append(
                "Hemelwaterafvoer is relatief hoog. Waterberging of vertraagde afvoer opnemen."
            )

        if storage_result["required_storage_m3"] > 20:
            warnings.append(
                "Benodigde waterberging is groot. Controleer ruimtebeslag en waterschapseisen."
            )

        if pipe_design["combined_system_allowed_indicative"]:
            warnings.append(
                "Gecombineerd stelsel kan lokaal mogelijk zijn, maar gescheiden HWA/DWA blijft ontwerpvoorkeur."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke riolerings- of afwateringswaarschuwingen op basis van deze indicatieve analyse."
            )

        return warnings

    def build_recommendation(self, storage_result, pipe_design, permit_warnings):
        if storage_result["recommended_infiltration"]:
            advice = (
                "Pas bij voorkeur infiltratie of berging toe voor hemelwater, "
                "met gescheiden afvoer van vuilwater."
            )
        else:
            advice = (
                "Onderzoek vertraagde afvoer of waterberging, omdat infiltratie "
                "mogelijk wordt beperkt door hoge grondwaterstand."
            )

        return {
            "status": "RIOLERING_AFWATERING_ADVIES_CONCEPT",
            "advice": advice,
            "preferred_system": pipe_design["system_type"],
            "next_steps": [
                "maaiveldhoogtes en vloerpeilen controleren",
                "aansluitpunt gemeentelijk riool bepalen",
                "waterschapseisen of lokale waternormen controleren",
                "HWA/DWA leidingtracés op tekening zetten",
                "putten, kolken en diameters definitief bepalen",
                "berging/infiltratievoorziening dimensioneren",
                "rioleringsplan opnemen in vergunningdossier"
            ],
            "warning_count": len(permit_warnings)
        }

    def get_drainage_result(self):
        return self.drainage_result

    def run(self):
        print("Drainage & Sewerage Engine actief")