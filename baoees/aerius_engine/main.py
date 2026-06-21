from datetime import datetime

class AERIUSEngine:

    def __init__(self):
        self.aerius_result = {}

    def prepare_aerius_assessment(
        self,
        project_result=None,
        aaie_result=None,
        traffic_parking_result=None,
        planning_result=None,
        cost_result=None,
        drainage_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        traffic_parking_result = traffic_parking_result or {}
        planning_result = planning_result or {}
        cost_result = cost_result or {}
        drainage_result = drainage_result or {}

        project_basis = self.build_project_basis(
            project_result=project_result,
            aaie_result=aaie_result,
            planning_result=planning_result,
            cost_result=cost_result
        )

        construction_phase = self.calculate_construction_phase_emissions(
            project_basis=project_basis
        )

        use_phase = self.calculate_use_phase_emissions(
            project_basis=project_basis,
            traffic_parking_result=traffic_parking_result
        )

        transport_emissions = self.calculate_transport_emissions(
            project_basis=project_basis,
            traffic_parking_result=traffic_parking_result
        )

        aerius_input_data = self.build_aerius_input_data(
            project_basis=project_basis,
            construction_phase=construction_phase,
            use_phase=use_phase,
            transport_emissions=transport_emissions
        )

        sensitivity = self.assess_natura2000_sensitivity(
            project_basis=project_basis
        )

        permit_warnings = self.build_permit_warnings(
            construction_phase=construction_phase,
            use_phase=use_phase,
            transport_emissions=transport_emissions,
            sensitivity=sensitivity
        )

        self.aerius_result = {
            "engine": "AERIUSEngine",
            "version": "1.0",
            "status": "AERIUS_VOORBEREIDING_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve stikstof- en AERIUS-voorbereiding",
            "project_basis": project_basis,
            "construction_phase_emissions": construction_phase,
            "use_phase_emissions": use_phase,
            "transport_emissions": transport_emissions,
            "natura2000_sensitivity": sensitivity,
            "aerius_input_data": aerius_input_data,
            "permit_warnings": permit_warnings,
            "recommendation": self.build_recommendation(
                construction_phase=construction_phase,
                use_phase=use_phase,
                transport_emissions=transport_emissions,
                sensitivity=sensitivity,
                permit_warnings=permit_warnings
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze AERIUS Engine v1.0 maakt alleen een indicatieve voorbereiding. "
                "Voor formele indiening moet altijd de actuele AERIUS Calculator worden gebruikt "
                "met projectspecifieke invoer, actuele emissiefactoren, locatiecoördinaten, "
                "bouwmaterieel, verkeersroutes en Natura 2000-gegevens."
            )
        }

        return self.aerius_result

    def build_project_basis(self, project_result, aaie_result, planning_result, cost_result):
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

        total_duration = planning_result.get("total_duration_working_days", 120)

        try:
            total_duration = int(total_duration)
        except ValueError:
            total_duration = 120

        construction_duration_days = max(30, round(total_duration * 0.35))

        return {
            "project_type": project_type,
            "country": country,
            "location": project_result.get("location", "Onbekend"),
            "gross_floor_area_m2": gross_floor_area_m2,
            "construction_duration_days": construction_duration_days,
            "construction_duration_months": round(construction_duration_days / 21, 1),
            "construction_scale": self.determine_construction_scale(gross_floor_area_m2),
            "status": "AANNAME"
        }

    def determine_construction_scale(self, gross_floor_area_m2):
        if gross_floor_area_m2 <= 100:
            return "klein"

        if gross_floor_area_m2 <= 500:
            return "middel"

        return "groot"

    def calculate_construction_phase_emissions(self, project_basis):
        area = project_basis["gross_floor_area_m2"]
        scale = project_basis["construction_scale"]
        duration_months = project_basis["construction_duration_months"]

        equipment = self.estimate_construction_equipment(scale)

        total_diesel_liters = 0.0
        total_nox_kg = 0.0
        total_nh3_kg = 0.0
        equipment_rows = []

        for item in equipment:
            hours = item["hours_per_month"] * duration_months
            diesel_liters = hours * item["diesel_l_per_hour"]
            nox_kg = diesel_liters * item["nox_kg_per_liter"]
            nh3_kg = diesel_liters * item["nh3_kg_per_liter"]

            total_diesel_liters += diesel_liters
            total_nox_kg += nox_kg
            total_nh3_kg += nh3_kg

            equipment_rows.append({
                "equipment": item["equipment"],
                "stage_class": item["stage_class"],
                "hours": round(hours, 1),
                "diesel_liters": round(diesel_liters, 1),
                "nox_kg": round(nox_kg, 3),
                "nh3_kg": round(nh3_kg, 3)
            })

        return {
            "method": "indicatieve emissieberekening bouwmaterieel",
            "gross_floor_area_m2": area,
            "construction_scale": scale,
            "equipment": equipment_rows,
            "total_diesel_liters": round(total_diesel_liters, 1),
            "total_nox_kg": round(total_nox_kg, 3),
            "total_nh3_kg": round(total_nh3_kg, 3),
            "status": "BOUWFASE_EMISSIES_BEREKEND_INDICATIEF"
        }

    def estimate_construction_equipment(self, scale):
        if scale == "klein":
            return [
                {
                    "equipment": "minigraver",
                    "stage_class": "Stage V indicatief",
                    "hours_per_month": 24,
                    "diesel_l_per_hour": 4.0,
                    "nox_kg_per_liter": 0.025,
                    "nh3_kg_per_liter": 0.0001
                },
                {
                    "equipment": "verreiker / kleine loader",
                    "stage_class": "Stage V indicatief",
                    "hours_per_month": 16,
                    "diesel_l_per_hour": 5.0,
                    "nox_kg_per_liter": 0.025,
                    "nh3_kg_per_liter": 0.0001
                }
            ]

        if scale == "groot":
            return [
                {
                    "equipment": "rupsgraafmachine",
                    "stage_class": "Stage V indicatief",
                    "hours_per_month": 90,
                    "diesel_l_per_hour": 12.0,
                    "nox_kg_per_liter": 0.025,
                    "nh3_kg_per_liter": 0.0001
                },
                {
                    "equipment": "mobiele kraan",
                    "stage_class": "Stage V indicatief",
                    "hours_per_month": 60,
                    "diesel_l_per_hour": 14.0,
                    "nox_kg_per_liter": 0.025,
                    "nh3_kg_per_liter": 0.0001
                },
                {
                    "equipment": "loader / verreiker",
                    "stage_class": "Stage V indicatief",
                    "hours_per_month": 60,
                    "diesel_l_per_hour": 8.0,
                    "nox_kg_per_liter": 0.025,
                    "nh3_kg_per_liter": 0.0001
                }
            ]

        return [
            {
                "equipment": "graafmachine",
                "stage_class": "Stage V indicatief",
                "hours_per_month": 50,
                "diesel_l_per_hour": 8.0,
                "nox_kg_per_liter": 0.025,
                "nh3_kg_per_liter": 0.0001
            },
            {
                "equipment": "mobiele kraan / verreiker",
                "stage_class": "Stage V indicatief",
                "hours_per_month": 35,
                "diesel_l_per_hour": 9.0,
                "nox_kg_per_liter": 0.025,
                "nh3_kg_per_liter": 0.0001
            }
        ]

    def calculate_use_phase_emissions(self, project_basis, traffic_parking_result):
        traffic_generation = traffic_parking_result.get("traffic_generation", {})
        daily_movements = traffic_generation.get("daily_vehicle_movements", 20.0)

        try:
            daily_movements = float(daily_movements)
        except ValueError:
            daily_movements = 20.0

        average_trip_length_km = 5.0
        operating_days_per_year = 260

        annual_vehicle_km = daily_movements * average_trip_length_km * operating_days_per_year

        nox_kg_per_vehicle_km = 0.00035
        nh3_kg_per_vehicle_km = 0.00002

        annual_nox_kg = annual_vehicle_km * nox_kg_per_vehicle_km
        annual_nh3_kg = annual_vehicle_km * nh3_kg_per_vehicle_km

        building_heating_nox_kg = self.estimate_building_heating_nox(project_basis)

        total_annual_nox_kg = annual_nox_kg + building_heating_nox_kg

        return {
            "method": "indicatieve gebruiksfase-emissies verkeer en gebouw",
            "daily_vehicle_movements": round(daily_movements, 1),
            "average_trip_length_km": average_trip_length_km,
            "annual_vehicle_km": round(annual_vehicle_km, 1),
            "traffic_nox_kg_year": round(annual_nox_kg, 3),
            "traffic_nh3_kg_year": round(annual_nh3_kg, 3),
            "building_heating_nox_kg_year": round(building_heating_nox_kg, 3),
            "total_nox_kg_year": round(total_annual_nox_kg, 3),
            "total_nh3_kg_year": round(annual_nh3_kg, 3),
            "status": "GEBRUIKSFASE_EMISSIES_BEREKEND_INDICATIEF"
        }

    def estimate_building_heating_nox(self, project_basis):
        country = str(project_basis.get("country", "")).lower()
        area = project_basis.get("gross_floor_area_m2", 200.0)

        if "suriname" in country:
            return 0.0

        return area * 0.01

    def calculate_transport_emissions(self, project_basis, traffic_parking_result):
        scale = project_basis["construction_scale"]

        if scale == "klein":
            heavy_truck_movements = 20
            light_vehicle_movements = 80
        elif scale == "groot":
            heavy_truck_movements = 180
            light_vehicle_movements = 400
        else:
            heavy_truck_movements = 70
            light_vehicle_movements = 180

        average_route_length_km = 8.0

        truck_nox_kg_per_km = 0.0035
        light_vehicle_nox_kg_per_km = 0.0005

        truck_nh3_kg_per_km = 0.00004
        light_vehicle_nh3_kg_per_km = 0.00002

        truck_km = heavy_truck_movements * average_route_length_km
        light_vehicle_km = light_vehicle_movements * average_route_length_km

        nox_kg = (
            truck_km * truck_nox_kg_per_km
            + light_vehicle_km * light_vehicle_nox_kg_per_km
        )

        nh3_kg = (
            truck_km * truck_nh3_kg_per_km
            + light_vehicle_km * light_vehicle_nh3_kg_per_km
        )

        return {
            "method": "indicatieve bouwtransport-emissies",
            "heavy_truck_movements": heavy_truck_movements,
            "light_vehicle_movements": light_vehicle_movements,
            "average_route_length_km": average_route_length_km,
            "heavy_truck_km": round(truck_km, 1),
            "light_vehicle_km": round(light_vehicle_km, 1),
            "total_nox_kg": round(nox_kg, 3),
            "total_nh3_kg": round(nh3_kg, 3),
            "status": "BOUWTRANSPORT_EMISSIES_BEREKEND_INDICATIEF"
        }

    def assess_natura2000_sensitivity(self, project_basis):
        country = str(project_basis.get("country", "")).lower()

        if "nederland" in country or "netherlands" in country:
            sensitivity = "te_controleren"
            required = True
            note = "Controleer afstand tot Natura 2000-gebieden en actuele AERIUS Calculator."
        else:
            sensitivity = "niet_nederlandse_aerius_context"
            required = False
            note = "AERIUS is primair Nederlandse stikstofsystematiek. Lokale milieuregels controleren."

        return {
            "status": "NATURA2000_GEVOELIGHEID_PLACEHOLDER",
            "aerius_required_indicative": required,
            "sensitivity": sensitivity,
            "distance_to_natura2000_km": None,
            "note": note
        }

    def build_aerius_input_data(
        self,
        project_basis,
        construction_phase,
        use_phase,
        transport_emissions
    ):
        return {
            "status": "AERIUS_INVOERDATA_CONCEPT",
            "project_location": project_basis.get("location"),
            "source_types": [
                {
                    "source_name": "bouwmaterieel",
                    "source_type": "mobiele werktuigen",
                    "nox_kg": construction_phase["total_nox_kg"],
                    "nh3_kg": construction_phase["total_nh3_kg"],
                    "input_status": "AANNAME"
                },
                {
                    "source_name": "bouwtransport",
                    "source_type": "wegverkeer bouwfase",
                    "nox_kg": transport_emissions["total_nox_kg"],
                    "nh3_kg": transport_emissions["total_nh3_kg"],
                    "input_status": "AANNAME"
                },
                {
                    "source_name": "gebruiksfase verkeer",
                    "source_type": "wegverkeer gebruiksfase",
                    "nox_kg_per_year": use_phase["traffic_nox_kg_year"],
                    "nh3_kg_per_year": use_phase["traffic_nh3_kg_year"],
                    "input_status": "AANNAME"
                },
                {
                    "source_name": "gebouwinstallaties",
                    "source_type": "gebouw emissie",
                    "nox_kg_per_year": use_phase["building_heating_nox_kg_year"],
                    "input_status": "AANNAME"
                }
            ],
            "required_manual_inputs": [
                "exacte projectcoördinaten",
                "bouwjaar en emissieklasse materieel",
                "draaiuren per machine",
                "transport- en verkeersroutes",
                "percentage licht/middel/zwaar verkeer",
                "Natura 2000-afstand",
                "actuele AERIUS Calculator-versie",
                "rekenjaar bouwfase en gebruiksfase"
            ]
        }

    def build_permit_warnings(
        self,
        construction_phase,
        use_phase,
        transport_emissions,
        sensitivity
    ):
        warnings = []

        total_construction_nox = (
            construction_phase["total_nox_kg"]
            + transport_emissions["total_nox_kg"]
        )

        total_use_nox = use_phase["total_nox_kg_year"]

        if sensitivity["aerius_required_indicative"]:
            warnings.append(
                "AERIUS-berekening is indicatief nodig omdat het project in Nederlandse context valt."
            )

        if total_construction_nox > 25:
            warnings.append(
                "Bouwfase NOx-emissie is indicatief verhoogd. Controleer elektrisch materieel of schonere emissieklasse."
            )

        if total_use_nox > 10:
            warnings.append(
                "Gebruiksfase NOx-emissie is indicatief verhoogd. Controleer verkeersgeneratie en gebouwinstallaties."
            )

        if construction_phase["total_nh3_kg"] > 1:
            warnings.append(
                "NH3-emissie bouwfase controleren in formele AERIUS-invoer."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke stikstofwaarschuwingen op basis van deze indicatieve voorbereiding."
            )

        return warnings

    def build_recommendation(
        self,
        construction_phase,
        use_phase,
        transport_emissions,
        sensitivity,
        permit_warnings
    ):
        total_construction_nox = (
            construction_phase["total_nox_kg"]
            + transport_emissions["total_nox_kg"]
        )

        total_use_nox = use_phase["total_nox_kg_year"]

        if sensitivity["aerius_required_indicative"]:
            advice = (
                "Maak een formele AERIUS-berekening met actuele projectlocatie, "
                "bouwmaterieel, verkeersroutes en rekenjaar."
            )
        else:
            advice = (
                "Controleer lokale milieuregels. AERIUS is waarschijnlijk niet het primaire systeem "
                "buiten Nederland, maar emissie-inventarisatie blijft nuttig."
            )

        if total_construction_nox > 25:
            advice += " Onderzoek emissiereductie in de bouwfase."

        if total_use_nox > 10:
            advice += " Onderzoek beperking van verkeers- en gebouwemissies in de gebruiksfase."

        return {
            "status": "STIKSTOFADVIES_CONCEPT",
            "advice": advice,
            "construction_nox_total_kg": round(total_construction_nox, 3),
            "use_phase_nox_kg_year": round(total_use_nox, 3),
            "warning_count": len(permit_warnings),
            "next_steps": [
                "exacte projectlocatie vastleggen",
                "Natura 2000-afstand bepalen",
                "bouwmaterieelstaat opstellen",
                "transportbewegingen en routes vastleggen",
                "gebruiksfase verkeersgeneratie controleren",
                "actuele AERIUS Calculator gebruiken",
                "uitkomst opnemen in vergunningdossier"
            ]
        }

    def get_aerius_result(self):
        return self.aerius_result

    def run(self):
        print("AERIUS / Stikstof Engine actief")
