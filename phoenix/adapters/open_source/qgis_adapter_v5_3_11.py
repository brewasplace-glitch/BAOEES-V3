from pathlib import Path
from typing import Any
from phoenix.adapters.open_source.base import Detection,EngineAdapter,EngineSpec
from phoenix.adapters.open_source.qgis_windows import command_for_launcher,find_qgis_process,probe_version

class QGISWindowsAdapter(EngineAdapter):
    spec=EngineSpec(
        "qgis","QGIS Processing Executor",
        ("qgis_process-qgis-ltr.bat","qgis_process-qgis.bat","qgis_process.exe"),
        ("QGIS_PROCESS_EXE","QGIS_HOME"),
        (".json",".model3",".py",".gpkg",".shp",".geojson",".tif",".tiff"),
        (".gpkg",".shp",".geojson",".tif",".tiff",".csv",".html"),
        "https://docs.qgis.org/3.44/en/docs/user_manual/processing/standalone.html"
    )
    def detect(self):
        launcher=find_qgis_process()
        if launcher is None:
            return Detection("qgis",False,None,"not_found","",[])

        code,out,err=probe_version(launcher)
        lines=(out or err).strip().splitlines()
        notes=[]
        if code!=0:
            notes.append(f"version probe exit code {code}")

        acceptance_path=Path(
            "outputs/runtime/open_source_engines_v5_0_0/"
            "qgis_acceptance/qgis_engine_acceptance.json"
        )
        evidence_available=False
        evidence_version=""
        if acceptance_path.is_file():
            import json
            try:
                evidence=json.loads(acceptance_path.read_text(encoding="utf-8"))
                evidence_available=(
                    evidence.get("status")=="ACCEPTED"
                    and evidence.get("simulated") is False
                    and str(evidence.get("launcher","")).lower()
                        == str(launcher.resolve()).lower()
                    and str(evidence.get("detected_version","")).startswith("3.44.")
                    and evidence.get("acceptance_basis")
                        =="REAL_VALID_GEOPACKAGE_ARTIFACT"
                )
                evidence_version=str(evidence.get("detected_version",""))
                if evidence_available:
                    notes.append("availability confirmed by real accepted GeoPackage evidence")
            except Exception as exc:
                notes.append(f"acceptance evidence unreadable: {exc}")

        available=(code==0) or evidence_available
        version=(
            lines[0][:300]
            if lines
            else (
                f"QGIS {evidence_version} confirmed by acceptance evidence"
                if evidence_version else ""
            )
        )
        return Detection(
            "qgis",
            available,
            str(launcher.resolve()),
            "qgis_windows_launcher",
            version,
            notes,
        )
    def build_command(self,job:dict[str,Any],executable:str):
        algorithm=job.get("algorithm")
        if not algorithm:
            raise ValueError("QGIS job requires algorithm")
        args=["run",str(algorithm),"--"]
        for key in sorted(job.get("parameters",{})):
            args.append(f"{key}={job['parameters'][key]}")
        return command_for_launcher(Path(executable),args)
