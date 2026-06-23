import json
from datetime import datetime
from pathlib import Path


class ProjectConfigEngine:

    def __init__(self):
        self.config_result = {}

    def load_project_config(self, config_data=None, config_path=None):
        config_data = config_data or {}

        default_config = self.build_default_config()
        json_config = self.load_json_config(config_path)

        merged_config = self.merge_config(default_config, json_config)
        merged_config = self.merge_config(merged_config, config_data)

        validation = self.validate_config(merged_config)

        self.config_result = {
            "engine": "ProjectConfigEngine",
            "version": "1.1",
            "status": "PROJECT_CONFIG_GELADEN",
            "calculation_level": "centrale projectinvoer met JSON-ondersteuning",
            "config_path": str(config_path) if config_path else "configs/projects/plutostraat.json",
            "project_config": merged_config,
            "validation": validation,
            "input_sources": self.build_input_sources(),
            "future_input_modes": self.build_future_input_modes(),
            "warnings": self.build_warnings(validation, json_config),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Configuration Engine v1.1 ondersteunt standaardconfiguratie, "
                "optionele config_data en projectinvoer via JSON. Later kan dit worden gekoppeld "
                "aan upload, kaartselectie, formulierinvoer, spraakinvoer en projectbibliotheek."
            )
        }

        return self.config_result

    def load_json_config(self, config_path=None):
        if config_path is None:
            config_path = Path("configs/projects/plutostraat.json")
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            return {
                "_json_status": "JSON_CONFIG_NIET_GEVONDEN",
                "_json_path": str(config_path)
            }

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            data["_json_status"] = "JSON_CONFIG_GELADEN"
            data["_json_path"] = str(config_path)
            return data

        except json.JSONDecodeError as error:
            return {
                "_json_status": "JSON_CONFIG_FOUT",
                "_json_path": str(config_path),
                "_json_error": str(error)
            }

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

    def merge_config(self, base_config, override_config):
        merged = base_config.copy()

        for key, value in override_config.items():
            if key.startswith("_"):
                merged[key] = value
            elif value is not None and value != "":
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
            "is_valid": len(missing_fields) == 0,
            "json_status": project_config.get("_json_status", "ONBEKEND"),
            "json_path": project_config.get("_json_path", "")
        }

    def build_input_sources(self):
        return {
            "status": "INPUTBRONNEN_CONCEPT",
            "current_sources": [
                "default Python config",
                "optionele config_data dictionary",
                "JSON projectconfig"
            ],
            "future_sources": [
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
                    "mode": "json_project_config",
                    "description": "projectgegevens lezen uit JSON-projectbestand"
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

    def build_warnings(self, validation, json_config):
        warnings = []

        if validation.get("status") != "PROJECT_CONFIG_VALID":
            warnings.append(
                "Projectconfiguratie is onvolledig; ontbrekende velden moeten worden aangevuld."
            )

        json_status = json_config.get("_json_status")

        if json_status == "JSON_CONFIG_NIET_GEVONDEN":
            warnings.append(
                "JSON-projectconfig niet gevonden; BAOEES gebruikt fallback standaardconfiguratie."
            )

        if json_status == "JSON_CONFIG_FOUT":
            warnings.append(
                "JSON-projectconfig bevat een fout; BAOEES gebruikt fallback standaardconfiguratie."
            )

        if not warnings:
            warnings.append("Geen kritieke projectconfiguratie-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_CONFIG_ADVIES",
            "advice": (
                "Gebruik deze engine als centrale ingang voor alle projectgegevens. "
                "Projecten kunnen nu via JSON worden geladen, waardoor BAOEES meerdere "
                "projectprofielen kan ondersteunen."
            ),
            "next_steps": [
                "meerdere JSON-projectprofielen toevoegen",
                "Moskee Bunschoten als JSON-project toevoegen",
                "Bruynzeel Waterfront als JSON-project toevoegen",
                "projectkeuze vanuit startscherm voorbereiden",
                "upload-invoer koppelen aan JSON-generator",
                "projectbibliotheek koppelen"
            ]
        }

    def get_config_result(self):
        return self.config_result

    def run(self):
        print("Project Configuration / Input Engine actief")