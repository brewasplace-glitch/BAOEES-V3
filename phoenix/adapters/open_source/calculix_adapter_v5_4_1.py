from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from phoenix.adapters.open_source.base import Detection, EngineAdapter, EngineSpec
from phoenix.adapters.open_source.calculix_windows import find_calculix_ccx

class CalculiXWindowsAdapter(EngineAdapter):
    spec = EngineSpec(
        "calculix",
        "CalculiX CrunchiX",
        ("ccx.exe", "ccx_static.exe", "ccx_2.23.exe", "ccx_2.23_MT.exe"),
        ("CALCULIX_CCX_EXE", "CALCULIX_HOME"),
        (".inp",),
        (".dat", ".frd", ".sta", ".cvg"),
        "https://dhondt.de/",
    )

    def detect(self) -> Detection:
        executable = find_calculix_ccx()
        if executable is None:
            return Detection("calculix", False, None, "not_found", "", [])

        notes: list[str] = []
        evidence_path = Path(
            "outputs/runtime/open_source_engines_v5_0_0/"
            "calculix_acceptance/calculix_engine_acceptance.json"
        )
        accepted = False
        version = ""
        if evidence_path.is_file():
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                accepted = (
                    evidence.get("status") == "ACCEPTED"
                    and evidence.get("simulated") is False
                    and str(evidence.get("executable", "")).lower()
                        == str(executable.resolve()).lower()
                    and str(evidence.get("version", "")).startswith("2.23")
                    and evidence.get("windows_binary_provider") == "MSYS2"
                    and evidence.get("acceptance_basis")
                        == "REAL_CCX_DAT_FRD_ARTIFACTS"
                )
                version = str(evidence.get("version", ""))
                if accepted:
                    notes.append(
                        "availability confirmed by real accepted DAT/FRD evidence"
                    )
            except Exception as exc:
                notes.append(f"acceptance evidence unreadable: {exc}")

        return Detection(
            "calculix",
            accepted,
            str(executable.resolve()),
            "calculix_windows_executable",
            f"CalculiX {version}" if version else "",
            notes if accepted else notes + ["real acceptance evidence required"],
        )

    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        model_stem = job.get("model_stem")
        if not model_stem:
            raise ValueError("CalculiX job requires model_stem")
        return [executable, str(model_stem)]
