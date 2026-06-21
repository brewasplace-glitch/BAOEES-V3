from datetime import datetime


class TrafficParkingEngine:

    def __init__(self):
        self.traffic_parking_result = {}

    def analyze_traffic_and_parking(
        self,
        project_result=None,
        aaie_result=None,
        permit_result=None,
        planning_result=None,
        cost_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        permit_result = permit_result or {}
        planning_result = planning_result or {}
        cost_result = cost_result or {}

        project_basis = self.build_project_basis(project_result, aaie_result)

        parking_demand = self.calculate_parking_demand(project_basis)
        parking_supply = self.estimate_parking_supply(project_basis)
        parking_balance = self.calculate_parking_balance(
            parking_demand=parking_demand,
            parking_supply=parking_supply
        )

        traffic_generation = self.calculate_traffic_generation(project_basis)
        peak_moments = self.calculate_peak_moments(project_basis, traffic_generation)
        parking_pressure = self.calculate_parking_pressure(
            parking_supply=parking_supply,
            parking_demand=parking_demand,
            peak_moments=peak_moments
        )

        parking_regime_advice = self.generate_parking_regime_advice(
            project_basis=project_basis,
            parking_balance=parking_balance,
            parking_pressure=parking_pressure
        )

        permit_warnings = self.build_permit_warnings(
            parking_balance=parking_balance,
            parking_pressure=parking_pressure,
            traffic_generation=traffic_generation
        )

        self.traffic_parking_result = {
            "engine": "TrafficParkingEngine",
            "version": "1.0",
            "status": "TRAFFIC_PARKING_ANALYSE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve verkeers- en parkeeranalyse",
            "project_basis": project_basis,
            "parking_demand": parking_demand,
            "parking_supply": parking_supply,
            "parking_balance": parking_balance,
            "traffic_generation": traffic_generation,
            "peak_moments": peak_moments,
            "parking_pressure": parking_pressure,
            "parking_regime_advice": parking_regime_advice,
            "permit_warnings": permit_warnings,
            "recommendation": self.build_recommendation(
                parking_balance=parking_balance,
                parking_pressure=parking_pressure,
                traffic_generation=traffic_generation,
                parking_regime_advice=parking_regime_advice
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze analyse is indicatief. Voor formele vergunning, ruimtelijke onderbouwing "
                "of verkeerskundig advies zijn projectspecifieke tellingen, CROW-kencijfers, "
                "gemeentelijk parkeerbeleid en lokale verkeersgegevens noodzakelijk."
            )
        }

        return self.traffic_parking_result

    def build_project_basis(self, project_result, aaie_result):
        project_type = project_result.get("project_type", "Bouw")
        description = project_result.get("project_description", "")

        gross_floor_area_m2 = project_result.get("gross_floor_area_m2")
        if gross_floor_area_m2 is None:
            gross_floor_area_m2 = aaie_result.get("gross_floor_area_m2", 200.0)

        try:
            gross_floor_area_m2 = float(gross_floor_area_m2)
        except ValueError:
            gross_floor_area_m2 = 200.0

        if gross_floor_area_m2 <= 0:
            gross_floor_area_m2 = 200.0

        function_type = self.detect_function_type(project_type, description)

        return {
            "project_type": project_type,
            "function_type": function_type,
            "gross_floor_area_m2": gross_floor_area_m2,
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "crow_basis_status": "INDICATIEVE_KENCIJFERS",
            "parking_policy_status": "GEMEENTELIJK_BELEID_NOG_TE_CONTROLEREN",
            "status": "AANNAME"
        }

    def detect_function_type(self, project_type, description):
        text = f"{project_type} {description}".lower()

        if "moskee" in text or "gebed" in text or "relig" in text:
            return "religieuze_bijeenkomstfunctie"

        if "woning" in text or "woon" in text:
            return "wonen"

        if "kantoor" in text:
            return "kantoor"

        if "winkel" in text or "retail" in text:
            return "detailhandel"

        if "school" in text or "les" in text:
            return "onderwijs"

        if "infra" in text:
            return "infra"

        return "algemene_bouwfunctie"

    def calculate_parking_demand(self, project_basis):
        function_type = project_basis["function_type"]
        area = project_basis["gross_floor_area_m2"]

        parking_norm = self.get_parking_norm(function_type)

        demand_spaces = area / 100.0 * parking_norm["spaces_per_100m2"]

        if function_type == "religieuze_bijeenkomstfunctie":
            visitor_peak_factor = 1.35
        else:
            visitor_peak_factor = 1.00

        peak_demand_spaces = demand_spaces * visitor_peak_factor

        return {
            "method": "indicatieve CROW-achtige parkeerkencijfers",
            "function_type": function_type,
            "gross_floor_area_m2": area,
            "parking_norm_spaces_per_100m2": parking_norm["spaces_per_100m2"],
            "norm_description": parking_norm["description"],
            "base_parking_demand_spaces": round(demand_spaces, 1),
            "visitor_peak_factor": visitor_peak_factor,
            "peak_parking_demand_spaces": round(peak_demand_spaces, 1),
            "rounded_required_spaces": round(peak_demand_spaces),
            "status": "PARKEERBEHOEFTE_BEREKEND_INDICATIEF"
        }

    def get_parking_norm(self, function_type):
        norms = {
            "religieuze_bijeenkomstfunctie": {
                "spaces_per_100m2": 8.0,
                "description": "bijeenkomstfunctie indicatief; piekbelasting sterk afhankelijk van bezoekersaantal"
            },
            "wonen": {
                "spaces_per_100m2": 1.8,
                "description": "wonen indicatief omgerekend per 100 m2"
            },
            "kantoor": {
                "spaces_per_100m2": 2.2,
                "description": "kantoor indicatief"
            },
            "detailhandel": {
                "spaces_per_100m2": 4.0,
                "description": "detailhandel indicatief"
            },
            "onderwijs": {
                "spaces_per_100m2": 2.5,
                "description": "onderwijs indicatief"
            },
            "infra": {
                "spaces_per_100m2": 0.5,
                "description": "infra indicatief"
            },
            "algemene_bouwfunctie": {
                "spaces_per_100m2": 2.5,
                "description": "algemene bouwfunctie indicatief"
            }
        }

        return norms.get(function_type, norms["algemene_bouwfunctie"])

    def estimate_parking_supply(self, project_basis):
        function_type = project_basis["function_type"]

        if function_type == "religieuze_bijeenkomstfunctie":
            public_spaces = 300
            private_spaces = 0
            source = "BAOEES standaard aanname voor sport-/recreatiecluster of vergelijkbare omgeving"
        else:
            public_spaces = 40
            private_spaces = 10
            source = "BAOEES standaard aanname; fysieke inventarisatie nodig"

        total_spaces = public_spaces + private_spaces

        return {
            "private_spaces": private_spaces,
            "public_spaces": public_spaces,
            "total_available_spaces": total_spaces,
            "source": source,
            "status": "AANNAME_FYSIEKE_PARKEERINFO_NOG_TE_CONTROLEREN"
        }

    def calculate_parking_balance(self, parking_demand, parking_supply):
        required = parking_demand["rounded_required_spaces"]
        available = parking_supply["total_available_spaces"]

        balance = available - required

        if balance >= 20:
            status = "RUIM_VOLDOENDE_PARKEERCAPACITEIT_INDICATIEF"
        elif balance >= 0:
            status = "VOLDOENDE_PARKEERCAPACITEIT_INDICATIEF"
        else:
            status = "PARKEERTEKORT_INDICATIEF"

        occupancy_percent = 0.0
        if available > 0:
            occupancy_percent = required / available * 100

        return {
            "required_spaces": required,
            "available_spaces": available,
            "parking_balance_spaces": balance,
            "occupancy_percent": round(occupancy_percent, 1),
            "status": status
        }

    def calculate_traffic_generation(self, project_basis):
        function_type = project_basis["function_type"]
        area = project_basis["gross_floor_area_m2"]

        trip_rate = self.get_trip_rate(function_type)

        daily_vehicle_movements = area / 100.0 * trip_rate["daily_movements_per_100m2"]
        peak_hour_vehicle_movements = daily_vehicle_movements * trip_rate["peak_hour_fraction"]

        return {
            "method": "indicatieve verkeersgeneratie per functie",
            "function_type": function_type,
            "daily_vehicle_movements": round(daily_vehicle_movements, 1),
            "peak_hour_vehicle_movements": round(peak_hour_vehicle_movements, 1),
            "trip_rate_description": trip_rate["description"],
            "status": "VERKEERSGENERATIE_BEREKEND_INDICATIEF"
        }

    def get_trip_rate(self, function_type):
        rates = {
            "religieuze_bijeenkomstfunctie": {
                "daily_movements_per_100m2": 18.0,
                "peak_hour_fraction": 0.55,
                "description": "bijeenkomstfunctie met sterke piek rond hoofdactiviteit"
            },
            "wonen": {
                "daily_movements_per_100m2": 7.0,
                "peak_hour_fraction": 0.12,
                "description": "wonen indicatief"
            },
            "kantoor": {
                "daily_movements_per_100m2": 8.0,
                "peak_hour_fraction": 0.18,
                "description": "kantoor indicatief"
            },
            "detailhandel": {
                "daily_movements_per_100m2": 35.0,
                "peak_hour_fraction": 0.14,
                "description": "detailhandel indicatief"
            },
            "onderwijs": {
                "daily_movements_per_100m2": 12.0,
                "peak_hour_fraction": 0.30,
                "description": "onderwijs indicatief"
            },
            "infra": {
                "daily_movements_per_100m2": 5.0,
                "peak_hour_fraction": 0.10,
                "description": "infra indicatief"
            },
            "algemene_bouwfunctie": {
                "daily_movements_per_100m2": 10.0,
                "peak_hour_fraction": 0.15,
                "description": "algemene bouwfunctie indicatief"
            }
        }

        return rates.get(function_type, rates["algemene_bouwfunctie"])

    def calculate_peak_moments(self, project_basis, traffic_generation):
        function_type = project_basis["function_type"]
        peak_hour_movements = traffic_generation["peak_hour_vehicle_movements"]

        if function_type == "religieuze_bijeenkomstfunctie":
            moments = [
                {
                    "moment": "vrijdagmiddag hoofdgebed",
                    "traffic_movements": round(peak_hour_movements, 1),
                    "parking_factor": 1.00,
                    "risk": "hoog"
                },
                {
                    "moment": "avondbijeenkomst",
                    "traffic_movements": round(peak_hour_movements * 0.75, 1),
                    "parking_factor": 0.75,
                    "risk": "middel"
                },
                {
                    "moment": "weekendbijeenkomst",
                    "traffic_movements": round(peak_hour_movements * 0.90, 1),
                    "parking_factor": 0.90,
                    "risk": "middel"
                }
            ]
        else:
            moments = [
                {
                    "moment": "ochtendspits",
                    "traffic_movements": round(peak_hour_movements, 1),
                    "parking_factor": 0.80,
                    "risk": "middel"
                },
                {
                    "moment": "middagspits",
                    "traffic_movements": round(peak_hour_movements * 0.85, 1),
                    "parking_factor": 0.75,
                    "risk": "middel"
                },
                {
                    "moment": "avondperiode",
                    "traffic_movements": round(peak_hour_movements * 0.50, 1),
                    "parking_factor": 0.50,
                    "risk": "laag"
                }
            ]

        return {
            "status": "PIEKMOMENTEN_BEREKEND_INDICATIEF",
            "moments": moments
        }

    def calculate_parking_pressure(self, parking_supply, parking_demand, peak_moments):
        available = parking_supply["total_available_spaces"]
        required_peak = parking_demand["rounded_required_spaces"]

        pressure_table = []

        for moment in peak_moments["moments"]:
            moment_demand = required_peak * moment["parking_factor"]

            if available > 0:
                occupancy_percent = moment_demand / available * 100
            else:
                occupancy_percent = 999

            if occupancy_percent <= 75:
                status = "LAAG"
            elif occupancy_percent <= 90:
                status = "AANDACHTSPUNT"
            else:
                status = "HOOG"

            pressure_table.append({
                "moment": moment["moment"],
                "estimated_parking_demand": round(moment_demand, 1),
                "available_spaces": available,
                "occupancy_percent": round(occupancy_percent, 1),
                "pressure_status": status,
                "risk": moment["risk"]
            })

        highest_pressure = max(
            pressure_table,
            key=lambda item: item["occupancy_percent"]
        )

        return {
            "status": "PARKEERDRUK_BEREKEND_INDICATIEF",
            "highest_pressure_moment": highest_pressure,
            "pressure_table": pressure_table
        }

    def generate_parking_regime_advice(
        self,
        project_basis,
        parking_balance,
        parking_pressure
    ):
        highest_pressure = parking_pressure["highest_pressure_moment"]
        occupancy = highest_pressure["occupancy_percent"]
        balance = parking_balance["parking_balance_spaces"]
        function_type = project_basis["function_type"]

        if balance < 0 or occupancy > 95:
            advice_type = "sturend_parkeerregime"
            measures = [
                "parkeerduurbeperking tijdens piekmomenten onderzoeken",
                "overloopparkeren aanwijzen",
                "verkeersregelaars of parkeerbegeleiding bij piekmomenten",
                "fysieke hertelling parkeerplaatsen uitvoeren",
                "bezettingsgraad meten tijdens maatgevend moment"
            ]
        elif occupancy > 85:
            advice_type = "licht_regulerend_parkeerregime"
            measures = [
                "parkeerdruk monitoren",
                "gebruik openbare parkeerplaatsen spreiden",
                "communicatie over voorkeursparkeerlocaties",
                "fiets- en looproutes verbeteren",
                "maatgevend piekmoment opnieuw tellen"
            ]
        else:
            advice_type = "geen_zwaar_parkeerregime_nodig"
            measures = [
                "bestaande openbare parkeercapaciteit lijkt indicatief voldoende",
                "parkeerbalans onderbouwen in vergunningstukken",
                "fysieke parkeertelling toevoegen als bewijs",
                "monitoring opnemen bij piekactiviteiten"
            ]

        if function_type == "religieuze_bijeenkomstfunctie":
            measures.append(
                "specifiek vrijdagmiddagmoment opnemen in parkeeronderzoek"
            )

        return {
            "status": "PARKEERREGIME_ADVIES_GEREED",
            "advice_type": advice_type,
            "highest_pressure_moment": highest_pressure["moment"],
            "measures": measures
        }

    def build_permit_warnings(self, parking_balance, parking_pressure, traffic_generation):
        warnings = []

        if parking_balance["parking_balance_spaces"] < 0:
            warnings.append(
                "Indicatief parkeer tekort. Dit kan een vergunningrisico geven."
            )

        highest_pressure = parking_pressure["highest_pressure_moment"]

        if highest_pressure["occupancy_percent"] > 90:
            warnings.append(
                "Indicatieve parkeerdruk boven 90 procent tijdens maatgevend moment."
            )

        if traffic_generation["peak_hour_vehicle_movements"] > 100:
            warnings.append(
                "Verkeersgeneratie tijdens piekuur is hoog. Kruispunten en ontsluiting controleren."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke verkeers- of parkeerwaarschuwingen op basis van deze indicatieve analyse."
            )

        return warnings

    def build_recommendation(
        self,
        parking_balance,
        parking_pressure,
        traffic_generation,
        parking_regime_advice
    ):
        highest_pressure = parking_pressure["highest_pressure_moment"]

        return {
            "status": "VERKEER_PARKEREN_ADVIES_CONCEPT",
            "summary": (
                f"Indicatieve parkeerbalans: {parking_balance['parking_balance_spaces']} plaatsen. "
                f"Hoogste parkeerdruk: {highest_pressure['occupancy_percent']}% "
                f"tijdens {highest_pressure['moment']}."
            ),
            "parking_regime_advice_type": parking_regime_advice["advice_type"],
            "next_steps": [
                "fysieke parkeerinventarisatie uitvoeren",
                "bezettingsgraad meten op maatgevende momenten",
                "gemeentelijke parkeernormen controleren",
                "CROW-kencijfers projectspecifiek vaststellen",
                "verkeersgeneratie toetsen op ontsluiting en kruispunten",
                "parkeerregime-advies opnemen in ruimtelijke onderbouwing"
            ]
        }

    def get_traffic_parking_result(self):
        return self.traffic_parking_result

    def run(self):
        print("Traffic & Parking Engine actief")