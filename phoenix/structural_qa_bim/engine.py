#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

STATUS = "PASS_STRUCTURAL_QA_GATE_EXECUTED_BIM_HANDOFF_CREATED"
RELEASE_DECISION = "HOLD"
NEXT_STAGE = "PHOENIX_4.41_REAL_PROJECT_RELEASE_HOLD_CLOSURE_AND_FINAL_STRUCTURAL_PACKAGE"
ENGINE_VERSION = "1.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_chain(design: Dict[str, Any], solver: Dict[str, Any], report3d: Dict[str, Any], source_sha: str) -> None:
    if design.get("status") != "PASS_PRELIMINARY_STRUCTURAL_DESIGN_CONSOLIDATION_AND_DRAWINGS":
        raise RuntimeError("Design consolidation evidence is not PASS")
    if solver.get("status") not in (
        "PASS_REAL_OPEN_SOURCE_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION",
        "PASS_PRIMARY_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION",
    ):
        raise RuntimeError("Solver evidence is not PASS")
    if report3d.get("status") != "PASS_PRELIMINARY_3D_STRUCTURAL_MODEL_AND_CALCULATION_REPORT":
        raise RuntimeError("3D/report evidence is not PASS")
    for name, sha in [
        ("design", design.get("source_sha256")),
        ("solver", solver.get("source_sha256")),
        ("3d_report", report3d.get("source_sha256")),
    ]:
        if sha != source_sha:
            raise RuntimeError(f"{name} source SHA mismatch")


def classify_holds(release_holds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    classification = {
        "H01": ("EXTERNAL_AUTHORITY_CONFIRMATION", "Research can assist, but legally applicable code/wind basis requires authoritative confirmation."),
        "H02": ("EXTERNAL_SITE_EVIDENCE", "Requires site-specific geotechnical investigation and settlement/groundwater evidence."),
        "H03": ("PHOENIX_AUTOMATABLE_PENDING", "Phoenix can continue semantic mapping, but current source vectors are not yet accepted."),
        "H04": ("EXTERNAL_PRODUCT_SITE_EVIDENCE", "Timber species/grade/dressed dimensions/service condition must be physically confirmed."),
        "H05": ("PHOENIX_AUTOMATABLE_AFTER_H01_H03_H04", "Connection/uplift design can be completed after governing inputs are confirmed."),
        "H06": ("PHOENIX_AUTOMATABLE_AFTER_H01_H02_H03", "RC N-M/shear/anchorage/punching/detailing can be completed after governing inputs are confirmed."),
        "H07": ("MIXED_EXTERNAL_AND_AUTOMATABLE", "Actual tank height/location/support geometry must be confirmed; Phoenix can then complete wind/stability/design."),
        "H08": ("PROFESSIONAL_APPROVAL_REQUIRED", "Qualified structural professional review/sign-off cannot be replaced by automation."),
    }
    result = []
    for item in release_holds:
        hid = item["id"]
        cls, note = classification.get(hid, ("UNCLASSIFIED_HOLD", "Requires review."))
        result.append({
            "id": hid,
            "hold": item["hold"],
            "required_for_release": item["required_for_release"],
            "closure_class": cls,
            "status": "OPEN",
            "closure_note": note,
        })
    return result


def qa_matrix(design: Dict[str, Any], solver: Dict[str, Any], report3d: Dict[str, Any]) -> Dict[str, Any]:
    holds = classify_holds(design["release_holds"])
    open_count = sum(1 for h in holds if h["status"] == "OPEN")

    gates = [
        {"id":"Q01","gate":"Source traceability and SHA chain","status":"PASS"},
        {"id":"Q02","gate":"Preliminary load derivation","status":"PASS"},
        {"id":"Q03","gate":"Real open-source solver execution and analytical cross-check","status":"PASS"},
        {"id":"Q04","gate":"Element verification / foundation gravity sensitivity","status":"PASS_PRELIMINARY"},
        {"id":"Q05","gate":"2D structural drawing consolidation","status":"PASS_PRELIMINARY"},
        {"id":"Q06","gate":"3D structural coordination model","status":"PASS_PRELIMINARY"},
        {"id":"Q07","gate":"Calculation report DOCX/PDF evidence","status":"PASS_PRELIMINARY"},
        {"id":"Q08","gate":"Confirmed Suriname legal code/wind basis","status":"HOLD"},
        {"id":"Q09","gate":"Site-specific geotechnical evidence","status":"HOLD"},
        {"id":"Q10","gate":"Confirmed material/product inputs and complete structural topology","status":"HOLD"},
        {"id":"Q11","gate":"Final professional structural review","status":"HOLD"},
    ]
    return {
        "pipeline_gates": gates,
        "release_holds": holds,
        "open_release_holds": open_count,
        "pipeline_integrity": "PASS",
        "technical_preliminary_workflow": "PASS",
        "construction_release": RELEASE_DECISION,
        "release_allowed": False,
    }


def create_ifc(model_metadata: Dict[str, Any], design: Dict[str, Any], source_sha: str, out: Path) -> Dict[str, Any]:
    import ifcopenshell
    import ifcopenshell.guid

    f = ifcopenshell.file(schema="IFC4")
    guid = ifcopenshell.guid.new

    point = f.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0))
    axis = f.create_entity("IfcAxis2Placement3D", Location=point)
    context = f.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Model",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
        WorldCoordinateSystem=axis,
    )

    units = [
        f.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE"),
        f.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE"),
        f.create_entity("IfcSIUnit", UnitType="VOLUMEUNIT", Name="CUBIC_METRE"),
    ]
    unit_assignment = f.create_entity("IfcUnitAssignment", Units=units)

    project = f.create_entity(
        "IfcProject",
        GlobalId=guid(),
        Name="PHOENIX Anijstraat 616 Structural QA BIM Handoff",
        RepresentationContexts=[context],
        UnitsInContext=unit_assignment,
    )
    site = f.create_entity("IfcSite", GlobalId=guid(), Name="Anijstraat #616", CompositionType="ELEMENT")
    building = f.create_entity("IfcBuilding", GlobalId=guid(), Name="Woonhuis Anijstraat #616", CompositionType="ELEMENT")
    storey = f.create_entity(
        "IfcBuildingStorey",
        GlobalId=guid(),
        Name="Structural Coordination Storey",
        CompositionType="ELEMENT",
        Elevation=0.0,
    )

    f.create_entity("IfcRelAggregates", GlobalId=guid(), RelatingObject=project, RelatedObjects=[site])
    f.create_entity("IfcRelAggregates", GlobalId=guid(), RelatingObject=site, RelatedObjects=[building])
    f.create_entity("IfcRelAggregates", GlobalId=guid(), RelatingObject=building, RelatedObjects=[storey])

    proxies = []
    for comp in model_metadata["components"]:
        proxy = f.create_entity(
            "IfcBuildingElementProxy",
            GlobalId=guid(),
            Name=comp["id"],
            Description=comp.get("note",""),
            ObjectType=comp["category"],
            PredefinedType="NOTDEFINED",
        )

        props = [
            f.create_entity("IfcPropertySingleValue", Name="PhoenixStatus", NominalValue=f.create_entity("IfcLabel", comp["status"])),
            f.create_entity("IfcPropertySingleValue", Name="PhoenixCategory", NominalValue=f.create_entity("IfcLabel", comp["category"])),
            f.create_entity("IfcPropertySingleValue", Name="PhoenixSourceSHA256", NominalValue=f.create_entity("IfcText", source_sha)),
            f.create_entity("IfcPropertySingleValue", Name="PhoenixExtentsM", NominalValue=f.create_entity("IfcText", json.dumps(comp["extents_m"]))),
            f.create_entity("IfcPropertySingleValue", Name="PhoenixCenterM", NominalValue=f.create_entity("IfcText", json.dumps(comp["center_m"]))),
            f.create_entity("IfcPropertySingleValue", Name="PhoenixRelease", NominalValue=f.create_entity("IfcLabel", "LOCKED")),
        ]
        pset = f.create_entity(
            "IfcPropertySet",
            GlobalId=guid(),
            Name="Pset_PhoenixStructuralQA",
            HasProperties=props,
        )
        f.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=guid(),
            RelatedObjects=[proxy],
            RelatingPropertyDefinition=pset,
        )
        proxies.append(proxy)

    if proxies:
        f.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=guid(),
            RelatedElements=proxies,
            RelatingStructure=storey,
        )

    ifc_path = out / "ANJ616_structural_QA_handoff.ifc"
    f.write(str(ifc_path))

    reopened = ifcopenshell.open(str(ifc_path))
    proxy_count = len(reopened.by_type("IfcBuildingElementProxy"))
    if proxy_count != len(proxies):
        raise RuntimeError("IFC readback proxy count mismatch")

    return {
        "ifc_path": ifc_path.name,
        "schema": reopened.schema,
        "proxy_count": proxy_count,
        "readback": "PASS",
    }


def write_ifctester_json_report(report_obj: Any, report_path: Path) -> Dict[str, Any]:
    """Use IfcTester's own encoder; raw report results contain IFC entity objects."""
    results = report_obj.report()
    report_obj.to_file(str(report_path))

    if not report_path.exists() or report_path.stat().st_size <= 0:
        raise RuntimeError("IfcTester JSON report was not written")

    serialized = json.loads(report_path.read_text(encoding="utf-8"))
    status = serialized.get("status")
    if status is not True:
        raise RuntimeError(f"IDS validation failed: {status}")

    return serialized


def validate_ids(ifc_path: Path, out: Path) -> Dict[str, Any]:
    import ifcopenshell
    from ifctester import ids, reporter

    spec_file = ids.Ids(title="PHOENIX Structural BIM QA Requirements")
    spec = ids.Specification(name="All PHOENIX structural proxies carry QA metadata")
    spec.applicability.append(ids.Entity(name="IFCBUILDINGELEMENTPROXY"))
    spec.requirements.append(ids.Property(
        baseName="PhoenixStatus",
        propertySet="Pset_PhoenixStructuralQA",
        dataType="IfcLabel",
        cardinality="required",
    ))
    spec.requirements.append(ids.Property(
        baseName="PhoenixCategory",
        propertySet="Pset_PhoenixStructuralQA",
        dataType="IfcLabel",
        cardinality="required",
    ))
    spec.requirements.append(ids.Property(
        baseName="PhoenixRelease",
        value="LOCKED",
        propertySet="Pset_PhoenixStructuralQA",
        dataType="IfcLabel",
        cardinality="required",
    ))
    spec_file.specifications.append(spec)

    ids_path = out / "ANJ616_structural_QA_requirements.ids"
    spec_file.to_xml(str(ids_path))

    model = ifcopenshell.open(str(ifc_path))
    spec_file.validate(model)

    report_path = out / "ANJ616_ifctester_report.json"
    report = reporter.Json(spec_file)
    serialized = write_ifctester_json_report(report, report_path)

    return {
        "ids_path": ids_path.name,
        "report_path": report_path.name,
        "ifctester_report_status": serialized.get("status"),
        "ifctester_json_writer": "reporter.Json.to_file",
        "status": "PASS",
    }


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def write_dashboard(summary: Dict[str, Any], qa: Dict[str, Any], out: Path) -> None:
    gate_rows = "".join(
        f"<tr><td>{g['id']}</td><td>{g['gate']}</td><td>{g['status']}</td></tr>"
        for g in qa["pipeline_gates"]
    )
    hold_rows = "".join(
        f"<tr><td>{h['id']}</td><td>{h['hold']}</td><td>{h['closure_class']}</td><td>{h['status']}</td></tr>"
        for h in qa["release_holds"]
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>PHOENIX Structural QA Gate - Anijstraat 616</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1200px;margin:auto;padding:24px}}
table{{border-collapse:collapse;width:100%;margin-bottom:28px}}
th,td{{border:1px solid #777;padding:8px;vertical-align:top}}
.notice{{font-weight:bold;border:2px solid #222;padding:14px}}
</style></head><body>
<h1>PHOENIX 4.41 - Structural QA Release Gate + BIM Integration</h1>
<div class="notice">QA GATE EXECUTION: PASS | CONSTRUCTION RELEASE: HOLD</div>
<p>Project: {summary['project_id']}</p>
<p>IFC/IDS BIM handoff created and validated. Release remains locked because mandatory external/professional holds are open.</p>
<h2>Pipeline QA</h2><table><tr><th>ID</th><th>Gate</th><th>Status</th></tr>{gate_rows}</table>
<h2>Release holds</h2><table><tr><th>ID</th><th>Hold</th><th>Closure class</th><th>Status</th></tr>{hold_rows}</table>
<p><b>PRELIMINARY / NOT FOR CONSTRUCTION</b></p>
</body></html>"""
    (out / "structural_QA_dashboard.html").write_text(html, encoding="utf-8")


def main_run(design_path: Path, solver_path: Path, report3d_path: Path, model_metadata_path: Path,
             source_pdf: Path, out: Path) -> Dict[str, Any]:
    design = json.loads(design_path.read_text(encoding="utf-8"))
    solver = json.loads(solver_path.read_text(encoding="utf-8"))
    report3d = json.loads(report3d_path.read_text(encoding="utf-8"))
    model_metadata = json.loads(model_metadata_path.read_text(encoding="utf-8"))
    source_sha = sha256_file(source_pdf)

    validate_chain(design, solver, report3d, source_sha)
    qa = qa_matrix(design, solver, report3d)

    out.mkdir(parents=True, exist_ok=True)
    bim = out / "bim"
    bim.mkdir(exist_ok=True)

    ifc = create_ifc(model_metadata, design, source_sha, bim)
    ids_result = validate_ids(bim / ifc["ifc_path"], bim)

    write_csv(
        out / "QA_release_matrix.csv",
        qa["pipeline_gates"],
        ["id","gate","status"],
    )
    write_csv(
        out / "release_holds.csv",
        qa["release_holds"],
        ["id","hold","required_for_release","closure_class","status","closure_note"],
    )

    handoff = {
        "schema":"PHOENIX_STRUCTURAL_BIM_HANDOFF_1.0",
        "project_id":design["project_id"],
        "source_sha256":source_sha,
        "release_status":"LOCKED",
        "model_status":report3d["model_status"],
        "ifc":ifc,
        "ids_validation":ids_result,
        "visual_3d_source":"Prior stage GLB/OBJ/STL remains authoritative visual coordination evidence.",
        "qa_gate":qa,
        "professional_review_required":True,
    }
    (bim / "digital_twin_structural_handoff.json").write_text(json.dumps(handoff, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        "schema":"PHOENIX_STRUCTURAL_QA_BIM_1.0",
        "project_id":design["project_id"],
        "source_sha256":source_sha,
        "pipeline_integrity":"PASS",
        "ifc_export":"PASS",
        "ifc_readback":"PASS",
        "ids_validation":"PASS",
        "open_release_holds":qa["open_release_holds"],
        "release_decision":RELEASE_DECISION,
        "release_allowed":False,
        "preliminary_not_for_construction":True,
        "professional_structural_review_required":True,
        "status":STATUS,
        "next_stage":NEXT_STAGE,
    }
    (out / "structural_QA_BIM_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "structural_QA_release_gate.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# PHOENIX 4.41 - Structural QA Release Gate + BIM Integration",
        "",
        f"Project: `{summary['project_id']}`",
        "",
        f"Pipeline integrity: **{summary['pipeline_integrity']}**",
        f"IFC export/readback: **PASS**",
        f"IDS validation: **PASS**",
        f"Open mandatory release holds: **{summary['open_release_holds']}**",
        f"Construction release decision: **{summary['release_decision']}**",
        "",
        "The QA workflow itself passes, but construction release remains locked.",
        "",
        "## Release-hold closure classes",
        "",
    ]
    for h in qa["release_holds"]:
        md.append(f"- **{h['id']}** — {h['closure_class']}: {h['hold']}")
    md += [
        "",
        "**PRELIMINARY / NOT FOR CONSTRUCTION**",
        "",
        "`FOR_CONSTRUCTION_RELEASE = LOCKED`",
        "",
        f"Next stage: `{NEXT_STAGE}`",
    ]
    (out / "structural_QA_release_gate_report.md").write_text("\n".join(md), encoding="utf-8")

    write_dashboard(summary, qa, out)

    manifest = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "evidence_manifest.json":
            manifest[p.relative_to(out).as_posix()] = {
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
    (out / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return summary


def self_test() -> None:
    holds = [
        {"id":f"H{i:02d}","hold":"x","required_for_release":"MANDATORY"}
        for i in range(1,9)
    ]
    c = classify_holds(holds)
    assert len(c) == 8
    assert c[1]["closure_class"] == "EXTERNAL_SITE_EVIDENCE"
    assert c[-1]["closure_class"] == "PROFESSIONAL_APPROVAL_REQUIRED"
    assert all(x["status"] == "OPEN" for x in c)
    print("PHOENIX_4_41_STRUCTURAL_QA_BIM_SELF_TEST=PASS")


def verify_output(path: Path) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    out = path.parent
    assert d["status"] == STATUS
    assert d["pipeline_integrity"] == "PASS"
    assert d["ifc_export"] == "PASS"
    assert d["ifc_readback"] == "PASS"
    assert d["ids_validation"] == "PASS"
    assert d["release_decision"] == "HOLD"
    assert d["release_allowed"] is False
    assert d["open_release_holds"] >= 1
    required = [
        "bim/ANJ616_structural_QA_handoff.ifc",
        "bim/ANJ616_structural_QA_requirements.ids",
        "bim/ANJ616_ifctester_report.json",
        "bim/digital_twin_structural_handoff.json",
        "QA_release_matrix.csv",
        "release_holds.csv",
        "structural_QA_dashboard.html",
        "structural_QA_release_gate_report.md",
        "evidence_manifest.json",
    ]
    for rel in required:
        p = out / rel
        assert p.exists() and p.stat().st_size > 0, rel
    print("PHOENIX_4_41_STRUCTURAL_QA_BIM_OUTPUT_VERIFY=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design-json", type=Path)
    ap.add_argument("--solver-json", type=Path)
    ap.add_argument("--report3d-json", type=Path)
    ap.add_argument("--model-metadata", type=Path)
    ap.add_argument("--source-pdf", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--verify-output", type=Path)
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.verify_output:
        verify_output(args.verify_output)
        return 0
    if not all([args.design_json,args.solver_json,args.report3d_json,args.model_metadata,args.source_pdf,args.output]):
        ap.error("--design-json --solver-json --report3d-json --model-metadata --source-pdf --output required")

    result = main_run(
        args.design_json,
        args.solver_json,
        args.report3d_json,
        args.model_metadata,
        args.source_pdf,
        args.output,
    )
    print(f"PROJECT_ID={result['project_id']}")
    print("PIPELINE_INTEGRITY=PASS")
    print("BIM_IFC_EXPORT=PASS")
    print("IFC_READBACK=PASS")
    print("IDS_VALIDATION=PASS")
    print(f"OPEN_RELEASE_HOLDS={result['open_release_holds']}")
    print("QA_GATE_EXECUTION=PASS")
    print("RELEASE_DECISION=HOLD")
    print("FOR_CONSTRUCTION_RELEASE=LOCKED")
    print(f"STRUCTURAL_QA_BIM_STATUS={result['status']}")
    print(f"NEXT_STAGE={result['next_stage']}")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
