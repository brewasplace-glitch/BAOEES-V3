from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baoees.project_analyzer.aaie_bib_assumption_loader import AaieBibAssumptionLoader


class GeoFoundationBibEngine:
    """
    PROJECT PHOENIX / BAOEES V3-V4
    Geo/Foundation BIB Engine v4.0

    Doel:
    - Leest AAIE BIB-aannames.
    - Zet BIB-regels om naar een geo- en funderingsanalyse-startpakket.
    - Past fallback grondwaterstand P = -0,50 m toe als projectdata ontbreken.
    - Genereert funderingsvarianten F1 strokenfundering en F2 paalfundering.
    - Maakt een vergelijkingstabel voor funderingskeuze.
    """

    ENGINE_NAME = "Project Phoenix Geo/Foundation BIB Engine"
    ENGINE_VERSION = "v4.0"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        assumptions_path: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.assumptions_path = (
            Path(assumptions_path)
            if assumptions_path
            else self.project_output_root / "aaie_bib_assumptions.json"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        force_refresh_assumptions: bool = False,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        project_context = project_context or self.default_project_context()

        assumptions_status = self.ensure_assumptions(
            project_context=project_context,
            force_refresh_assumptions=force_refresh_assumptions,
        )

        assumptions_data = self.read_json(self.assumptions_path)
        assumptions = assumptions_data.get("assumptions", [])

        geo_defaults = self.build_geo_defaults(assumptions, project_context)
        foundation_variants = self.build_foundation_variants(assumptions, project_context)
        comparison = self.build_foundation_comparison(foundation_variants, geo_defaults, project_context)
        recommendation = self.build_foundation_recommendation(comparison, geo_defaults, project_context)

        output_json_path = self.project_output_root / "geo_foundation_bib_analysis.json"
        output_html_path = self.project_output_root / "geo_foundation_bib_analysis.html"

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Geo- en funderingsanalyse voorbereiden vanuit BIB en AAIE.",
            "project_context": project_context,
            "assumptions_status": assumptions_status,
            "assumptions_path": str(self.assumptions_path),
            "geo_defaults": geo_defaults,
            "foundation_variants": foundation_variants,
            "foundation_comparison": comparison,
            "foundation_recommendation": recommendation,
            "aaie_assumption_links": self.build_aaie_links(assumptions),
            "warnings": self.build_warnings(geo_defaults, foundation_variants, comparison),
            "outputs": {
                "json_path": str(output_json_path),
                "html_path": str(output_html_path),
            },
            "next_steps": [
                "Koppel deze engine in v4.1 aan de projectrapportage.",
                "Gebruik geo_defaults voor automatisch geo-profiel.",
                "Gebruik foundation_variants voor F1/F2 ontwerpstart.",
                "Gebruik foundation_comparison voor rapporttabel.",
                "Registreer alle aannames in AAIE en bronnen/fallbacks in STEE.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(output_json_path, result)
        output_html_path.write_text(
            self.build_html_report(result),
            encoding="utf-8",
        )

        return result

    def ensure_assumptions(
        self,
        project_context: Dict[str, Any],
        force_refresh_assumptions: bool,
    ) -> Dict[str, Any]:
        if self.assumptions_path.exists() and not force_refresh_assumptions:
            return {
                "status": "AANWEZIG",
                "message": "AAIE BIB assumptions bestonden al.",
                "path": str(self.assumptions_path),
            }

        loader = AaieBibAssumptionLoader(project_output_root=self.project_output_root)
        loader_result = loader.run(project_context=project_context, force_refresh_context=force_refresh_assumptions)

        return {
            "status": "GEGENEREERD",
            "message": "AAIE BIB assumptions zijn gegenereerd of vernieuwd.",
            "path": str(self.assumptions_path),
            "loader_result_status": loader_result.get("status"),
        }

    def build_geo_defaults(
        self,
        assumptions: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        groundwater_fallback = self.find_assumption_value(
            assumptions=assumptions,
            code="AAIE-BIB-006",
            default="P = -0,50 m",
        )

        automatic_groundwater = self.find_assumption_value(
            assumptions=assumptions,
            code="AAIE-BIB-005",
            default=True,
        )

        automatic_geo_profile = self.find_assumption_value(
            assumptions=assumptions,
            code="AAIE-BIB-008",
            default=True,
        )

        project_groundwater = self.find_project_value(
            project_context,
            keys=[
                "groundwater",
                "groundwater_level",
                "grondwater",
                "grondwaterstand",
            ],
        )

        selected_groundwater = project_groundwater or groundwater_fallback

        groundwater_source = "project_context" if project_groundwater else "AAIE-BIB fallback"

        return {
            "status": "GEREED",
            "automatic_groundwater_detection": automatic_groundwater,
            "automatic_geo_profile": automatic_geo_profile,
            "groundwater_level": selected_groundwater,
            "groundwater_source": groundwater_source,
            "fallback_groundwater_level": groundwater_fallback,
            "fallback_status": "AAIE fallback assumption",
            "minimum_geo_profile": [
                {
                    "field": "maaiveldniveau",
                    "default": "P = 0,00 m",
                    "source": "project_context of AAIE fallback",
                },
                {
                    "field": "grondwaterstand",
                    "default": selected_groundwater,
                    "source": groundwater_source,
                },
                {
                    "field": "globale bodemopbouw",
                    "default": "automatisch genereren op basis van locatie/kaart/bodemdata of handmatige invoer",
                    "source": "AAIE + STEE",
                },
                {
                    "field": "grondsoort per laag",
                    "default": "voorlopig onbekend totdat bodemdata/sondering beschikbaar zijn",
                    "source": "AAIE assumption",
                },
                {
                    "field": "draagkrachtindicatie",
                    "default": "voorlopige indicatie; definitief na grondonderzoek",
                    "source": "engineering rule",
                },
                {
                    "field": "zettingsgevoeligheid",
                    "default": "voorlopige risico-inschatting",
                    "source": "engineering rule",
                },
                {
                    "field": "advies vervolgonderzoek",
                    "default": "sondering/grondonderzoek vereist voor definitief funderingsadvies",
                    "source": "QA/QC rule",
                },
            ],
            "data_sources_to_check": [
                "projectlocatie",
                "kaartuitsnede",
                "Google Maps of satellietbeeld",
                "bodemkaart",
                "hoogtekaart / maaiveld",
                "oppervlaktewater in omgeving",
                "eerdere projectkennis uit BIB",
                "handmatige invoer gebruiker",
                "sondering of geotechnisch rapport",
            ],
            "aaie_required": True,
            "stee_required": True,
            "qa_qc_required": True,
        }

    def build_foundation_variants(
        self,
        assumptions: List[Dict[str, Any]],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        variants: List[Dict[str, Any]] = []

        for assumption in assumptions:
            code = str(assumption.get("code", ""))
            value = assumption.get("value")

            if code.startswith("AAIE-BIB-F") and isinstance(value, dict):
                variant = dict(value)
                variant["source_assumption_code"] = code
                variants.append(variant)

        if not variants:
            variants = self.default_foundation_variants()

        normalized = []

        for variant in variants:
            code = variant.get("code", "")
            name = variant.get("name", "")

            if code == "F1":
                normalized.append(self.normalize_f1(variant, project_context))
            elif code == "F2":
                normalized.append(self.normalize_f2(variant, project_context))
            else:
                normalized.append(variant)

        existing_codes = {item.get("code") for item in normalized}

        if "F1" not in existing_codes:
            normalized.append(self.normalize_f1({}, project_context))

        if "F2" not in existing_codes:
            normalized.append(self.normalize_f2({}, project_context))

        return normalized

    def normalize_f1(
        self,
        variant: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        default_dimensions = variant.get("default_dimensions") or {}

        return {
            "code": "F1",
            "name": variant.get("name", "Strokenfundering"),
            "type": "fundering_op_staal",
            "description": variant.get(
                "description",
                "Fundering op staal met stroken onder dragende wanden en kolommen.",
            ),
            "default_dimensions": {
                "strookbreedte": default_dimensions.get("strookbreedte", "150 cm tot 200 cm"),
                "strookhoogte": default_dimensions.get("strookhoogte", "40 cm"),
                "funderingsbalk": default_dimensions.get("funderingsbalk", "50 cm x 60 cm"),
                "ligging_balk": default_dimensions.get("ligging_balk", "hart van strook"),
            },
            "checks": variant.get(
                "checks",
                [
                    "draagkracht",
                    "zetting",
                    "grondwaterinvloed",
                    "uitvoerbaarheid",
                    "kosten",
                    "bouwrisico",
                ],
            ),
            "initial_assessment": {
                "cost_level": "laag tot middel",
                "construction_speed": "snel",
                "risk_level": "laag bij draagkrachtige bodem, hoger bij slappe bodem",
                "suitable_when": [
                    "voldoende draagkrachtige bovenlaag",
                    "beperkte zettingsgevoeligheid",
                    "laagbouw of beperkte belasting",
                    "grondwater beheersbaar",
                ],
                "not_suitable_when": [
                    "slappe klei/veen",
                    "hoge zettingsgevoeligheid",
                    "grote kolomlasten",
                    "hoge of variabele grondwaterstand zonder maatregelen",
                ],
            },
            "source": "BIB + AAIE",
        }

    def normalize_f2(
        self,
        variant: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "code": "F2",
            "name": variant.get("name", "Paalfundering"),
            "type": "diepe_fundering",
            "description": variant.get(
                "description",
                "Diepe fundering op palen bij slappe bodem, onvoldoende draagkracht of verhoogd zettingsrisico.",
            ),
            "default_dimensions": variant.get("default_dimensions", {}),
            "checks": variant.get(
                "checks",
                [
                    "paallengte",
                    "paaltype",
                    "draagkracht per paal",
                    "paalbelasting",
                    "paalafstand",
                    "kosten",
                    "uitvoerbaarheid",
                ],
            ),
            "initial_assessment": {
                "cost_level": "middel tot hoog",
                "construction_speed": "middel",
                "risk_level": "lager bij slappe bodem, afhankelijk van paaltype en grondonderzoek",
                "suitable_when": [
                    "slappe of samendrukbare bovenlagen",
                    "grote lasten",
                    "zetting moet sterk worden beperkt",
                    "draagkrachtige laag ligt dieper",
                ],
                "not_suitable_when": [
                    "klein project met voldoende draagkrachtige bovenlaag",
                    "kosten niet proportioneel",
                    "trillingsgevoelige omgeving zonder passende paaltechniek",
                ],
            },
            "source": "BIB + AAIE",
        }

    def build_foundation_comparison(
        self,
        foundation_variants: List[Dict[str, Any]],
        geo_defaults: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        comparison = []

        aspects = [
            "draagkracht",
            "zetting",
            "kosten",
            "bouwtijd",
            "risico",
            "bodemgeschiktheid",
            "grondwaterinvloed",
            "constructieve haalbaarheid",
            "vergunning / acceptatie",
        ]

        for variant in foundation_variants:
            code = variant.get("code", "")
            row = {
                "code": code,
                "name": variant.get("name", ""),
                "scores": {},
                "remarks": [],
            }

            for aspect in aspects:
                row["scores"][aspect] = self.score_variant_aspect(code, aspect, geo_defaults, project_context)

            row["total_score"] = sum(item["score"] for item in row["scores"].values())
            row["remarks"] = self.variant_remarks(code, geo_defaults, project_context)
            comparison.append(row)

        comparison.sort(key=lambda item: item.get("total_score", 0), reverse=True)
        return comparison

    def score_variant_aspect(
        self,
        code: str,
        aspect: str,
        geo_defaults: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        text = json.dumps(project_context, ensure_ascii=False, default=str).lower()

        weak_soil_terms = ["slappe klei", "veen", "zetting", "samendrukbaar", "lage draagkracht", "slappe bodem"]
        strong_soil_terms = ["zand", "vaste klei", "draagkrachtig", "funderen op staal"]

        weak_soil = any(term in text for term in weak_soil_terms)
        strong_soil = any(term in text for term in strong_soil_terms)

        if code == "F1":
            base = {
                "draagkracht": 3,
                "zetting": 3,
                "kosten": 5,
                "bouwtijd": 5,
                "risico": 3,
                "bodemgeschiktheid": 3,
                "grondwaterinvloed": 3,
                "constructieve haalbaarheid": 4,
                "vergunning / acceptatie": 4,
            }
            if weak_soil and aspect in ["draagkracht", "zetting", "risico", "bodemgeschiktheid"]:
                score = max(1, base[aspect] - 2)
                note = "Verlaagd door mogelijke slappe/zettingsgevoelige bodem."
            elif strong_soil and aspect in ["draagkracht", "zetting", "bodemgeschiktheid"]:
                score = min(5, base[aspect] + 1)
                note = "Verhoogd door indicatie draagkrachtige bodem."
            else:
                score = base[aspect]
                note = "Voorlopige BIB/AAIE-score."
        elif code == "F2":
            base = {
                "draagkracht": 5,
                "zetting": 5,
                "kosten": 2,
                "bouwtijd": 3,
                "risico": 4,
                "bodemgeschiktheid": 4,
                "grondwaterinvloed": 4,
                "constructieve haalbaarheid": 5,
                "vergunning / acceptatie": 4,
            }
            if weak_soil and aspect in ["draagkracht", "zetting", "risico", "bodemgeschiktheid"]:
                score = min(5, base[aspect] + 1)
                note = "Verhoogd door mogelijke slappe/zettingsgevoelige bodem."
            elif strong_soil and aspect in ["kosten", "bouwtijd"]:
                score = max(1, base[aspect] - 1)
                note = "Minder gunstig als eenvoudige fundering op staal voldoende is."
            else:
                score = base[aspect]
                note = "Voorlopige BIB/AAIE-score."
        else:
            score = 3
            note = "Onbekende variant; neutrale score."

        return {
            "score": score,
            "scale": "1=ongunstig, 5=gunstig",
            "note": note,
        }

    def variant_remarks(
        self,
        code: str,
        geo_defaults: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:
        groundwater = geo_defaults.get("groundwater_level", "onbekend")

        if code == "F1":
            return [
                "Strokenfundering is standaard goedkoop en snel uitvoerbaar.",
                "Definitieve keuze afhankelijk van draagkracht en zettingsberekening.",
                f"Grondwaterstand voorlopig: {groundwater}.",
                "Bij slappe bodem of hoge zettingsgevoeligheid F2 serieus onderzoeken.",
            ]

        if code == "F2":
            return [
                "Paalfundering is robuuster bij slappe bodem en zettingsrisico.",
                "Duurder en vraagt meer geotechnisch detailonderzoek.",
                f"Grondwaterstand voorlopig: {groundwater}.",
                "Paaltype en paallengte pas definitief na sondering/grondonderzoek.",
            ]

        return ["Aanvullende beoordeling vereist."]

    def build_foundation_recommendation(
        self,
        comparison: List[Dict[str, Any]],
        geo_defaults: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        best = comparison[0] if comparison else {}

        return {
            "status": "VOORLOPIG",
            "preferred_variant_by_score": {
                "code": best.get("code"),
                "name": best.get("name"),
                "total_score": best.get("total_score"),
            },
            "important_note": "Dit is een automatische voorlopige BIB/AAIE-beoordeling. Definitieve funderingskeuze vereist projectlasten, bodemonderzoek en constructieve berekening.",
            "required_before_final_design": [
                "projectlocatie bevestigen",
                "maaiveldpeil bepalen",
                "grondwaterstand verifiëren",
                "bodemopbouw/sondering invoeren",
                "belastingen bepalen",
                "zettingscontrole uitvoeren",
                "draagkrachtcontrole uitvoeren",
                "QA/QC uitvoeren",
            ],
        }

    def build_aaie_links(self, assumptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        relevant_codes = {
            "AAIE-BIB-005",
            "AAIE-BIB-006",
            "AAIE-BIB-007",
            "AAIE-BIB-008",
            "AAIE-BIB-009",
            "AAIE-BIB-010",
        }

        links = []

        for assumption in assumptions:
            code = assumption.get("code", "")
            if code in relevant_codes or str(code).startswith("AAIE-BIB-F"):
                links.append(
                    {
                        "code": code,
                        "name": assumption.get("name"),
                        "discipline": assumption.get("discipline"),
                        "source": assumption.get("source"),
                    }
                )

        return links

    def build_warnings(
        self,
        geo_defaults: Dict[str, Any],
        foundation_variants: List[Dict[str, Any]],
        comparison: List[Dict[str, Any]],
    ) -> List[str]:
        warnings = []

        if not geo_defaults.get("groundwater_level"):
            warnings.append("Geen grondwaterstand bepaald.")

        variant_codes = {variant.get("code") for variant in foundation_variants}

        if "F1" not in variant_codes:
            warnings.append("F1 strokenfundering ontbreekt.")

        if "F2" not in variant_codes:
            warnings.append("F2 paalfundering ontbreekt.")

        if not comparison:
            warnings.append("Geen funderingsvergelijking opgebouwd.")

        if not warnings:
            warnings.append("Geen kritieke Geo/Foundation BIB-waarschuwingen.")

        return warnings

    def default_foundation_variants(self) -> List[Dict[str, Any]]:
        return [
            {
                "code": "F1",
                "name": "Strokenfundering",
                "description": "Fundering op staal met stroken onder dragende wanden en kolommen.",
            },
            {
                "code": "F2",
                "name": "Paalfundering",
                "description": "Diepe fundering op palen bij slappe bodem of verhoogd zettingsrisico.",
            },
        ]

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default Geo/Foundation BIB Analysis",
            "project_type": "bouw",
            "purpose": "Automatische geo- en funderingsanalyse vanuit BIB en AAIE.",
            "location": "nog niet opgegeven",
            "groundwater": None,
            "soil_profile": None,
        }

    def find_assumption_value(
        self,
        assumptions: List[Dict[str, Any]],
        code: str,
        default: Any,
    ) -> Any:
        for assumption in assumptions:
            if assumption.get("code") == code:
                return assumption.get("value", default)

        return default

    def find_project_value(self, data: Dict[str, Any], keys: List[str]) -> Any:
        for key in keys:
            if key in data and data[key] not in [None, "", []]:
                return data[key]

        for value in data.values():
            if isinstance(value, dict):
                found = self.find_project_value(value, keys)
                if found not in [None, "", []]:
                    return found

        return None

    def build_html_report(self, result: Dict[str, Any]) -> str:
        geo = result.get("geo_defaults", {})
        variants = result.get("foundation_variants", [])
        comparison = result.get("foundation_comparison", [])
        recommendation = result.get("foundation_recommendation", {})

        geo_rows = []

        for item in geo.get("minimum_geo_profile", []):
            geo_rows.append(
                "<tr>"
                f"<td>{self.esc(item.get('field', ''))}</td>"
                f"<td>{self.esc(item.get('default', ''))}</td>"
                f"<td>{self.esc(item.get('source', ''))}</td>"
                "</tr>"
            )

        variant_rows = []

        for variant in variants:
            default_dimensions = variant.get("default_dimensions", {})
            variant_rows.append(
                "<tr>"
                f"<td>{self.esc(variant.get('code', ''))}</td>"
                f"<td>{self.esc(variant.get('name', ''))}</td>"
                f"<td>{self.esc(variant.get('type', ''))}</td>"
                f"<td>{self.esc(variant.get('description', ''))}</td>"
                f"<td><code>{self.esc(json.dumps(default_dimensions, ensure_ascii=False, default=str))}</code></td>"
                "</tr>"
            )

        comparison_rows = []

        for row in comparison:
            scores = row.get("scores", {})
            score_text = "; ".join(
                [
                    f"{aspect}: {score_data.get('score')}"
                    for aspect, score_data in scores.items()
                ]
            )

            comparison_rows.append(
                "<tr>"
                f"<td>{self.esc(row.get('code', ''))}</td>"
                f"<td>{self.esc(row.get('name', ''))}</td>"
                f"<td>{self.esc(row.get('total_score', ''))}</td>"
                f"<td>{self.esc(score_text)}</td>"
                f"<td>{self.esc(' | '.join(row.get('remarks', [])))}</td>"
                "</tr>"
            )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Geo/Foundation BIB Analysis</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #050816;
      color: #f8fafc;
      line-height: 1.5;
    }}
    header {{
      padding: 34px 42px;
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
      border-bottom: 1px solid #334155;
    }}
    main {{
      padding: 30px 38px 50px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border: 1px solid #334155;
      margin-top: 18px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #334155;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #0f172a;
      color: #bfdbfe;
    }}
    code {{
      color: #cbd5e1;
      white-space: pre-wrap;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>GEO / FOUNDATION BIB ANALYSIS</h1>
    <p>Automatische geo- en funderingsstart vanuit BIB + AAIE.</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Grondwaterstand</h3>
        <p>{self.esc(geo.get("groundwater_level", ""))}</p>
        <p class="muted">{self.esc(geo.get("groundwater_source", ""))}</p>
      </div>
      <div class="card">
        <h3>Voorkeursvariant voorlopig</h3>
        <p>{self.esc(recommendation.get("preferred_variant_by_score", {}).get("code", ""))} — {self.esc(recommendation.get("preferred_variant_by_score", {}).get("name", ""))}</p>
      </div>
      <div class="card">
        <h3>Belangrijke waarschuwing</h3>
        <p class="muted">{self.esc(recommendation.get("important_note", ""))}</p>
      </div>
    </section>

    <h2>Geo-profiel startwaarden</h2>
    <table>
      <thead>
        <tr>
          <th>Veld</th>
          <th>Waarde</th>
          <th>Bron</th>
        </tr>
      </thead>
      <tbody>
        {''.join(geo_rows)}
      </tbody>
    </table>

    <h2>Funderingsvarianten</h2>
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Naam</th>
          <th>Type</th>
          <th>Omschrijving</th>
          <th>Standaard dimensies</th>
        </tr>
      </thead>
      <tbody>
        {''.join(variant_rows)}
      </tbody>
    </table>

    <h2>Funderingsvergelijking</h2>
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Naam</th>
          <th>Totaalscore</th>
          <th>Scores</th>
          <th>Opmerkingen</th>
        </tr>
      </thead>
      <tbody>
        {''.join(comparison_rows)}
      </tbody>
    </table>
  </main>
</body>
</html>
"""

    def read_json(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = GeoFoundationBibEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()