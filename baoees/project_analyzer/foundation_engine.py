from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FoundationEngine:
    ENGINE_NAME = "Project Phoenix Foundation Engine"
    ENGINE_VERSION = "v7.3"

    def __init__(self) -> None:
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.context_path = self.out / "project_context_v7_1.json"
        self.geo_path = self.out / "project_geotechniek_v7_2.json"

        self.foundation_json_path = self.out / "project_foundation_design_v7_3.json"
        self.foundation_summary_path = self.out / "project_foundation_summary_v7_3.md"
        self.foundation_log_path = self.out / "project_foundation_log_v7_3.json"
        self.foundation_dashboard_path = self.out / "project_foundation_dashboard_v7_3.html"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        context = self.read_json(self.context_path)
        geotechniek = self.read_json(self.geo_path)

        foundation = self.build_foundation_design(context, geotechniek)

        self.write_json(self.foundation_json_path, foundation)
        self.write_text(self.foundation_summary_path, self.build_markdown_summary(foundation))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.out),
            "project_context_path": str(self.context_path),
            "geotechniek_path": str(self.geo_path),
            "foundation_json_path": str(self.foundation_json_path),
            "foundation_summary_path": str(self.foundation_summary_path),
            "foundation_log_path": str(self.foundation_log_path),
            "foundation_dashboard_path": str(self.foundation_dashboard_path),
            "source_status": {
                "project_context": "GELEZEN" if context else "ONTBREEKT",
                "geotechniek": "GELEZEN" if geotechniek else "ONTBREEKT",
            },
            "project_name": foundation["project"]["project_name"],
            "foundation_type": foundation["selected_concept"]["type"],
            "concept_status": foundation["selected_concept"]["status"],
            "variant_count": len(foundation["variants"]),
            "risk_count": len(foundation["risks"]),
            "next_steps": [
                "Controleer project_foundation_dashboard_v7_3.html.",
                "Controleer project_foundation_design_v7_3.json.",
                "Gebruik foundation-output als basis voor v7.4 Constructie Engine.",
                "Vul later echte belastingen, stramien, muren/kolommen en sondering in voor definitieve berekening.",
            ],
        }

        self.write_json(self.foundation_log_path, result)
        self.write_text(self.foundation_dashboard_path, self.build_dashboard(result, foundation))

        return result

    def build_foundation_design(
        self,
        context: Dict[str, Any],
        geotechniek: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = self.resolve_project(context, geotechniek)
        soil_profile = geotechniek.get("soil_profile", {}) if isinstance(geotechniek, dict) else {}
        groundwater = geotechniek.get("groundwater", {}) if isinstance(geotechniek, dict) else {}
        geo_advice = geotechniek.get("foundation_advice", {}) if isinstance(geotechniek, dict) else {}

        has_soft_clay = self.has_soft_clay(soil_profile)
        location_unknown = project.get("location") == "Locatie nog te bepalen"

        selected = self.build_selected_concept(has_soft_clay, location_unknown)
        variants = self.build_variants(has_soft_clay)
        design_rules = self.build_design_rules()
        checks = self.build_required_checks(has_soft_clay)
        risks = self.build_risks(project, has_soft_clay, groundwater)
        assumptions = self.build_assumptions(selected, groundwater, soil_profile)

        return {
            "status": "VOORLOPIG_CONCEPT",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "selected_concept": selected,
            "variants": variants,
            "design_rules": design_rules,
            "required_checks": checks,
            "geotechnical_basis": {
                "soil_profile_status": soil_profile.get("status", "ONBEKEND"),
                "soil_profile_source": soil_profile.get("source", "niet beschikbaar"),
                "soil_profile_reliability": soil_profile.get("reliability", "onbekend"),
                "groundwater_level": groundwater.get("default_level", "P = -0,50 m"),
                "geo_foundation_advice": geo_advice.get("primary_advice", "niet beschikbaar"),
            },
            "preliminary_dimensions": self.build_preliminary_dimensions(selected),
            "outputs_for_next_engine": {
                "next_engine": "Structural Engine v7.4",
                "foundation_type": selected["type"],
                "foundation_level": selected["foundation_level"],
                "strip_width_cm": selected["strip_width_cm"],
                "strip_height_cm": selected["strip_height_cm"],
                "beam_width_cm": selected["beam_width_cm"],
                "beam_height_cm": selected["beam_height_cm"],
                "needs_load_model": True,
            },
            "risks": risks,
            "assumptions": assumptions,
            "not_for_execution_note": "Dit is een automatisch concept. Definitief ontwerp vereist projectspecifieke berekening, bodemonderzoek en constructieve toetsing.",
        }

    def resolve_project(self, context: Dict[str, Any], geotechniek: Dict[str, Any]) -> Dict[str, Any]:
        project = {}
        if isinstance(context.get("project"), dict):
            project.update(context["project"])
        if isinstance(geotechniek.get("project"), dict):
            for key, value in geotechniek["project"].items():
                if value and not project.get(key):
                    project[key] = value

        defaults = {
            "project_name": "Nieuw Project Phoenix project",
            "location": "Locatie nog te bepalen",
            "project_type": "algemeen bouwkundig / civiel project",
            "description": "Voorlopig funderingsconcept op basis van projectcontext en geotechniek.",
        }

        for key, value in defaults.items():
            if not str(project.get(key, "")).strip():
                project[key] = value

        return project

    def has_soft_clay(self, soil_profile: Dict[str, Any]) -> bool:
        for layer in soil_profile.get("layers", []):
            text = " ".join(
                [
                    str(layer.get("soil_type", "")),
                    str(layer.get("classification", "")),
                ]
            ).lower()
            if "slappe klei" in text or "zettingsgevoelig" in text:
                return True
        return False

    def build_selected_concept(self, has_soft_clay: bool, location_unknown: bool) -> Dict[str, Any]:
        concept = {
            "type": "strokenfundering_met_funderingsbalk",
            "status": "VOORLOPIG",
            "foundation_level": "P = -0,50 m voorlopig",
            "strip_width_cm": 150,
            "strip_height_cm": 40,
            "beam_width_cm": 50,
            "beam_height_cm": 60,
            "beam_position": "in hart strook",
            "scope": "onder alle dragende muren en kolommen",
            "reinforcement_status": "nog te bepalen na belastingen en normtoets",
            "drawing_status": "schematisch concept; CAD volgt in latere engine",
        }

        if has_soft_clay:
            concept["status"] = "VOORLOPIG_MET_ZETTINGSRISICO"
            concept["strip_width_cm"] = 200
            concept["note"] = "Door slappe/zettingsgevoelige lagen wordt voorlopig een verbrede strook aangehouden en moet een palenvariant worden onderzocht."
        elif location_unknown:
            concept["note"] = "Locatie ontbreekt; standaard Brewster-funderingsregel toegepast."
        else:
            concept["note"] = "Standaard Brewster-funderingsregel toegepast."

        return concept

    def build_variants(self, has_soft_clay: bool) -> List[Dict[str, Any]]:
        variants = [
            {
                "variant": "A",
                "name": "Standaard strokenfundering",
                "description": "Strook 150 x 40 cm met funderingsbalk 50 x 60 cm in hart strook.",
                "status": "basisvariant",
                "when_to_use": "Bij voldoende draagkrachtige ondergrond en beperkte zettingsrisico's.",
            },
            {
                "variant": "B",
                "name": "Verbrede strokenfundering",
                "description": "Strook 200 x 40 cm met funderingsbalk 50 x 60 cm.",
                "status": "risicovariant" if has_soft_clay else "optioneel",
                "when_to_use": "Bij lagere draagkracht, hogere lasten of beperkte zettingsgevoeligheid.",
            },
            {
                "variant": "C",
                "name": "Palenfundering",
                "description": "Palen met funderingsbalken/poeren op basis van draagkrachtige dieper gelegen laag.",
                "status": "onderzoeken" if has_soft_clay else "alleen bij onvoldoende draagkracht",
                "when_to_use": "Bij slappe lagen, hoge zettingsrisico's of onvoldoende strookdraagkracht.",
            },
            {
                "variant": "D",
                "name": "Grondverbetering plus stroken",
                "description": "Lokale grondverbetering of ophoog-/verdichtingspakket met strokenfundering.",
                "status": "kostenvariant",
                "when_to_use": "Wanneer grondverbetering goedkoper is dan palen en zettingen beheersbaar zijn.",
            },
        ]
        return variants

    def build_design_rules(self) -> Dict[str, Any]:
        return {
            "default_brewster_foundation_rule": {
                "strip_width_cm": 150,
                "strip_height_cm": 40,
                "foundation_beam_width_cm": 50,
                "foundation_beam_height_cm": 60,
                "beam_position": "hart strook",
                "application": "onder alle dragende muren en kolommen",
            },
            "project_specific_override_rule": {
                "strip_width_cm": 200,
                "trigger": "slappe klei, zettingsrisico, hogere belasting of eerdere projectspecifieke keuze",
            },
            "groundwater_default": "P = -0,50 m",
            "execution_level": "conceptontwerp; niet uitvoeringsgereed",
        }

    def build_required_checks(self, has_soft_clay: bool) -> List[Dict[str, Any]]:
        checks = [
            {
                "check": "draagkracht strookfundering",
                "status": "open",
                "input_needed": "bodemparameters en verticale belastingen",
            },
            {
                "check": "zettingscontrole",
                "status": "verplicht" if has_soft_clay else "open",
                "input_needed": "samendrukkingsparameters en belastingtoename",
            },
            {
                "check": "grondwater / ontgraving",
                "status": "open",
                "input_needed": "actuele grondwaterstand en uitvoeringsmethode",
            },
            {
                "check": "wapening funderingsbalk",
                "status": "open",
                "input_needed": "lijnlasten, kolomlasten, overspanningen en normaanduiding",
            },
            {
                "check": "palenvariant",
                "status": "onderzoeken" if has_soft_clay else "optioneel",
                "input_needed": "sondering en paalpuntniveau",
            },
        ]
        return checks

    def build_preliminary_dimensions(self, selected: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "foundation_level": selected["foundation_level"],
            "strip": {
                "width_m": selected["strip_width_cm"] / 100,
                "height_m": selected["strip_height_cm"] / 100,
            },
            "foundation_beam": {
                "width_m": selected["beam_width_cm"] / 100,
                "height_m": selected["beam_height_cm"] / 100,
                "position": selected["beam_position"],
            },
            "minimum_required_project_inputs_for_calculation": [
                "stramien / assen",
                "dragende muren",
                "kolomposities",
                "lijnlasten",
                "kolomlasten",
                "bodemonderzoek",
                "grondwaterstand",
            ],
        }

    def build_risks(
        self,
        project: Dict[str, Any],
        has_soft_clay: bool,
        groundwater: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        risks = []

        if project.get("location") == "Locatie nog te bepalen":
            risks.append(
                {
                    "risk": "Locatie ontbreekt",
                    "severity": "hoog",
                    "impact": "Funderingsadvies blijft generiek.",
                    "repair": "Vul locatie/adres in project_intake_input.txt.",
                }
            )

        if has_soft_clay:
            risks.append(
                {
                    "risk": "Slappe/zettingsgevoelige laag aanwezig",
                    "severity": "hoog",
                    "impact": "Strokenfundering kan te veel zetten; palenvariant moet worden onderzocht.",
                    "repair": "Voer zettingsberekening en paalvariant uit.",
                }
            )

        if groundwater.get("needs_verification", True):
            risks.append(
                {
                    "risk": "Grondwaterstand nog te verifiëren",
                    "severity": "middel",
                    "impact": "Invloed op ontgraving, bemaling en funderingsniveau.",
                    "repair": "Controleer grondwaterstand projectspecifiek.",
                }
            )

        risks.append(
            {
                "risk": "Belastingen ontbreken",
                "severity": "middel",
                "impact": "Wapening en definitieve afmetingen kunnen nog niet worden berekend.",
                "repair": "Laat v7.4 Constructie Engine lijnlasten en kolomlasten leveren.",
            }
        )

        return risks

    def build_assumptions(
        self,
        selected: Dict[str, Any],
        groundwater: Dict[str, Any],
        soil_profile: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "field": "foundation_type",
                "value": selected["type"],
                "confidence": "basis",
                "source": self.ENGINE_NAME,
                "reason": "Voorlopig concept gekozen volgens Brewster standaardregel en v7.2 geotechniek.",
            },
            {
                "field": "foundation_level",
                "value": selected["foundation_level"],
                "confidence": "basis",
                "source": self.ENGINE_NAME,
                "reason": "Voorlopig funderingsniveau gekoppeld aan standaard grondwateruitgangspunt.",
            },
            {
                "field": "groundwater_level",
                "value": groundwater.get("default_level", "P = -0,50 m"),
                "confidence": groundwater.get("reliability", "basis"),
                "source": groundwater.get("source", "Brewster standaard"),
                "reason": "Nog te verifiëren met projectspecifieke data.",
            },
            {
                "field": "soil_profile",
                "value": soil_profile.get("source", "voorlopig"),
                "confidence": soil_profile.get("reliability", "basis"),
                "source": "Geotechniek Engine v7.2",
                "reason": "Bodemopbouw is voorlopig totdat bodemonderzoek is toegevoegd.",
            },
        ]

    def build_markdown_summary(self, foundation: Dict[str, Any]) -> str:
        project = foundation["project"]
        selected = foundation["selected_concept"]

        lines = [
            "# Project Foundation Design v7.3",
            "",
            f"Project: {project.get('project_name', '')}",
            f"Locatie: {project.get('location', '')}",
            "",
            "## Geselecteerd concept",
            "",
            f"- Type: {selected.get('type', '')}",
            f"- Status: {selected.get('status', '')}",
            f"- Funderingsniveau: {selected.get('foundation_level', '')}",
            f"- Strook: {selected.get('strip_width_cm', '')} x {selected.get('strip_height_cm', '')} cm",
            f"- Funderingsbalk: {selected.get('beam_width_cm', '')} x {selected.get('beam_height_cm', '')} cm",
            "",
            "## Varianten",
            "",
        ]

        for variant in foundation["variants"]:
            lines.append(f"- {variant.get('variant', '')}: {variant.get('name', '')} — {variant.get('status', '')}")

        lines.extend(["", "## Risico's", ""])

        for risk in foundation["risks"]:
            lines.append(f"- {risk.get('risk', '')}: {risk.get('impact', '')}")

        lines.append("")
        return "\n".join(lines)

    def build_dashboard(
        self,
        result: Dict[str, Any],
        foundation: Dict[str, Any],
    ) -> str:
        project = foundation["project"]
        selected = foundation["selected_concept"]

        variant_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('variant', ''))}</td>"
            f"<td>{self.esc(item.get('name', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            f"<td>{self.esc(item.get('description', ''))}</td>"
            "</tr>"
            for item in foundation["variants"]
        )

        check_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('check', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            f"<td>{self.esc(item.get('input_needed', ''))}</td>"
            "</tr>"
            for item in foundation["required_checks"]
        )

        risk_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('risk', ''))}</td>"
            f"<td>{self.esc(item.get('severity', ''))}</td>"
            f"<td>{self.esc(item.get('impact', ''))}</td>"
            f"<td>{self.esc(item.get('repair', ''))}</td>"
            "</tr>"
            for item in foundation["risks"]
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Foundation v7.3</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1240px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; margin-bottom:18px; }}
h1,h2 {{ color:#f8fafc; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ border:1px solid #334155; padding:10px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
code {{ color:#bfdbfe; }}
</style>
</head>
<body>
<main>
<section>
<h1>Project Phoenix Foundation Engine v7.3</h1>
<p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
<p>Voorlopig funderingsconcept op basis van projectcontext en geotechniek.</p>
</section>

<section>
<h2>Project</h2>
<p><strong>Naam:</strong> {self.esc(project.get("project_name", ""))}</p>
<p><strong>Locatie:</strong> {self.esc(project.get("location", ""))}</p>
<p><strong>Type:</strong> {self.esc(project.get("project_type", ""))}</p>
</section>

<section>
<h2>Geselecteerd concept</h2>
<p><strong>Type:</strong> {self.esc(selected.get("type", ""))}</p>
<p><strong>Status:</strong> {self.esc(selected.get("status", ""))}</p>
<p><strong>Funderingsniveau:</strong> {self.esc(selected.get("foundation_level", ""))}</p>
<p><strong>Strook:</strong> {self.esc(selected.get("strip_width_cm", ""))} x {self.esc(selected.get("strip_height_cm", ""))} cm</p>
<p><strong>Funderingsbalk:</strong> {self.esc(selected.get("beam_width_cm", ""))} x {self.esc(selected.get("beam_height_cm", ""))} cm</p>
<p>{self.esc(selected.get("note", ""))}</p>
</section>

<section>
<h2>Varianten</h2>
<table>
<tr><th>Variant</th><th>Naam</th><th>Status</th><th>Beschrijving</th></tr>
{variant_rows}
</table>
</section>

<section>
<h2>Vereiste controles</h2>
<table>
<tr><th>Controle</th><th>Status</th><th>Benodigde input</th></tr>
{check_rows}
</table>
</section>

<section>
<h2>Risico's</h2>
<table>
<tr><th>Risico</th><th>Ernst</th><th>Impact</th><th>Herstel</th></tr>
{risk_rows}
</table>
</section>

<section>
<h2>Bestanden</h2>
<p><code>{self.esc(result.get("foundation_json_path", ""))}</code></p>
<p><code>{self.esc(result.get("foundation_summary_path", ""))}</code></p>
</section>
</main>
</body>
</html>
"""

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


FunderingsEngine = FoundationEngine
BAOEESFoundationEngine = FoundationEngine


def main() -> None:
    engine = FoundationEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
