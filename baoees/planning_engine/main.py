from datetime import datetime, timedelta


class PlanningEngine:

    def __init__(self):
        self.planning_result = {}

    def create_planning(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        reporting_result=None,
        drawing_result=None,
        cad_result=None,
        cost_result=None
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        reporting_result = reporting_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}
        cost_result = cost_result or {}

        project_basis = self.build_project_basis(project_result, cost_result)

        tasks = self.build_tasks(
            project_basis=project_basis,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            reporting_result=reporting_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            cost_result=cost_result
        )

        schedule = self.calculate_schedule(tasks)
        critical_path = self.determine_critical_path(schedule)
        milestones = self.build_milestones(schedule)

        self.planning_result = {
            "engine": "PlanningEngine",
            "version": "1.0",
            "status": "PLANNING_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve projectplanning",
            "project_basis": project_basis,
            "schedule": schedule,
            "milestones": milestones,
            "critical_path": critical_path,
            "total_duration_working_days": self.calculate_total_duration(schedule),
            "recommendation": self.build_recommendation(schedule, critical_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze planning is indicatief. Voor contractuele planning, uitvoering of aanbesteding "
                "moet de planning projectspecifiek worden gecontroleerd met echte beschikbaarheid, "
                "vergunningstermijnen, levertijden en uitvoeringsmethode."
            )
        }

        return self.planning_result

    def build_project_basis(self, project_result, cost_result):
        area = 200.0

        project_basis_from_cost = cost_result.get("project_basis", {})
        if project_basis_from_cost.get("gross_floor_area_m2"):
            area = project_basis_from_cost.get("gross_floor_area_m2")

        try:
            area = float(area)
        except ValueError:
            area = 200.0

        project_type = project_result.get("project_type", "Bouw")

        if area <= 100:
            complexity = "laag"
        elif area <= 500:
            complexity = "middel"
        else:
            complexity = "hoog"

        return {
            "project_type": project_type,
            "gross_floor_area_m2": area,
            "complexity": complexity,
            "planning_start_date": datetime.now().date().isoformat(),
            "calendar": "werkdagen indicatief",
            "status": "AANNAME"
        }

    def build_tasks(
        self,
        project_basis,
        geo_result,
        structural_result,
        permit_result,
        reporting_result,
        drawing_result,
        cad_result,
        cost_result
    ):
        complexity = project_basis["complexity"]

        factor = self.get_complexity_factor(complexity)

        tasks = [
            {
                "id": "T01",
                "name": "Projectstart en intake",
                "phase": "initiatief",
                "duration_days": round(2 * factor),
                "depends_on": [],
                "critical": True
            },
            {
                "id": "T02",
                "name": "Projectanalyse en uitgangspunten",
                "phase": "analyse",
                "duration_days": round(3 * factor),
                "depends_on": ["T01"],
                "critical": True
            },
            {
                "id": "T03",
                "name": "Geotechnische analyse",
                "phase": "engineering",
                "duration_days": self.adjust_duration_for_status(
                    base_days=5 * factor,
                    status=geo_result.get("status"),
                    attention_statuses=["GEO_ANALYSE_GEREED"]
                ),
                "depends_on": ["T02"],
                "critical": True
            },
            {
                "id": "T04",
                "name": "Constructieve analyse",
                "phase": "engineering",
                "duration_days": self.adjust_duration_for_status(
                    base_days=6 * factor,
                    status=structural_result.get("status"),
                    attention_statuses=["STRUCTURAL_ANALYSE_GEREED"]
                ),
                "depends_on": ["T03"],
                "critical": True
            },
            {
                "id": "T05",
                "name": "Ontwerpvarianten beoordelen",
                "phase": "ontwerp",
                "duration_days": round(4 * factor),
                "depends_on": ["T02"],
                "critical": False
            },
            {
                "id": "T06",
                "name": "Vergunningstrategie en ruimtelijke toets",
                "phase": "vergunning",
                "duration_days": self.estimate_permit_duration(permit_result, factor),
                "depends_on": ["T04", "T05"],
                "critical": True
            },
            {
                "id": "T07",
                "name": "Rapportage en onderbouwing",
                "phase": "documentatie",
                "duration_days": self.adjust_duration_for_status(
                    base_days=5 * factor,
                    status=reporting_result.get("status"),
                    attention_statuses=["REPORTING_GEREED"]
                ),
                "depends_on": ["T04", "T06"],
                "critical": True
            },
            {
                "id": "T08",
                "name": "Tekeningen en CAD-export",
                "phase": "tekeningen",
                "duration_days": self.estimate_drawing_duration(drawing_result, cad_result, factor),
                "depends_on": ["T04"],
                "critical": True
            },
            {
                "id": "T09",
                "name": "Kostenraming en budgetcontrole",
                "phase": "kosten",
                "duration_days": self.adjust_duration_for_status(
                    base_days=3 * factor,
                    status=cost_result.get("status"),
                    attention_statuses=["COST_ESTIMATE_GEREED"]
                ),
                "depends_on": ["T04", "T08"],
                "critical": False
            },
            {
                "id": "T10",
                "name": "Vergunningsdossier gereedmaken",
                "phase": "vergunning",
                "duration_days": round(4 * factor),
                "depends_on": ["T07", "T08", "T09"],
                "critical": True
            },
            {
                "id": "T11",
                "name": "Indienen vergunning / formele aanvraag",
                "phase": "vergunning",
                "duration_days": 1,
                "depends_on": ["T10"],
                "critical": True
            },
            {
                "id": "T12",
                "name": "Behandeling vergunning",
                "phase": "vergunning",
                "duration_days": self.estimate_authority_duration(project_basis),
                "depends_on": ["T11"],
                "critical": True
            },
            {
                "id": "T13",
                "name": "Aanbesteding / prijsaanvraag",
                "phase": "aanbesteding",
                "duration_days": round(10 * factor),
                "depends_on": ["T10"],
                "critical": False
            },
            {
                "id": "T14",
                "name": "Werkvoorbereiding",
                "phase": "voorbereiding",
                "duration_days": round(10 * factor),
                "depends_on": ["T12", "T13"],
                "critical": True
            },
            {
                "id": "T15",
                "name": "Uitvoering bouw / civiel werk",
                "phase": "uitvoering",
                "duration_days": self.estimate_execution_duration(project_basis),
                "depends_on": ["T14"],
                "critical": True
            },
            {
                "id": "T16",
                "name": "Controle, oplevering en revisie",
                "phase": "oplevering",
                "duration_days": round(5 * factor),
                "depends_on": ["T15"],
                "critical": True
            }
        ]

        return tasks

    def get_complexity_factor(self, complexity):
        if complexity == "laag":
            return 0.8

        if complexity == "hoog":
            return 1.4

        return 1.0

    def adjust_duration_for_status(self, base_days, status, attention_statuses):
        duration = round(base_days)

        if status in attention_statuses:
            return max(1, duration)

        return duration + 2

    def estimate_permit_duration(self, permit_result, factor):
        base = 8 * factor
        status = permit_result.get("status", "")

        if status == "PERMIT_STRATEGY_GEREED":
            return round(base)

        return round(base + 4)

    def estimate_drawing_duration(self, drawing_result, cad_result, factor):
        base = 8 * factor

        if drawing_result.get("status") == "DRAWING_EXPORT_GEREED":
            base -= 2

        if cad_result.get("status") == "CAD_EXPORT_GEREED":
            base -= 2

        return max(2, round(base))

    def estimate_authority_duration(self, project_basis):
        project_type = str(project_basis.get("project_type", "")).lower()
        complexity = project_basis.get("complexity", "middel")

        if "infra" in project_type:
            base = 70
        elif "civiel" in project_type:
            base = 56
        else:
            base = 56

        if complexity == "hoog":
            base += 28

        if complexity == "laag":
            base -= 14

        return max(28, base)

    def estimate_execution_duration(self, project_basis):
        area = project_basis.get("gross_floor_area_m2", 200.0)
        complexity = project_basis.get("complexity", "middel")

        duration = 30 + area / 10

        if complexity == "hoog":
            duration *= 1.25

        if complexity == "laag":
            duration *= 0.85

        return round(duration)

    def calculate_schedule(self, tasks):
        task_lookup = {task["id"]: task for task in tasks}
        schedule = []
        start_date = datetime.now().date()

        calculated_dates = {}

        for task in tasks:
            depends_on = task.get("depends_on", [])

            if not depends_on:
                task_start = start_date
            else:
                latest_dependency_end = max(
                    calculated_dates[dependency_id]["end_date_obj"]
                    for dependency_id in depends_on
                    if dependency_id in calculated_dates
                )
                task_start = latest_dependency_end + timedelta(days=1)

            duration = max(1, int(task.get("duration_days", 1)))
            task_end = task_start + timedelta(days=duration - 1)

            calculated_dates[task["id"]] = {
                "start_date_obj": task_start,
                "end_date_obj": task_end
            }

            schedule.append({
                "id": task["id"],
                "name": task["name"],
                "phase": task["phase"],
                "duration_days": duration,
                "start_date": task_start.isoformat(),
                "end_date": task_end.isoformat(),
                "depends_on": depends_on,
                "critical": task.get("critical", False),
                "status": "GEPLAND"
            })

        return schedule

    def determine_critical_path(self, schedule):
        critical_tasks = [
            {
                "id": task["id"],
                "name": task["name"],
                "phase": task["phase"],
                "start_date": task["start_date"],
                "end_date": task["end_date"],
                "duration_days": task["duration_days"]
            }
            for task in schedule
            if task.get("critical")
        ]

        return {
            "status": "KRITIEKE_PAD_INDICATIEF",
            "tasks": critical_tasks,
            "note": "Kritieke pad is indicatief bepaald op basis van afhankelijkheden en gemarkeerde hoofdtaken."
        }

    def build_milestones(self, schedule):
        milestone_task_ids = ["T02", "T04", "T10", "T12", "T14", "T15", "T16"]

        milestone_names = {
            "T02": "Projectanalyse gereed",
            "T04": "Technische basisanalyse gereed",
            "T10": "Vergunningsdossier gereed",
            "T12": "Vergunningstraject afgerond indicatief",
            "T14": "Start uitvoering mogelijk",
            "T15": "Uitvoering gereed",
            "T16": "Project opgeleverd"
        }

        milestones = []

        for task in schedule:
            if task["id"] in milestone_task_ids:
                milestones.append({
                    "milestone": milestone_names.get(task["id"], task["name"]),
                    "linked_task": task["id"],
                    "date": task["end_date"],
                    "status": "CONCEPT"
                })

        return milestones

    def calculate_total_duration(self, schedule):
        if not schedule:
            return 0

        start_dates = [
            datetime.fromisoformat(task["start_date"]).date()
            for task in schedule
        ]

        end_dates = [
            datetime.fromisoformat(task["end_date"]).date()
            for task in schedule
        ]

        return (max(end_dates) - min(start_dates)).days + 1

    def build_recommendation(self, schedule, critical_path):
        total_duration = self.calculate_total_duration(schedule)

        if total_duration <= 120:
            planning_risk = "laag"
        elif total_duration <= 220:
            planning_risk = "middel"
        else:
            planning_risk = "hoog"

        return {
            "status": "PLANNINGADVIES_CONCEPT",
            "planning_risk": planning_risk,
            "advice": (
                "Gebruik deze planning als eerste projectplanning. "
                "Werk de planning later uit met echte vergunningstermijnen, leveranciers, uitvoeringsmethode en capaciteit."
            ),
            "next_steps": [
                "planning valideren met opdrachtgever",
                "vergunningstermijnen projectspecifiek controleren",
                "kritieke pad-stappen controleren",
                "aanbestedingsplanning toevoegen",
                "uitvoeringsplanning detailleren",
                "mijlpalen koppelen aan budget en documenten"
            ],
            "critical_task_count": len(critical_path.get("tasks", []))
        }

    def get_planning_result(self):
        return self.planning_result

    def run(self):
        print("Planning Engine actief")