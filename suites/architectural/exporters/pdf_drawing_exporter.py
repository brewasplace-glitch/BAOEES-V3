from pathlib import Path
from datetime import datetime


class ArchitecturalPdfDrawingExporter:
    MODULE_ID = "architectural.export.pdf_drawing_package"
    VERSION = "1.2.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_2/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        try:
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
        except Exception as exc:
            fallback = self.output_dir / "architectural_drawing_package_fallback.md"
            fallback.write_text(
                "# Architectural Drawing Package\n\n"
                "PDF export kon niet worden uitgevoerd omdat reportlab ontbreekt.\n\n"
                f"Fout: {exc}\n",
                encoding="utf-8"
            )
            return {"status": "fallback_markdown", "path": str(fallback)}

        project = result.get("project", {})
        results = result.get("results", {})
        schedule = results.get("space_schedule", {})
        floorplan = results.get("floorplan_generator", {})
        dimensions = results.get("dimensioning", {})

        pdf_path = self.output_dir / "architectural_drawing_package_v1_2.pdf"
        doc = SimpleDocTemplate(str(pdf_path))
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("PROJECT PHOENIX - Architectural Drawing Package v1.2", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Project: {project.get('project_name', '')}", styles["Heading2"]))
        story.append(Paragraph(f"Locatie: {project.get('location', '')}", styles["BodyText"]))
        story.append(Paragraph(f"Gebouwtype: {project.get('building_type', '')}", styles["BodyText"]))
        story.append(Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["BodyText"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Ruimtestaat", styles["Heading2"]))
        table_data = [["Nr", "Bouwlaag", "Ruimte", "Functie", "Opp. m2"]]
        for row in schedule.get("rows", []):
            table_data.append([
                row.get("nr", ""),
                row.get("floor", ""),
                row.get("name", ""),
                row.get("function", ""),
                row.get("area_m2", 0.0)
            ])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        story.append(Paragraph("Schematische plattegrond", styles["Heading2"]))
        for floor, rooms in floorplan.get("floors", {}).items():
            story.append(Paragraph(f"Bouwlaag: {floor}", styles["Heading3"]))
            for room in rooms:
                story.append(Paragraph(
                    f"- {room.get('space', '')}: x={room.get('x')} m, y={room.get('y')} m, "
                    f"b={room.get('width_m')} m, l={room.get('length_m')} m",
                    styles["BodyText"]
                ))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Maatvoering", styles["Heading2"]))
        for dim in dimensions.get("dimensions", []):
            story.append(Paragraph(str(dim), styles["BodyText"]))

        doc.build(story)

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "status": "ok",
            "path": str(pdf_path)
        }
