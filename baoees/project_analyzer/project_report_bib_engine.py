from datetime import datetime


class ProjectReportBibEngine:

    def __init__(self):
        self.project_report_bib_result = {}

    def create_project_report_bib(
        self,
        project_result=None,
        project_analyzer_result=None,
        aaie_bib_result=None,
        bib_knowledge_result=None,
        report_result=None,
        output_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        project_analyzer_result = project_analyzer_result or {}
        aaie_bib_result = aaie_bib_result or {}
        bib_knowledge_result = bib_knowledge_result or {}
        report_result = report_result or {}
        output_result = output_result or {}

        project_name = project_result.get(
            "project_name",
            project_analyzer_result.get("project_name", "Onbekend project")
        )

        project_id = project_result.get(
            "project_id",
            project_analyzer_result.get("project_id", "unknown_project")
        )

        bib_items = self.collect_bib_items(
            aaie_bib_result=aaie_bib_result,
            bib_knowledge_result=bib_knowledge_result,
            kwargs=kwargs
        )

        report_sections = self.build_report_sections(
            project_name=project_name,
            project_id=project_id,
            bib_items=bib_items
        )

        self.project_report_bib_result = {
            "engine": "ProjectReportBibEngine",
            "version": "1.0",
            "status": "PROJECT_REPORT_BIB_ENGINE_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "bib_item_count": len(bib_items),
            "bib_items": bib_items,
            "report_sections": report_sections,
            "warnings": self.build_warnings(bib_items),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Report BIB Engine koppelt beschikbare BIB-/kennisdata "
                "aan de projectrapportage. Ontbrekende kennisdata wordt veilig als "
                "waarschuwing vastgelegd en blokkeert de projectrun niet."
            )
        }

        return self.project_report_bib_result

    def build_project_report_bib(self, *args, **kwargs):
        return self.create_project_report_bib(*args, **kwargs)

    def generate_project_report_bib(self, *args, **kwargs):
        return self.create_project_report_bib(*args, **kwargs)

    def connect_bib_to_project_report(self, *args, **kwargs):
        return self.create_project_report_bib(*args, **kwargs)

    def create_report_bib(self, *args, **kwargs):
        return self.create_project_report_bib(*args, **kwargs)

    def generate_report_bib(self, *args, **kwargs):
        return self.create_project_report_bib(*args, **kwargs)

    def collect_bib_items(
        self,
        aaie_bib_result=None,
        bib_knowledge_result=None,
        kwargs=None
    ):
        aaie_bib_result = aaie_bib_result or {}
        bib_knowledge_result = bib_knowledge_result or {}
        kwargs = kwargs or {}

        bib_items = []

        self.add_items_from_source(
            bib_items=bib_items,
            source_name="aaie_bib_result",
            source_data=aaie_bib_result
        )

        self.add_items_from_source(
            bib_items=bib_items,
            source_name="bib_knowledge_result",
            source_data=bib_knowledge_result
        )

        for key, value in kwargs.items():
            if "bib" in str(key).lower() or "knowledge" in str(key).lower():
                self.add_items_from_source(
                    bib_items=bib_items,
                    source_name=str(key),
                    source_data=value
                )

        return bib_items

    def add_items_from_source(self, bib_items, source_name, source_data):
        if not source_data:
            return

        if isinstance(source_data, list):
            for item in source_data:
                bib_items.append(
                    self.normalize_bib_item(
                        source_name=source_name,
                        item=item
                    )
                )

            return

        if isinstance(source_data, dict):
            possible_lists = [
                "bib_items",
                "knowledge_items",
                "sources",
                "records",
                "items",
                "assumptions",
                "references"
            ]

            found_list = False

            for key in possible_lists:
                value = source_data.get(key)

                if isinstance(value, list):
                    found_list = True

                    for item in value:
                        bib_items.append(
                            self.normalize_bib_item(
                                source_name=f"{source_name}.{key}",
                                item=item
                            )
                        )

            if not found_list:
                bib_items.append(
                    self.normalize_bib_item(
                        source_name=source_name,
                        item=source_data
                    )
                )

            return

        bib_items.append({
            "source": source_name,
            "type": "tekst",
            "title": str(source_data),
            "description": "",
            "confidence": "onbekend"
        })

    def normalize_bib_item(self, source_name, item):
        if isinstance(item, dict):
            return {
                "source": source_name,
                "type": item.get("type", item.get("category", "kennisitem")),
                "title": item.get("title", item.get("name", item.get("key", "Onbenoemd kennisitem"))),
                "description": item.get("description", item.get("value", item.get("summary", ""))),
                "confidence": item.get("confidence", item.get("reliability", "onbekend")),
                "raw": item
            }

        return {
            "source": source_name,
            "type": "tekst",
            "title": str(item),
            "description": "",
            "confidence": "onbekend",
            "raw": item
        }

    def build_report_sections(self, project_name, project_id, bib_items):
        return [
            {
                "section_id": "bib_project_context",
                "title": "Projectkennis en uitgangspunten",
                "content": (
                    f"Voor project {project_name} ({project_id}) zijn "
                    f"{len(bib_items)} BIB-/kennisitems gekoppeld aan de rapportage."
                )
            },
            {
                "section_id": "bib_traceability",
                "title": "Herleidbaarheid kennisbronnen",
                "content": (
                    "De gekoppelde kennisitems worden gebruikt als projectcontext, "
                    "aannames of broninformatie voor verdere analyse."
                )
            }
        ]

    def build_warnings(self, bib_items):
        warnings = []

        if not bib_items:
            warnings.append(
                "Geen BIB-/kennisitems gevonden. Projectrun gaat door met standaard uitgangspunten."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke BIB-koppelingwaarschuwingen."
            )

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_REPORT_BIB_ADVIES",
            "advice": (
                "Gebruik deze engine als veilige koppellaag tussen BIB-kennis, "
                "AAIE-aannames en projectrapportage. De volgende stap is verdieping "
                "met projectspecifieke bronverwijzingen en rapportparagrafen."
            ),
            "next_steps": [
                "BIB-kennisitems koppelen aan rapporthoofdstukken",
                "bronverwijzingen tonen in PDF/DOCX",
                "AAIE-aannames herleidbaar maken",
                "projectkennis opnemen in Digital Twin",
                "waarschuwingen tonen in dashboard"
            ]
        }

    def get_project_report_bib_result(self):
        return self.project_report_bib_result

    def run(self, *args, **kwargs):
        return self.create_project_report_bib(*args, **kwargs)