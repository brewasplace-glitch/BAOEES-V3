from datetime import datetime


class ProjectConfigEngine:

    def __init__(self):
        self.config_result = {}

    def load_project_config(self, config_data=None):
        config_data = config_data or {}

        default_config = self.build_default_config()
        merged_config = self.merge_config(default_config, config_data)
        validation = self.validate_config(merged_config)

        self.config_result = {
            "engine": "ProjectConfigEngine",
            "version": "1.0",
            "status": "PROJECT_CONFIG_GELADEN",
            "calculation_level": "centrale projectinvoer",
            "project_config": merged_config,
            "validation": validation,
            "input_sources": self.build_input_sources(),
            "future_input_modes": self.build_future_input_modes(),
            "warnings": self.build_warnings(validation),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Configuration Engine v1.0 gebruikt nu nog standaardconfiguratie "
                "en optionele handmatige config_data. Later kan dit worden gekoppeld aan JSON, "
                "upload, kaartselectie, formulierinvoer, spraakinvoer en projectbibliotheek."
            )
        }

        return self.config_result

    def build_default_config(self):
        return {
            "project_name": "Plutostraat met BAOEES V3",
            "project_description": (
                "Vrijstaande woning met fundering, constructie, geotechniek "
                "en SketchUp-integratie."
            ),
            "location": "Plutostraat, Paramaribo",
            "country": "Suriname",
            "project_type": "Bouw",
            "client": "Brewster Engineering",
            "project_phase": "concept projectanalyse",
            "input_mode": "default_config",
            "autonomous_project_mode": "volledig autonoom met QA/QC-controle",
            "requested_outputs": [
                "projectanalyse",
                "ontwerpvarianten",
                "geotechniek",
                "constructie",
                "vergunningstrategie",
                "rapportage",
                "tekeningen",
                "CAD/DXF",
                "kostenraming",
                "planning",
                "verkeer en parkeren",
                "riolering en afwatering",
                "AERIUS/stikstof",
                "GIS/kaartanalyse",
                "hoeveelhedenstaat",
                "bestek",
                "aanbesteding",
                "contract",
                "uitvoeringsplan",
                "bouwplaatsmonitoring",
                "as-built/oplevering",
                "asset management",
                "duurzaamheid",
                "normenregister",
                "autonomous learning",
                "runtime orchestration",
                "project ZIP"
            ],
            "data_completeness_mode": (
                "Bekende gegevens + Open Data + AI-aannames"
            ),
            "geo_input_mode": (
                "grondwaterstand en geo-informatie automatisch genereren"
            ),
            "foundation_mode": (
                "funderingstypen automatisch onderzoeken en vergelijken"
            ),
            "default_groundwater_level_m": -0.50
        }

    def merge_config(self, default_config, config_data):
        merged = default_config.copy()

        for key, value in config_data.items():
            if value is not None and value != "":
                merged[key] = value

        return merged

    def validate_config(self, project_config):
        required_fields = [
            "project_name",
            "project_description",
            "location",
            "country",
            "project_type"
        ]

        missing_fields = []

        for field in required_fields:
            value = project_config.get(field)
            if value is None or value == "":
                missing_fields.append(field)

        if missing_fields:
            status = "PROJECT_CONFIG_ONVOLLEDIG"
        else:
            status = "PROJECT_CONFIG_VALID"

        return {
            "status": status,
            "required_fields": required_fields,
            "missing_fields": missing_fields,
            "is_valid": len(missing_fields) == 0
        }

    def build_input_sources(self):
        return {
            "status": "INPUTBRONNEN_CONCEPT",
            "current_sources": [
                "default Python config",
                "optionele config_data dictionary"
            ],
            "future_sources": [
                "JSON projectbestand",
                "Excel projectinvoer",
                "PDF projectomschrijving",
                "DWG/DXF/SKP upload",
                "Google Maps locatie",
                "satellietfoto / kaartuitsnede",
                "spraakinvoer",
                "startscherm formulier",
                "projectbibliotheek"
            ]
        }

    def build_future_input_modes(self):
        return {
            "status": "TOEKOMSTIGE_INVOERMODI_CONCEPT",
            "modes": [
                {
                    "mode": "manual_form",
                    "description": "projectgegevens invoeren via startscherm"
                },
                {
                    "mode": "file_upload",
                    "description": "projectomschrijving en tekeningen uploaden"
                },
                {
                    "mode": "speech_input",
                    "description": "projectopdracht via spraak invoeren"
                },
                {
                    "mode": "map_selection",
                    "description": "locatie bepalen via kaartvlak of Google Maps uitsnede"
                },
                {
                    "mode": "autonomous_project_mode",
                    "description": "BAOEES vult ontbrekende gegevens automatisch aan"
                }
            ]
        }

    def build_warnings(self, validation):
        warnings = []

        if validation.get("status") != "PROJECT_CONFIG_VALID":
            warnings.append(
                "Projectconfiguratie is onvolledig; ontbrekende velden moeten worden aangevuld."
            )

        if not warnings:
            warnings.append("Geen kritieke projectconfiguratie-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_CONFIG_ADVIES",
            "advice": (
                "Gebruik deze engine als centrale ingang voor alle projectgegevens. "
                "De volgende stap is om core/main.py niet meer hardcoded projectdata te laten gebruiken, "
                "maar de project_config uit deze engine."
            ),
            "next_steps": [
                "ProjectConfigEngine koppelen aan BAOEES Core",
                "hardcoded projectnaam uit core/main.py vervangen",
                "JSON-configbestand toevoegen",
                "startscherm-invoer voorbereiden",
                "meerdere projectprofielen mogelijk maken",
                "projectbibliotheek koppelen"
            ]
        }

    def get_config_result(self):
        return self.config_result

    def run(self):
        print("Project Configuration / Input Engine actief")