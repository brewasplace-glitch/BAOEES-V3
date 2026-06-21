import math
from datetime import datetime


class GeoEngine:

    def __init__(self):
        self.geo_result = {}

    def analyze_geotechnics(self, project_result=None, aaie_result=None):
        project_result = project_result or {}
        aaie_result = aaie_result or {}

        soil_profile = self.get_default_soil_profile()
        groundwater_level = self.get_design_groundwater_level(aaie_result)

        shallow_result = self.calculate_strip_foundation(
            soil_profile=soil_profile,
            groundwater_level=groundwater_level
        )

        pile_result = self.calculate_pile_foundation(
            soil_profile=soil_profile,
            groundwater_level=groundwater_level
        )

        settlement_result = self.calculate_settlement_indication(
            soil_profile=soil_profile,
            shallow_result=shallow_result
        )

        recommendation = self.select_foundation_type(
            shallow_result=shallow_result,
            pile_result=pile_result,
            settlement_result=settlement_result
        )

        self.geo_result = {
            "engine": "GeoEngine",
            "version": "1.1",
            "status": "GEO_ANALYSE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve geotechnische basisberekening",
            "soil_profile": soil_profile,
            "groundwater": {
                "design_groundwater_level_m": groundwater_level,
                "status": "AANNAME",
                "fallback": "P = -0,50 m"
            },
            "strip_foundation": shallow_result,
            "pile_foundation": pile_result,
            "settlement_indication": settlement_result,
            "recommended_foundation": recommendation,
            "warnings": self.build_warnings(
                shallow_result=shallow_result,
                pile_result=pile_result,
                settlement_result=settlement_result
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Geo Engine v1.1 maakt een indicatieve geotechnische basisberekening. "
                "Voor definitief ontwerp zijn sonderingen, grondonderzoek, normtoetsing "
                "en controle door een geotechnisch deskundige noodzakelijk."
            )
        }

        return self.geo_result

    def get_default_soil_profile(self):
        return [
            {
                "layer": 1,
                "name": "Zandopvulling",
                "top_m": 0.00,
                "bottom_m": -0.50,
                "thickness_m": 0.50,
                "soil_type": "sand",
                "gamma_kN_m3": 18.0,
                "phi_deg": 30.0,
                "cohesion_kPa": 0.0,
                "undrained_shear_strength_kPa": None,
                "compressibility": "laag"
            },
            {
                "layer": 2,
                "name": "Vaste klei",
                "top_m": -0.50,
                "bottom_m": -1.00,
                "thickness_m": 0.50,
                "soil_type": "clay",
                "gamma_kN_m3": 17.0,
                "phi_deg": 20.0,
                "cohesion_kPa": 3.0,
                "undrained_shear_strength_kPa": 50.0,
                "compressibility": "middel"
            },
            {
                "layer": 3,
                "name": "Slappe klei",
                "top_m": -1.00,
                "bottom_m": -2.20,
                "thickness_m": 1.20,
                "soil_type": "soft_clay",
                "gamma_kN_m3": 15.5,
                "phi_deg": 17.0,
                "cohesion_kPa": 1.0,
                "undrained_shear_strength_kPa": 25.0,
                "compressibility": "hoog"
            },
            {
                "layer": 4,
                "name": "Diepere zandlaag",
                "top_m": -2.20,
                "bottom_m": -6.00,
                "thickness_m": 3.80,
                "soil_type": "sand",
                "gamma_kN_m3": 19.0,
                "phi_deg": 32.0,
                "cohesion_kPa": 0.0,
                "undrained_shear_strength_kPa": None,
                "compressibility": "laag"
            }
        ]

    def get_design_groundwater_level(self, aaie_result=None):
        aaie_result = aaie_result or {}

        groundwater_from_aaie = aaie_result.get("groundwater_level_m")

        if groundwater_from_aaie is not None:
            try:
                return float(groundwater_from_aaie)
            except ValueError:
                pass

        return -0.50

    def calculate_strip_foundation(self, soil_profile, groundwater_level):
        foundation_width_m = 1.50
        foundation_height_m = 0.40
        foundation_depth_m = 0.50
        design_line_load_kN_m = 90.0

        bearing_layer = self.find_layer_at_depth(
            soil_profile=soil_profile,
            depth_m=-foundation_depth_m
        )

        phi_rad = math.radians(bearing_layer["phi_deg"])
        cohesion = bearing_layer["cohesion_kPa"]
        gamma = self.correct_gamma_for_groundwater(
            gamma=bearing_layer["gamma_kN_m3"],
            depth_m=-foundation_depth_m,
            groundwater_level=groundwater_level
        )

        nq = self.calculate_nq(phi_rad)
        nc = self.calculate_nc(nq, phi_rad)
        ngamma = self.calculate_ngamma(nq, phi_rad)

        surcharge_q = gamma * foundation_depth_m

        ultimate_bearing_capacity_kPa = (
            cohesion * nc
            + surcharge_q * nq
            + 0.5 * gamma * foundation_width_m * ngamma
        )

        safety_factor = 3.0
        allowable_bearing_capacity_kPa = ultimate_bearing_capacity_kPa / safety_factor

        design_soil_pressure_kPa = design_line_load_kN_m / foundation_width_m

        unity_check = design_soil_pressure_kPa / allowable_bearing_capacity_kPa

        if unity_check <= 1.0:
            status = "VOLDOET_INDICATIEF"
        else:
            status = "VOLDOET_NIET_INDICATIEF"

        return {
            "foundation_type": "strokenfundering",
            "foundation_width_m": foundation_width_m,
            "foundation_height_m": foundation_height_m,
            "foundation_depth_m": foundation_depth_m,
            "design_line_load_kN_m": design_line_load_kN_m,
            "bearing_layer": bearing_layer["name"],
            "bearing_layer_phi_deg": bearing_layer["phi_deg"],
            "bearing_layer_cohesion_kPa": cohesion,
            "corrected_gamma_kN_m3": gamma,
            "bearing_capacity_factors": {
                "Nc": round(nc, 2),
                "Nq": round(nq, 2),
                "Ngamma": round(ngamma, 2)
            },
            "ultimate_bearing_capacity_kPa": round(ultimate_bearing_capacity_kPa, 1),
            "allowable_bearing_capacity_kPa": round(allowable_bearing_capacity_kPa, 1),
            "design_soil_pressure_kPa": round(design_soil_pressure_kPa, 1),
            "unity_check": round(unity_check, 2),
            "status": status
        }

    def calculate_pile_foundation(self, soil_profile, groundwater_level):
        pile_diameter_m = 0.30
        pile_length_m = 6.00
        number_of_piles_reference = 4
        design_column_load_kN = 250.0

        base_layer = self.find_layer_at_depth(
            soil_profile=soil_profile,
            depth_m=-pile_length_m
        )

        pile_area_m2 = math.pi * (pile_diameter_m / 2) ** 2
        pile_circumference_m = math.pi * pile_diameter_m

        if base_layer["soil_type"] == "sand":
            base_resistance_kPa = 900.0
        elif base_layer["soil_type"] == "clay":
            base_resistance_kPa = 450.0
        else:
            base_resistance_kPa = 300.0

        shaft_resistance_total_kN = 0.0

        for layer in soil_profile:
            embedded_thickness = self.get_embedded_thickness_in_layer(
                layer=layer,
                pile_length_m=pile_length_m
            )

            if embedded_thickness <= 0:
                continue

            shaft_resistance_kPa = self.estimate_shaft_resistance(layer)
            shaft_resistance_total_kN += (
                shaft_resistance_kPa
                * pile_circumference_m
                * embedded_thickness
            )

        base_resistance_kN = base_resistance_kPa * pile_area_m2

        ultimate_pile_capacity_kN = base_resistance_kN + shaft_resistance_total_kN

        safety_factor = 2.5
        allowable_pile_capacity_kN = ultimate_pile_capacity_kN / safety_factor

        total_allowable_capacity_kN = allowable_pile_capacity_kN * number_of_piles_reference

        unity_check = design_column_load_kN / total_allowable_capacity_kN

        if unity_check <= 1.0:
            status = "VOLDOET_INDICATIEF"
        else:
            status = "VOLDOET_NIET_INDICATIEF"

        return {
            "foundation_type": "paalfundering",
            "pile_diameter_m": pile_diameter_m,
            "pile_length_m": pile_length_m,
            "number_of_piles_reference": number_of_piles_reference,
            "design_column_load_kN": design_column_load_kN,
            "base_layer": base_layer["name"],
            "base_resistance_kPa": base_resistance_kPa,
            "shaft_resistance_total_kN": round(shaft_resistance_total_kN, 1),
            "base_resistance_kN": round(base_resistance_kN, 1),
            "ultimate_pile_capacity_kN": round(ultimate_pile_capacity_kN, 1),
            "allowable_pile_capacity_kN": round(allowable_pile_capacity_kN, 1),
            "total_allowable_capacity_kN": round(total_allowable_capacity_kN, 1),
            "unity_check": round(unity_check, 2),
            "status": status
        }

    def calculate_settlement_indication(self, soil_profile, shallow_result):
        design_pressure_kPa = shallow_result.get("design_soil_pressure_kPa", 60.0)

        settlement_mm = 0.0
        risk_score = 0

        for layer in soil_profile:
            if layer["bottom_m"] < -3.0:
                continue

            thickness = layer["thickness_m"]
            compressibility = layer["compressibility"]

            if compressibility == "laag":
                layer_factor = 0.05
            elif compressibility == "middel":
                layer_factor = 0.15
            else:
                layer_factor = 0.35

            layer_settlement_mm = design_pressure_kPa * thickness * layer_factor
            settlement_mm += layer_settlement_mm

            if compressibility == "hoog":
                risk_score += 2
            elif compressibility == "middel":
                risk_score += 1

        if settlement_mm <= 25:
            status = "ZETTING_ACCEPTABEL_INDICATIEF"
        elif settlement_mm <= 50:
            status = "ZETTING_AANDACHTSPUNT"
        else:
            status = "ZETTING_RISICO_HOOG"

        return {
            "method": "indicatieve samendrukkingsinschatting",
            "estimated_settlement_mm": round(settlement_mm, 1),
            "risk_score": risk_score,
            "status": status,
            "note": (
                "Zetting is indicatief bepaald. Voor definitief ontwerp is "
                "een echte zettingsberekening met sondering en samendrukkingsparameters nodig."
            )
        }

    def select_foundation_type(self, shallow_result, pile_result, settlement_result):
        shallow_ok = shallow_result.get("status") == "VOLDOET_INDICATIEF"
        pile_ok = pile_result.get("status") == "VOLDOET_INDICATIEF"
        settlement_ok = settlement_result.get("status") == "ZETTING_ACCEPTABEL_INDICATIEF"

        if shallow_ok and settlement_ok:
            selected = "strokenfundering"
            reason = (
                "Strokenfundering voldoet indicatief op draagkracht en zetting. "
                "Dit is meestal de eenvoudigste en goedkoopste oplossing."
            )
        elif pile_ok:
            selected = "paalfundering"
            reason = (
                "Paalfundering wordt aanbevolen omdat draagkracht of zetting "
                "bij strokenfundering een aandachtspunt vormt."
            )
        else:
            selected = "nader_geotechnisch_onderzoek"
            reason = (
                "Geen funderingstype voldoet indicatief met de huidige aannames. "
                "Aanvullend grondonderzoek en herberekening zijn nodig."
            )

        return {
            "selected_foundation_type": selected,
            "reason": reason,
            "status": "AANBEVELING_CONCEPT"
        }

    def build_warnings(self, shallow_result, pile_result, settlement_result):
        warnings = []

        if shallow_result.get("unity_check", 0) > 1.0:
            warnings.append(
                "Strokenfundering voldoet indicatief niet op draagkracht."
            )

        if settlement_result.get("status") != "ZETTING_ACCEPTABEL_INDICATIEF":
            warnings.append(
                "Zetting is een aandachtspunt. Controleer met echte sonderingen en samendrukkingsparameters."
            )

        if pile_result.get("unity_check", 0) > 1.0:
            warnings.append(
                "Referentie-paalfundering voldoet indicatief niet. Controleer paallengte, paaldiameter en paaltype."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke waarschuwingen op basis van deze indicatieve geotechnische berekening."
            )

        return warnings

    def find_layer_at_depth(self, soil_profile, depth_m):
        for layer in soil_profile:
            if layer["top_m"] >= depth_m >= layer["bottom_m"]:
                return layer

        return soil_profile[-1]

    def correct_gamma_for_groundwater(self, gamma, depth_m, groundwater_level):
        if depth_m <= groundwater_level:
            return max(gamma - 10.0, 8.0)

        return gamma

    def calculate_nq(self, phi_rad):
        if phi_rad <= 0:
            return 1.0

        return math.exp(math.pi * math.tan(phi_rad)) * (
            math.tan(math.radians(45) + phi_rad / 2) ** 2
        )

    def calculate_nc(self, nq, phi_rad):
        if phi_rad <= 0:
            return 5.14

        return (nq - 1) / math.tan(phi_rad)

    def calculate_ngamma(self, nq, phi_rad):
        if phi_rad <= 0:
            return 0.0

        return 2 * (nq + 1) * math.tan(phi_rad)

    def get_embedded_thickness_in_layer(self, layer, pile_length_m):
        pile_tip_depth = -pile_length_m

        top = layer["top_m"]
        bottom = layer["bottom_m"]

        embedded_top = min(top, 0)
        embedded_bottom = max(bottom, pile_tip_depth)

        if embedded_bottom >= embedded_top:
            return 0.0

        return abs(embedded_top - embedded_bottom)

    def estimate_shaft_resistance(self, layer):
        soil_type = layer["soil_type"]

        if soil_type == "sand":
            return 25.0

        if soil_type == "clay":
            su = layer.get("undrained_shear_strength_kPa") or 40.0
            return 0.45 * su

        if soil_type == "soft_clay":
            su = layer.get("undrained_shear_strength_kPa") or 25.0
            return 0.35 * su

        return 10.0

    def get_geo_result(self):
        return self.geo_result

    def run(self):
        print("Geo Engine actief")