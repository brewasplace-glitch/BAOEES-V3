from __future__ import annotations
import csv, hashlib, html, json, zipfile
from pathlib import Path
from typing import Any

_FIXED=(2020,1,1,0,0,0)

class CommercialDeliveryExporter:
    def export_all(self, manifest: dict[str,Any], output_dir: str|Path) -> dict[str,Path]:
        root=Path(output_dir); root.mkdir(parents=True,exist_ok=True)
        paths={
            "manifest":self.export_json(manifest,root/"commercial_building_delivery_manifest.json"),
            "checklist":self.export_csv(manifest,root/"commercial_deliverable_checklist.csv"),
            "readiness":self.export_html(manifest,root/"commercial_delivery_readiness.html"),
        }
        paths["checksums"]=self.export_checksums(paths,root/"checksums.sha256")
        paths["dossier"]=self.export_dossier(manifest,paths,root/"commercial_building_delivery_dossier.zip")
        return paths

    @staticmethod
    def export_json(manifest,path):
        p=Path(path); p.write_text(json.dumps(manifest,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"); return p

    @staticmethod
    def export_csv(manifest,path):
        p=Path(path); fields=["deliverable_type","available","released","revision","file_name","sha256"]
        with p.open("w",encoding="utf-8-sig",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
            for item in manifest["deliverable_checklist"]:
                writer.writerow({k:item.get(k) for k in fields})
        return p

    @staticmethod
    def export_html(manifest,path):
        p=Path(path)
        rows="".join(
            "<tr>"+f"<td>{html.escape(x['deliverable_type'])}</td>"
            +f"<td>{'yes' if x['available'] else 'no'}</td>"
            +f"<td>{'yes' if x['released'] else 'no'}</td>"
            +f"<td>{html.escape(x['revision'])}</td><td>{html.escape(x['file_name'])}</td></tr>"
            for x in manifest["deliverable_checklist"]
        )
        upstream="".join(
            f"<tr><td>{html.escape(x['source'])}</td><td>{'yes' if x['available'] else 'no'}</td>"
            f"<td>{'yes' if x['passed'] else 'no'}</td></tr>"
            for x in manifest["upstream_status"]
        )
        issues="".join(f"<li>{html.escape(x['severity'])}: {html.escape(x['message'])}</li>"
                       for x in manifest["issues"]) or "<li>No blocking issues.</li>"
        p.write_text(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<title>{html.escape(manifest['project_name'])} readiness</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;margin:36px auto;color:#222}"
            "h1{border-bottom:3px solid #222;padding-bottom:8px}.status{padding:14px;background:#f4f4f4;"
            "border:1px solid #aaa}table{border-collapse:collapse;width:100%;margin:16px 0}"
            "th,td{border:1px solid #bbb;padding:7px;text-align:left}th{background:#263238;color:white}</style>"
            "</head><body>"+f"<h1>{html.escape(manifest['project_name'])}</h1>"
            +f"<div class='status'><strong>Status:</strong> {html.escape(manifest['release_status'])}<br>"
            +f"<strong>Commercial package ready:</strong> {'yes' if manifest['commercial_package_ready'] else 'no'}<br>"
            +f"<strong>Blocking issues:</strong> {manifest['blocking_issue_count']}</div>"
            +"<h2>Commercial deliverables</h2><table><tr><th>Deliverable</th><th>Available</th>"
            +"<th>Released</th><th>Revision</th><th>File</th></tr>"+rows+"</table>"
            +"<h2>Upstream engines</h2><table><tr><th>Source</th><th>Available</th><th>Passed</th></tr>"
            +upstream+"</table><h2>Issues</h2><ul>"+issues+"</ul></body></html>",
            encoding="utf-8"
        ); return p

    @staticmethod
    def export_checksums(paths,path):
        p=Path(path)
        p.write_text("\n".join(
            f"{hashlib.sha256(src.read_bytes()).hexdigest()}  {src.name}"
            for key,src in sorted(paths.items()) if key not in {"checksums","dossier"}
        )+"\n",encoding="utf-8"); return p

    def export_dossier(self,manifest,paths,path):
        p=Path(path)
        with zipfile.ZipFile(p,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            for key,src in sorted(paths.items()):
                if key=="dossier": continue
                self._write(archive,src.name,src.read_bytes())
            self._write(archive,"PACKAGE_README.txt",(
                "PROJECT-PHOENIX BB30 COMMERCIAL BUILDING DELIVERY DOSSIER\n"
                f"Project: {manifest['project_name']} ({manifest['project_id']})\n"
                f"Status: {manifest['release_status']}\n"
                "Commercial-pilot readiness package. Professional review and BB31-BB36 remain required.\n"
            ).encode())
        return p

    @staticmethod
    def _write(archive,name,data):
        info=zipfile.ZipInfo(name,_FIXED); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16
        archive.writestr(info,data)
