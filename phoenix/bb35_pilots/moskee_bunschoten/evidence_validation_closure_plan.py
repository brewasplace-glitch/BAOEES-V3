"""BB35 Evidence Validation & Closure Plan engine."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from collections import defaultdict, deque
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class EvidenceValidationClosurePlanEngine:
    VERSION = "1.5.0"

    def evaluate(
        self,
        *,
        intake_report: Mapping[str, Any],
        verified_register: Mapping[str, Any],
        review_summary: Mapping[str, Any],
        closure_register: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_sources(
            intake_report=intake_report,
            verified_register=verified_register,
            review_summary=review_summary,
        )

        closure_items = [
            dict(item) for item in closure_register["closure_items"]
        ]
        strategic_decisions = [
            dict(item) for item in closure_register["strategic_decisions"]
        ]

        request_ids = [item["request_id"] for item in closure_items]
        if request_ids != [
            "REQ-102",
            "REQ-103",
            "REQ-104",
            "REQ-105",
            "REQ-106",
            "REQ-107",
            "REQ-108",
        ]:
            raise ValueError("Closure register must contain REQ-102 through REQ-108.")

        decision_ids = {
            decision["decision_id"] for decision in strategic_decisions
        }
        for item in closure_items:
            missing = set(item["strategic_decisions"]) - decision_ids
            if missing:
                raise ValueError(
                    f"{item['request_id']} references unknown decisions: "
                    f"{sorted(missing)}"
                )
            if not item["acceptance_criteria"]:
                raise ValueError(
                    f"{item['request_id']} has no acceptance criteria."
                )
            if not item["external_deliverables"]:
                raise ValueError(
                    f"{item['request_id']} has no external deliverables."
                )

        dependencies = {
            item["request_id"]: list(item["depends_on"])
            for item in closure_items
        }
        execution_order = self._topological_order(dependencies)

        critical_path_root = config["critical_path_root"]
        downstream = self._downstream_map(closure_items)
        critical_downstream = sorted(downstream[critical_path_root])

        owner_counts: dict[str, int] = defaultdict(int)
        for item in closure_items:
            owner_counts[item["closure_authority"]] += 1

        professional_work_orders = [
            item for item in closure_items
            if item["closure_authority"] in {
                "external_professional",
                "mixed",
            }
        ]
        internal_action_count = sum(
            len(item["internal_actions"]) for item in closure_items
        )
        acceptance_criterion_count = sum(
            len(item["acceptance_criteria"]) for item in closure_items
        )

        result = {
            "schema_version": (
                "phoenix.bb35.evidence-validation-closure-plan/1.0"
            ),
            "engine_version": self.VERSION,
            "pilot_id": "BB35-PILOT-001-HBM",
            "project_id": "HBM-2026-001",
            "project_name": "Uitbreiding Haci Bayram Moskee",
            "authoritative_scope": {
                "width_m": 7.0,
                "depth_m": 10.0,
                "storeys": 2,
                "gross_extension_area_m2": 140.0,
            },
            "source_gate_status": intake_report["status"],
            "status": "EVIDENCE_VALIDATION_COMPLETE_CLOSURE_PLAN_READY",
            "closure_execution_allowed": True,
            "closure_item_count": len(closure_items),
            "remaining_blocking_input_count": int(
                intake_report["remaining_blocking_input_count"]
            ),
            "closed_request_count": int(
                intake_report["closed_request_count"]
            ),
            "partial_request_count": int(
                intake_report["partial_request_count"]
            ),
            "open_request_count": int(
                intake_report["open_request_count"]
            ),
            "strategic_decision_count": len(strategic_decisions),
            "pending_strategic_decision_count": sum(
                1 for item in strategic_decisions
                if item["status"] == "PENDING"
            ),
            "professional_work_order_count": len(
                professional_work_orders
            ),
            "internal_automation_action_count": internal_action_count,
            "acceptance_criterion_count": acceptance_criterion_count,
            "closure_authority_counts": dict(
                sorted(owner_counts.items())
            ),
            "critical_path_root": critical_path_root,
            "critical_path_downstream_requests": critical_downstream,
            "recommended_execution_order": execution_order,
            "closure_items": closure_items,
            "strategic_decisions": strategic_decisions,
            "policy": config["policy"],
            "concept_generation_allowed": True,
            "final_generation_allowed": False,
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "next_gate": (
                "Approve the strategic use and occupancy decisions for "
                "REQ-107, then issue the external professional work orders."
            ),
        }
        result["report_fingerprint_sha256"] = self._fingerprint(result)
        return result

    @staticmethod
    def _validate_sources(
        *,
        intake_report: Mapping[str, Any],
        verified_register: Mapping[str, Any],
        review_summary: Mapping[str, Any],
    ) -> None:
        checks = {
            "intake_status": (
                intake_report.get("status")
                == "EVIDENCE_ACQUISITION_PARTIALLY_SATISFIED"
            ),
            "six_valid_files": (
                int(intake_report.get("valid_file_count", 0)) == 6
            ),
            "one_closed": (
                int(intake_report.get("closed_request_count", 0)) == 1
            ),
            "two_partial": (
                int(intake_report.get("partial_request_count", 0)) == 2
            ),
            "five_open": (
                int(intake_report.get("open_request_count", 0)) == 5
            ),
            "seven_blockers": (
                int(
                    intake_report.get(
                        "remaining_blocking_input_count",
                        0,
                    )
                )
                == 7
            ),
            "review_complete": bool(
                review_summary.get("concept_review_complete")
            ),
            "scope_140": (
                float(
                    verified_register["scope_basis"][
                        "gross_extension_area_m2"
                    ]
                )
                == 140.0
            ),
        }
        failed = [
            key for key, passed in checks.items() if not passed
        ]
        if failed:
            raise ValueError(
                "Source gate validation failed: "
                + ", ".join(failed)
            )

    @staticmethod
    def _topological_order(
        dependencies: Mapping[str, list[str]],
    ) -> list[str]:
        indegree = {node: 0 for node in dependencies}
        outgoing: dict[str, list[str]] = {
            node: [] for node in dependencies
        }

        for node, prerequisites in dependencies.items():
            for prerequisite in prerequisites:
                if prerequisite not in dependencies:
                    raise ValueError(
                        f"Unknown dependency {prerequisite} for {node}."
                    )
                indegree[node] += 1
                outgoing[prerequisite].append(node)

        queue = deque(sorted(
            node for node, count in indegree.items()
            if count == 0
        ))
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for downstream in sorted(outgoing[node]):
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    queue.append(downstream)

        if len(order) != len(dependencies):
            raise ValueError("Closure dependency graph contains a cycle.")
        return order

    @staticmethod
    def _downstream_map(
        closure_items: list[dict[str, Any]],
    ) -> dict[str, set[str]]:
        direct: dict[str, set[str]] = defaultdict(set)
        for item in closure_items:
            for dependency in item["depends_on"]:
                direct[dependency].add(item["request_id"])

        result: dict[str, set[str]] = {}
        for node in [item["request_id"] for item in closure_items]:
            visited: set[str] = set()
            queue = deque(sorted(direct[node]))
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                queue.extend(sorted(direct[current]))
            result[node] = visited
        return result

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class EvidenceValidationClosurePlanExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        paths: dict[str, Path] = {}
        paths["summary"] = self._write_json(
            root / "01_evidence_validation_summary.json",
            {
                key: value
                for key, value in report.items()
                if key not in {
                    "closure_items",
                    "strategic_decisions",
                }
            },
        )
        paths["closure_plan"] = self._write_json(
            root / "02_evidence_closure_plan.json",
            {
                "closure_items": report["closure_items"],
                "recommended_execution_order": (
                    report["recommended_execution_order"]
                ),
                "critical_path_root": report["critical_path_root"],
                "critical_path_downstream_requests": (
                    report["critical_path_downstream_requests"]
                ),
            },
        )
        paths["closure_matrix"] = self._write_csv(
            root / "03_evidence_closure_matrix.csv",
            report["closure_items"],
            [
                "request_id",
                "input_id",
                "category",
                "title",
                "current_status",
                "priority",
                "closure_authority",
                "lead_party",
                "depends_on",
                "unblocks",
                "closure_status",
                "estimated_external_effort",
            ],
        )
        paths["strategic_decisions"] = self._write_json(
            root / "04_strategic_decision_register.json",
            {
                "status": "PENDING_OWNER_APPROVAL",
                "decision_count": report[
                    "strategic_decision_count"
                ],
                "decisions": report["strategic_decisions"],
            },
        )
        paths["professional_work_orders"] = self._write_csv(
            root / "05_professional_work_orders.csv",
            [
                item for item in report["closure_items"]
                if item["closure_authority"] in {
                    "external_professional",
                    "mixed",
                }
            ],
            [
                "request_id",
                "title",
                "lead_party",
                "supporting_parties",
                "external_deliverables",
                "acceptance_criteria",
                "required_formats",
                "estimated_external_effort",
            ],
        )
        paths["dependency_graph"] = self._write_json(
            root / "06_closure_dependency_graph.json",
            {
                "nodes": [
                    {
                        "request_id": item["request_id"],
                        "priority": item["priority"],
                        "depends_on": item["depends_on"],
                        "unblocks": item["unblocks"],
                    }
                    for item in report["closure_items"]
                ],
                "execution_order": (
                    report["recommended_execution_order"]
                ),
            },
        )
        paths["next_actions"] = self._write_markdown(
            root / "07_next_actions.md",
            self._next_actions_markdown(report),
        )
        paths["dashboard"] = self._write_html(
            root / "08_closure_dashboard.html",
            report,
        )

        package_paths = self._write_closure_packages(
            report,
            root / "closure_packages",
        )
        paths.update(package_paths)

        paths["checksums"] = self._write_checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._write_dossier(
            paths,
            root
            / "BB35_PILOT_1_EVIDENCE_VALIDATION_CLOSURE_PLAN_"
            "v1_5_0.zip",
        )
        return paths

    @staticmethod
    def _write_json(path: Path, value: Any) -> Path:
        path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _write_csv(
        path: Path,
        rows: list[dict[str, Any]],
        fields: list[str],
    ) -> Path:
        with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
                lineterminator="\r\n",
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    field: (
                        json.dumps(
                            row.get(field),
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        if isinstance(
                            row.get(field),
                            (list, dict),
                        )
                        else row.get(field)
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _write_markdown(path: Path, content: str) -> Path:
        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        return path

    @classmethod
    def _write_html(
        cls,
        path: Path,
        report: Mapping[str, Any],
    ) -> Path:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item['request_id'])}</td>"
            f"<td>{html.escape(item['title'])}</td>"
            f"<td>{html.escape(item['priority'])}</td>"
            f"<td>{html.escape(item['closure_authority'])}</td>"
            f"<td>{html.escape(item['lead_party'])}</td>"
            f"<td>{html.escape(item['closure_status'])}</td>"
            "</tr>"
            for item in report["closure_items"]
        )
        content = (
            "<!doctype html><html lang=\"nl\"><head>"
            "<meta charset=\"utf-8\">"
            "<title>BB35 Evidence Validation & Closure Plan</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;max-width:1200px;"
            "margin:32px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:10px}"
            ".status{padding:14px;border:1px solid #9e9e9e;"
            "background:#f5f5f5;margin-bottom:20px}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #bdbdbd;padding:7px;"
            "text-align:left;vertical-align:top}"
            "th{background:#263238;color:#fff}"
            "</style></head><body>"
            "<h1>BB35 Pilot 1 — Evidence Validation & Closure Plan v1.5.0</h1>"
            "<div class=\"status\">"
            f"<strong>Status:</strong> {html.escape(report['status'])}<br>"
            f"<strong>Blokkades:</strong> "
            f"{report['remaining_blocking_input_count']}<br>"
            f"<strong>Strategische besluiten:</strong> "
            f"{report['strategic_decision_count']} pending<br>"
            f"<strong>Professionele werkopdrachten:</strong> "
            f"{report['professional_work_order_count']}<br>"
            f"<strong>Kritieke start:</strong> "
            f"{html.escape(report['critical_path_root'])}<br>"
            "<strong>Definitieve generatie:</strong> geblokkeerd<br>"
            "<strong>BB36:</strong> vergrendeld"
            "</div>"
            "<table><thead><tr>"
            "<th>ID</th><th>Onderwerp</th><th>Prioriteit</th>"
            "<th>Sluitingsbevoegdheid</th><th>Lead</th><th>Status</th>"
            "</tr></thead><tbody>"
            + rows
            + "</tbody></table></body></html>"
        )
        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        return path

    @classmethod
    def _write_closure_packages(
        cls,
        report: Mapping[str, Any],
        root: Path,
    ) -> dict[str, Path]:
        outputs: dict[str, Path] = {}
        decisions = {
            item["decision_id"]: item
            for item in report["strategic_decisions"]
        }

        for item in report["closure_items"]:
            request_root = root / item["request_id"]
            request_root.mkdir(parents=True, exist_ok=True)

            brief = request_root / "closure_brief.md"
            brief.write_text(
                cls._closure_brief(item, decisions),
                encoding="utf-8",
                newline="\n",
            )
            outputs[f"{item['request_id']}_brief"] = brief

            checklist = request_root / "acceptance_checklist.json"
            checklist.write_text(
                json.dumps(
                    {
                        "request_id": item["request_id"],
                        "title": item["title"],
                        "closure_status": item["closure_status"],
                        "acceptance_criteria": [
                            {
                                "criterion_id": (
                                    f"{item['request_id']}-AC-{index:02d}"
                                ),
                                "description": criterion,
                                "status": "PENDING",
                                "evidence_reference": None,
                                "reviewer": None,
                            }
                            for index, criterion in enumerate(
                                item["acceptance_criteria"],
                                start=1,
                            )
                        ],
                        "rejection_conditions": (
                            item["rejection_conditions"]
                        ),
                        "professional_signoff_required": (
                            item["closure_authority"]
                            != "client_strategic_decision"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            outputs[f"{item['request_id']}_checklist"] = checklist

            submission = request_root / "submission_manifest_template.json"
            submission.write_text(
                json.dumps(
                    {
                        "schema_version": (
                            "phoenix.bb35.evidence-submission-manifest/1.0"
                        ),
                        "request_id": item["request_id"],
                        "submission_id": None,
                        "provider_name": None,
                        "provider_role": item["lead_party"],
                        "submission_date": None,
                        "source_files": [],
                        "required_formats": item["required_formats"],
                        "signature": {
                            "signed": False,
                            "signatory": None,
                            "qualification": None,
                        },
                        "verification": {
                            "sha256_complete": False,
                            "acceptance_checklist_complete": False,
                            "accepted": False,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            outputs[f"{item['request_id']}_submission"] = submission

        return outputs

    @staticmethod
    def _closure_brief(
        item: Mapping[str, Any],
        decisions: Mapping[str, Mapping[str, Any]],
    ) -> str:
        lines = [
            f"# {item['request_id']} — {item['title']}",
            "",
            f"**Huidige status:** `{item['current_status']}`",
            f"**Prioriteit:** `{item['priority']}`",
            f"**Lead:** {item['lead_party']}",
            f"**Sluitingsbevoegdheid:** `{item['closure_authority']}`",
            "",
            "## Phoenix voert intern uit",
        ]
        lines.extend(
            f"- {action}" for action in item["internal_actions"]
        )
        lines.extend(["", "## Extern te leveren"])
        lines.extend(
            f"- {deliverable}"
            for deliverable in item["external_deliverables"]
        )

        if item["strategic_decisions"]:
            lines.extend(["", "## Strategische besluiten"])
            for decision_id in item["strategic_decisions"]:
                decision = decisions[decision_id]
                lines.append(
                    f"- `{decision_id}` — {decision['title']}: "
                    f"{decision['question']}"
                )

        lines.extend(["", "## Acceptatiecriteria"])
        lines.extend(
            f"- [ ] {criterion}"
            for criterion in item["acceptance_criteria"]
        )
        lines.extend(["", "## Afkeurcriteria"])
        lines.extend(
            f"- {condition}"
            for condition in item["rejection_conditions"]
        )
        lines.extend([
            "",
            "## Afhankelijkheden",
            (
                "- Geen."
                if not item["depends_on"]
                else "- " + ", ".join(item["depends_on"])
            ),
            "",
            "## Geblokkeerde producten",
            "- " + ", ".join(item["unblocks"]),
            "",
            (
                "**Let op:** dit plan sluit de bewijsaanvraag nog niet. "
                "Sluiting volgt pas na geverifieerd bewijs en vereiste "
                "ondertekening."
            ),
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _next_actions_markdown(
        report: Mapping[str, Any],
    ) -> str:
        return "\n".join([
            "# BB35 Pilot 1 — Eerstvolgende acties",
            "",
            "## 1. Strategische kritieke padbeslissing",
            "",
            (
                "Vul en keur eerst `REQ-107` goed: reguliere bezetting, "
                "vrijdagpiek, bijzondere piek en weekprogramma."
            ),
            "",
            (
                "Deze gegevens zijn de gemeenschappelijke bron voor "
                "brandveiligheid, ventilatie, parkeren en AERIUS."
            ),
            "",
            "## 2. Parallel extern uitzetten",
            "",
            "- REQ-102 — landmeter/CAD-validatie.",
            "- REQ-103 — actuele constructieve opname.",
            "- REQ-104 — geotechnisch onderzoek.",
            "",
            "## 3. Na goedgekeurd REQ-107",
            "",
            "- REQ-105 — Bbl, brand en installaties.",
            "- REQ-106 — parkeerdruk en parkeerbalans.",
            "- REQ-108 — AERIUS aanleg en gebruik.",
            "",
            "## Gate",
            "",
            f"`{report['status']}`",
            "",
            "Definitieve generatie blijft geblokkeerd.",
            "BB36 blijft vergrendeld.",
            "",
        ])

    @staticmethod
    def _write_checksums(
        paths: Mapping[str, Path],
        destination: Path,
    ) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(destination.parent).as_posix()}"
            for key, path in sorted(paths.items())
            if key not in {"checksums", "dossier"}
        ]
        destination.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return destination

    @classmethod
    def _write_dossier(
        cls,
        paths: Mapping[str, Path],
        destination: Path,
    ) -> Path:
        root = destination.parent
        with zipfile.ZipFile(
            destination,
            "w",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            archive.comment = b""
            for key, source in sorted(paths.items()):
                if key == "dossier":
                    continue
                relative = source.relative_to(root).as_posix()
                archive.writestr(
                    cls._canonical_info(relative),
                    source.read_bytes(),
                )
        return destination

    @staticmethod
    def _canonical_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = 20
        info.reserved = 0
        info.flag_bits = 0
        info.volume = 0
        info.internal_attr = 0
        info.external_attr = 0o100644 << 16
        info.extra = b""
        info.comment = b""
        return info
