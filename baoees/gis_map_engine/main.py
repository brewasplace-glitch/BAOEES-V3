from datetime import datetime


class GISMapEngine:

    def __init__(self):
        self.gis_result = {}

    def analyze_location_and_maps(
        self,
        project_result=None,
        aaie_result=None,
        geo_result=None,
        traffic_parking_result=None,
        drainage_result=None,
        aerius_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        geo_result = geo_result or {}
        traffic_parking_result = traffic_parking_result or {}
        drainage_result = drainage_result or {}
        aerius_result = aerius_result or {}

        location_basis = self.build_location_basis(project_result, aaie_result)

        coordinates = self.estimate_coordinates_placeholder(location_basis)
        map_layers = self.build_map_layers(location_basis)
        area_contour = self.build_area_contour_placeholder(location_basis, coordinates)
        distance_checks = self.build_distance_checks(
            location_basis=location_basis,
            coordinates=coordinates,
            aerius_result=aerius_result
        )
        gis_sources = self.build_gis_sources(location_basis)
        map_outputs = self.build_map_outputs(location_basis, map_layers, area_contour)
        permit_warnings = self.build_permit_warnings(
            distance_checks=distance_checks,
            drainage_result=drainage_result,
            traffic_parking_result=traffic_parking_result
        )

        self.gis_result = {
            "engine": "GISMapEngine",
            "version": "1.0",
            "status": "GIS_MAP_ANALYSE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve GIS- en kaartanalyse",
            "location_basis": location_basis,
            "coordinates": coordinates,
            "area_contour": area_contour,
            "map_layers": map_layers,
            "distance_checks": distance_checks,
            "gis_sources": gis_sources,
            "map_outputs": map_outputs,
            "permit_warnings": permit_warnings,
            "recommendation": self.build_recommendation(
                location_basis=location_basis,
                distance_checks=distance_checks,
                permit_warnings=permit_warnings
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze GIS / Map Engine v1.0 maakt een indicatieve kaart- en locatieanalyse. "
                "Voor formele vergunningstukken zijn exacte coördinaten, kadastrale gegevens, "
                "gevalideerde GIS-lagen, actuele kaartbronnen en lokale overheidsdata nodig."
            )
        }

        return self.gis_result

    def build_location_basis(self, project_result, aaie_result):
        location = project_result.get("location", "Onbekend")
        country = project_result.get("country", "Onbekend")
        project_type = project_result.get("project_type", "Bouw")

        return {
            "location": location,
            "country": country,
            "project_type": project_type,
            "coordinate_status": "PLACEHOLDER",
            "contour_status": "PLACEHOLDER",
            "map_basis": "BAOEES indicatieve locatieanalyse",
            "required_user_input": [
                "exact adres",
                "kadastraal perceelnummer",
                "kaartuitsnede of Google Maps/Satellietfoto",
                "projectcontour of gebiedsafbakening",
                "eventuele bestaande situatietekening"
            ],
            "status": "AANNAME"
        }

    def estimate_coordinates_placeholder(self, location_basis):
        country = str(location_basis.get("country", "")).lower()
        location = str(location_basis.get("location", "")).lower()

        latitude = None
        longitude = None
        confidence = "laag"

        if "paramaribo" in location or "suriname" in country:
            latitude = 5.8520
            longitude = -55.2038
            confidence = "middel_placeholder_paramaribo"

        if "bunschoten" in location or "nederland" in country or "netherlands" in country:
            latitude = 52.2430
            longitude = 5.3780
            confidence = "middel_placeholder_bunschoten_nederland"

        return {
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_system": "WGS84",
            "confidence": confidence,
            "status": "COORDINATEN_PLACEHOLDER",
            "note": "Exacte coördinaten moeten later uit adres, kaartklik of GIS-bron worden bepaald."
        }

    def build_area_contour_placeholder(self, location_basis, coordinates):
        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

        if latitude is None or longitude is None:
            return {
                "status": "GEEN_CONTOUR_BESCHIKBAAR",
                "contour_type": "unknown",
                "geometry": None,
                "note": "Geen coördinaten beschikbaar. Upload kaartuitsnede of geef exacte locatie."
            }

        offset = 0.0005

        polygon = [
            [longitude - offset, latitude - offset],
            [longitude + offset, latitude - offset],
            [longitude + offset, latitude + offset],
            [longitude - offset, latitude + offset],
            [longitude - offset, latitude - offset]
        ]

        return {
            "status": "CONTOUR_PLACEHOLDER_GEREED",
            "contour_type": "indicatieve_projectcontour",
            "geometry_type": "Polygon",
            "coordinates": polygon,
            "note": "Contour is indicatief. Vervangen door kadastrale of handmatig getekende projectgrens."
        }

    def build_map_layers(self, location_basis):
        country = str(location_basis.get("country", "")).lower()

        layers = [
            {
                "layer_name": "projectlocatie",
                "layer_type": "point",
                "required": True,
                "status": "PLACEHOLDER"
            },
            {
                "layer_name": "projectcontour",
                "layer_type": "polygon",
                "required": True,
                "status": "PLACEHOLDER"
            },
            {
                "layer_name": "wegen en ontsluiting",
                "layer_type": "line",
                "required": True,
                "status": "TE_CONTROLEREN"
            },
            {
                "layer_name": "watergangen en afwatering",
                "layer_type": "line/polygon",
                "required": True,
                "status": "TE_CONTROLEREN"
            },
            {
                "layer_name": "percelen / kadastraal",
                "layer_type": "polygon",
                "required": True,
                "status": "TE_CONTROLEREN"
            },
            {
                "layer_name": "luchtfoto / satellietbeeld",
                "layer_type": "raster",
                "required": True,
                "status": "TE_CONTROLEREN"
            },
            {
                "layer_name": "milieu en beschermde gebieden",
                "layer_type": "polygon",
                "required": True,
                "status": "TE_CONTROLEREN"
            }
        ]

        if "nederland" in country or "netherlands" in country:
            layers.append({
                "layer_name": "Natura 2000",
                "layer_type": "polygon",
                "required": True,
                "status": "TE_CONTROLEREN_VOOR_AERIUS"
            })
            layers.append({
                "layer_name": "Omgevingsplan / Regels op de kaart",
                "layer_type": "policy",
                "required": True,
                "status": "TE_CONTROLEREN"
            })

        if "suriname" in country:
            layers.append({
                "layer_name": "GLIS / perceelsinformatie",
                "layer_type": "polygon",
                "required": True,
                "status": "TE_CONTROLEREN"
            })

        return {
            "status": "KAARTLAGENREGISTER_GEREED",
            "layers": layers
        }

    def build_distance_checks(self, location_basis, coordinates, aerius_result):
        country = str(location_basis.get("country", "")).lower()

        checks = [
            {
                "check": "afstand tot hoofdweg",
                "estimated_distance_m": None,
                "status": "TE_BEPALEN_MET_GIS"
            },
            {
                "check": "afstand tot watergang",
                "estimated_distance_m": None,
                "status": "TE_BEPALEN_MET_GIS"
            },
            {
                "check": "afstand tot perceelgrens",
                "estimated_distance_m": None,
                "status": "TE_BEPALEN_MET_KADASTER"
            },
            {
                "check": "afstand tot bebouwing omgeving",
                "estimated_distance_m": None,
                "status": "TE_BEPALEN_MET_KAART"
            }
        ]

        if "nederland" in country or "netherlands" in country:
            checks.append({
                "check": "afstand tot Natura 2000",
                "estimated_distance_m": None,
                "status": "TE_BEPALEN_VOOR_AERIUS"
            })

        return {
            "status": "AFSTANDSCONTROLES_PLACEHOLDER",
            "checks": checks,
            "aerius_status": aerius_result.get("status", "onbekend"),
            "note": "Afstanden zijn placeholders totdat echte GIS-data of kaartbronnen gekoppeld zijn."
        }

    def build_gis_sources(self, location_basis):
        country = str(location_basis.get("country", "")).lower()

        sources = [
            {
                "source_name": "Google Maps / satellietbeeld",
                "purpose": "visuele locatiecontrole en kaartuitsnede",
                "status": "TE_GEBRUIKEN"
            },
            {
                "source_name": "OpenStreetMap",
                "purpose": "wegen, omgeving en basiskaart",
                "status": "TE_GEBRUIKEN"
            }
        ]

        if "nederland" in country or "netherlands" in country:
            sources.extend([
                {
                    "source_name": "PDOK",
                    "purpose": "Nederlandse geo-basisregistraties",
                    "status": "TE_GEBRUIKEN"
                },
                {
                    "source_name": "Kadaster",
                    "purpose": "perceelgrenzen en kadastrale informatie",
                    "status": "TE_GEBRUIKEN"
                },
                {
                    "source_name": "Omgevingswet - Regels op de kaart",
                    "purpose": "omgevingsplan en juridische regels",
                    "status": "TE_GEBRUIKEN"
                },
                {
                    "source_name": "Natura 2000 / AERIUS bronnen",
                    "purpose": "stikstof- en gebiedsgevoeligheid",
                    "status": "TE_GEBRUIKEN"
                }
            ])

        if "suriname" in country:
            sources.extend([
                {
                    "source_name": "GLIS Suriname",
                    "purpose": "perceel- en eigendomsinformatie",
                    "status": "TE_CONTROLEREN"
                },
                {
                    "source_name": "lokale luchtfoto / dronefoto",
                    "purpose": "situatieanalyse en gebiedsafbakening",
                    "status": "TE_GEBRUIKEN"
                }
            ])

        return {
            "status": "GIS_BRONNENREGISTER_GEREED",
            "sources": sources
        }

    def build_map_outputs(self, location_basis, map_layers, area_contour):
        return {
            "status": "KAARTOUTPUTS_VOORBEREID",
            "outputs": [
                {
                    "name": "situatiekaart",
                    "format": "PNG/PDF placeholder",
                    "purpose": "rapportage en vergunning",
                    "status": "TE_GENEREREN"
                },
                {
                    "name": "projectcontourkaart",
                    "format": "GeoJSON/DXF placeholder",
                    "purpose": "projectafbakening",
                    "status": area_contour.get("status")
                },
                {
                    "name": "ontsluitingskaart",
                    "format": "PNG/PDF placeholder",
                    "purpose": "verkeer en parkeren",
                    "status": "TE_GENEREREN"
                },
                {
                    "name": "waterkaart",
                    "format": "PNG/PDF placeholder",
                    "purpose": "riolering en afwatering",
                    "status": "TE_GENEREREN"
                },
                {
                    "name": "milieu- en vergunningkaart",
                    "format": "PNG/PDF placeholder",
                    "purpose": "vergunning en AERIUS",
                    "status": "TE_GENEREREN"
                }
            ]
        }

    def build_permit_warnings(self, distance_checks, drainage_result, traffic_parking_result):
        warnings = []

        drainage_warnings = drainage_result.get("permit_warnings", [])
        traffic_warnings = traffic_parking_result.get("permit_warnings", [])

        if drainage_warnings:
            warnings.append("Water- en rioleringsaspecten moeten op kaart worden gecontroleerd.")

        if traffic_warnings:
            warnings.append("Ontsluiting en parkeeraanbod moeten op kaart worden onderbouwd.")

        for check in distance_checks.get("checks", []):
            if "Natura 2000" in check.get("check", ""):
                warnings.append("Afstand tot Natura 2000 moet met echte GIS-data worden bepaald.")

        if not warnings:
            warnings.append("Geen kritieke GIS-waarschuwingen op basis van deze indicatieve analyse.")

        return warnings

    def build_recommendation(self, location_basis, distance_checks, permit_warnings):
        return {
            "status": "GIS_KAARTADVIES_CONCEPT",
            "advice": (
                "Gebruik deze GIS-analyse als kaartvoorbereiding. "
                "Vervang placeholders door exacte coördinaten, perceelgrenzen en officiële kaartlagen."
            ),
            "next_steps": [
                "exacte locatie bepalen via kaartklik of adresgeocoding",
                "projectcontour intekenen of kadastraal importeren",
                "kaartlagen voor wegen, water, percelen en milieu koppelen",
                "afstand tot relevante objecten berekenen",
                "kaartoutputs genereren voor rapportage en vergunning",
                "GIS-bronnen opnemen in STEE bronregistratie"
            ],
            "warning_count": len(permit_warnings),
            "distance_check_status": distance_checks.get("status")
        }

    def get_gis_result(self):
        return self.gis_result

    def run(self):
        print("GIS / Map Engine actief")