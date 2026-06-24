from datetime import datetime
from pathlib import Path


class ProjectDrawingPdfWriterEngine:

    def __init__(self):
        self.drawing_pdf_result = {}

    def write_drawing_pdfs(
        self,
        project_result=None,
        storage_result=None,
        drawing_result=None,
        dxf_writer_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        drawing_result = drawing_result or {}
        dxf_writer_result = dxf_writer_result or {}

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        drawings_dir = Path(
            folder_structure.get(
                "drawings",
                project_output_dir / "02_drawings"
            )
        )

        drawings_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        drawing_files = {
            "situatie": drawings_dir / f"{project_id}_situatie.pdf",
            "plattegrond": drawings_dir / f"{project_id}_plattegrond.pdf",
            "doorsnede": drawings_dir / f"{project_id}_doorsnede.pdf"
        }

        written_files = []

        written_files.append(
            self.write_drawing_pdf(
                pdf_path=drawing_files["situatie"],
                title=f"{project_name} - Situatietekening",
                drawing_type="situatie",
                project_result=project_result
            )
        )

        written_files.append(
            self.write_drawing_pdf(
                pdf_path=drawing_files["plattegrond"],
                title=f"{project_name} - Plattegrond",
                drawing_type="plattegrond",
                project_result=project_result
            )
        )

        written_files.append(
            self.write_drawing_pdf(
                pdf_path=drawing_files["doorsnede"],
                title=f"{project_name} - Doorsnede",
                drawing_type="doorsnede",
                project_result=project_result
            )
        )

        self.drawing_pdf_result = {
            "engine": "ProjectDrawingPdfWriterEngine",
            "version": "1.0",
            "status": "PROJECT_DRAWING_PDF_FILES_OPGESLAGEN",
            "calculation_level": "basis PDF tekeningexport",
            "project_id": project_id,
            "project_name": project_name,
            "drawings_dir": str(drawings_dir),
            "written_files": written_files,
            "written_file_count": len(written_files),
            "drawing_engine_status": drawing_result.get("status", "ONBEKEND"),
            "dxf_writer_status": dxf_writer_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(written_files),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Drawing PDF Writer Engine v1.0 maakt eenvoudige schematische "
                "PDF-tekeningen. De tekeningen zijn nog geen officiële maatvaste vergunningstekeningen. "
                "Latere versies moeten schaal, maatvoering, legenda, lagen, stempels en echte geometrie "
                "uit de Digital Twin toevoegen."
            )
        }

        return self.drawing_pdf_result

    def write_drawing_pdf(self, pdf_path, title, drawing_type, project_result):
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            pdf_content = self.build_pdf_content(
                title=title,
                drawing_type=drawing_type,
                project_result=project_result
            )

            with open(pdf_path, "wb") as file:
                file.write(pdf_content)

            return {
                "drawing_type": drawing_type,
                "path": str(pdf_path),
                "status": "OPGESLAGEN",
                "exists": pdf_path.exists(),
                "size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0
            }

        except Exception as error:
            return {
                "drawing_type": drawing_type,
                "path": str(pdf_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_pdf_content(self, title, drawing_type, project_result):
        project_name = project_result.get("project_name", "Onbekend project")
        location = project_result.get("location", "Onbekend")
        country = project_result.get("country", "Onbekend")
        project_type = project_result.get("project_type", "Onbekend")

        drawing_commands = []

        if drawing_type == "situatie":
            drawing_commands.extend(self.situation_pdf_commands())

        elif drawing_type == "plattegrond":
            drawing_commands.extend(self.floorplan_pdf_commands())

        elif drawing_type == "doorsnede":
            drawing_commands.extend(self.section_pdf_commands())

        text_commands = self.title_block_pdf_commands(
            title=title,
            project_name=project_name,
            location=location,
            country=country,
            project_type=project_type
        )

        stream_lines = []

        stream_lines.append("0.8 w")
        stream_lines.append("50 120 495 650 re S")

        stream_lines.extend(drawing_commands)
        stream_lines.extend(text_commands)

        stream = "\n".join(stream_lines).encode("latin-1", errors="replace")

        return self.wrap_pdf_stream(stream)

    def situation_pdf_commands(self):
        return [
            "100 390 360 210 re S",
            "220 455 120 80 re S",
            "90 350 m 470 350 l S",
            "BT /F1 12 Tf 100 330 Td (Schematische situatie / perceel en gebouw) Tj ET",
            "BT /F1 10 Tf 225 495 Td (Gebouw) Tj ET",
            "BT /F1 10 Tf 105 580 Td (Perceelgrens) Tj ET"
        ]

    def floorplan_pdf_commands(self):
        return [
            "120 390 320 210 re S",
            "226 390 m 226 600 l S",
            "333 390 m 333 600 l S",
            "120 495 m 440 495 l S",
            "BT /F1 10 Tf 140 560 Td (Ruimte 1) Tj ET",
            "BT /F1 10 Tf 250 560 Td (Ruimte 2) Tj ET",
            "BT /F1 10 Tf 355 560 Td (Ruimte 3) Tj ET",
            "BT /F1 12 Tf 120 350 Td (Schematische plattegrond) Tj ET"
        ]

    def section_pdf_commands(self):
        return [
            "120 390 m 460 390 l S",
            "150 390 m 150 540 l S",
            "430 390 m 430 540 l S",
            "150 540 m 290 620 l S",
            "290 620 m 430 540 l S",
            "150 470 m 430 470 l S",
            "BT /F1 10 Tf 160 480 Td (Verdieping / constructieniveau) Tj ET",
            "BT /F1 12 Tf 120 350 Td (Schematische doorsnede) Tj ET"
        ]

    def title_block_pdf_commands(
        self,
        title,
        project_name,
        location,
        country,
        project_type
    ):
        title = self.safe_pdf_text(title)
        project_name = self.safe_pdf_text(project_name)
        location = self.safe_pdf_text(location)
        country = self.safe_pdf_text(country)
        project_type = self.safe_pdf_text(project_type)

        return [
            "50 60 495 50 re S",
            f"BT /F1 10 Tf 60 98 Td (Titel: {title}) Tj ET",
            f"BT /F1 10 Tf 60 84 Td (Project: {project_name}) Tj ET",
            f"BT /F1 10 Tf 60 70 Td (Locatie: {location}, {country}) Tj ET",
            f"BT /F1 10 Tf 310 70 Td (Type: {project_type}) Tj ET",
            "BT /F1 9 Tf 410 98 Td (BAOEES V3) Tj ET"
        ]

    def safe_pdf_text(self, text):
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )[:80]

    def wrap_pdf_stream(self, stream):
        objects = []

        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        objects.append(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>\n"
            b"endobj\n"
        )
        objects.append(
            b"4 0 obj\n"
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
            b"endobj\n"
        )
        objects.append(
            b"5 0 obj\n"
            + f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream\nendobj\n"
        )

        pdf = b"%PDF-1.4\n"
        offsets = [0]

        for obj in objects:
            offsets.append(len(pdf))
            pdf += obj

        xref_start = len(pdf)

        pdf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
        pdf += b"0000000000 65535 f \n"

        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n".encode("latin-1")

        pdf += (
            b"trailer\n"
            + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("latin-1")
            + b"startxref\n"
            + f"{xref_start}\n".encode("latin-1")
            + b"%%EOF\n"
        )

        return pdf

    def build_warnings(self, written_files):
        warnings = []

        for file_info in written_files:
            if file_info.get("status") != "OPGESLAGEN":
                warnings.append(
                    f"PDF-tekening niet opgeslagen: {file_info.get('path')}"
                )

        if not warnings:
            warnings.append("Geen kritieke PDF-tekeningexportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_DRAWING_PDF_WRITER_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste PDF-tekeningenlaag. "
                "De volgende stap is om de tekeningen te voeden vanuit echte projectgeometrie "
                "en Digital Twin objecten."
            ),
            "next_steps": [
                "ProjectDrawingPdfWriterEngine koppelen aan BAOEES Core",
                "PDF-tekeningen opnemen in ZIP-export",
                "maatvoering toevoegen",
                "schaal en noordpijl toevoegen",
                "stempelblok professionaliseren",
                "echte geometrie uit Digital Twin gebruiken",
                "per projecttype aparte tekeningsets maken"
            ]
        }

    def get_drawing_pdf_result(self):
        return self.drawing_pdf_result

    def run(self):
        print("Project Drawing PDF Writer Engine actief")