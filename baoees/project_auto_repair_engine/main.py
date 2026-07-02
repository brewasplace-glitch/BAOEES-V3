import json
from datetime import datetime
from pathlib import Path


class ProjectAutoRepairEngine:

    def __init__(self):
        self.repair_result = {}

    def run_auto_repair(
        self,
        error_reports_dir="outputs/runtime_errors",
        repair_output_dir="outputs/auto_repairs",
        apply_safe_repairs=True
    ):
        error_reports_dir = Path(error_reports_dir)
        repair_output_dir = Path(repair_output_dir)

        repair_output_dir.mkdir(parents=True, exist_ok=True)

        latest_error_report = self.find_latest_error_report(
            error_reports_dir=error_reports_dir
        )

        if not latest_error_report:
            self.repair_result = {
                "engine": "ProjectAutoRepairEngine",
                "version": "1.0",
                "status": "GEEN_FOUTRAPPORT_GEVONDEN",
                "message": "Er is geen foutdiagnose gevonden in outputs/runtime_errors.",
                "created_at": datetime.now().isoformat(timespec="seconds")
            }

            return self.repair_result

        repair_plan = self.build_repair_plan(
            error_report=latest_error_report,
            apply_safe_repairs=apply_safe_repairs
        )

        repair_actions_result = self.execute_repair_plan(
            repair_plan=repair_plan,
            apply_safe_repairs=apply_safe_repairs
        )

        repair_id = self.create_repair_id(
            error_id=latest_error_report.get("error_id", "unknown_error")
        )

        repair_json_path = repair_output_dir / f"{repair_id}.json"
        repair_txt_path = repair_output_dir / f"{repair_id}.txt"

        report_data = {
            "engine": "ProjectAutoRepairEngine",
            "version": "1.0",
            "status": "AUTO_REPAIR_PLAN_OPGESLAGEN",
            "repair_id": repair_id,
            "apply_safe_repairs": apply_safe_repairs,
            "source_error_id": latest_error_report.get("error_id", "ONBEKEND"),
            "source_error_type": latest_error_report.get("error_type", "ONBEKEND"),
            "source_error_message": latest_error_report.get("error_message", "ONBEKEND"),
            "repair_plan": repair_plan,
            "repair_actions_result": repair_actions_result,
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        json_report = self.write_json_file(
            file_path=repair_json_path,
            data=report_data
        )

        text_report = self.write_text_file(
            file_path=repair_txt_path,
            content=self.build_text_report(report_data)
        )

        report_data["json_report"] = json_report
        report_data["text_report"] = text_report

        self.repair_result = report_data

        self.print_console_report(self.repair_result)

        return self.repair_result

    def find_latest_error_report(self, error_reports_dir):
        error_reports_dir = Path(error_reports_dir)

        if not error_reports_dir.exists():
            return None

        json_files = sorted(
            error_reports_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True
        )

        for json_file in json_files:
            data = self.read_json_file(json_file)

            if isinstance(data, dict) and data.get("error_id"):
                return data

        return None

    def build_repair_plan(self, error_report, apply_safe_repairs):
        error_type = error_report.get("error_type", "")
        error_message = error_report.get("error_message", "")
        message_lower = str(error_message).lower()

        repair_plan = {
            "status": "REPAIR_PLAN_CREATED",
            "error_type": error_type,
            "error_message": error_message,
            "apply_safe_repairs": apply_safe_repairs,
            "confidence": "laag",
            "safe_auto_repairs": [],
            "manual_repairs": [],
            "blocked_repairs": [],
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        if error_type == "ModuleNotFoundError" or "no module named" in message_lower:
            return self.plan_module_not_found_repair(
                repair_plan=repair_plan,
                error_message=error_message
            )

        if error_type == "ImportError" or "cannot import name" in message_lower:
            return self.plan_import_error_repair(
                repair_plan=repair_plan
            )

        if "unexpected keyword argument" in message_lower:
            return self.plan_unexpected_keyword_repair(
                repair_plan=repair_plan,
                error_message=error_message
            )

        repair_plan["manual_repairs"].append({
            "action": "HANDMATIGE_ANALYSE_NODIG",
            "reason": "Dit fouttype is nog niet veilig automatisch te repareren.",
            "recommended_step": (
                "Gebruik de foutdiagnose en maak daarna een gecontroleerde "
                "volledige bestandsvervanging."
            )
        })

        return repair_plan

    def plan_module_not_found_repair(self, repair_plan, error_message):
        missing_module = self.extract_missing_module_name(error_message)

        repair_plan["confidence"] = "middel"

        repair_plan["safe_auto_repairs"].append({
            "action": "CONTROLEER_MODULEPAD",
            "module": missing_module,
            "description": "Controleer of de modulemap bestaat."
        })

        if str(missing_module).startswith("baoees."):
            relative_module_path = str(missing_module).replace(".", "/")
            folder_path = Path(relative_module_path)

            repair_plan["safe_auto_repairs"].append({
                "action": "MAAK_MODULEMAP_INDIEN_ONTBREEKT",
                "path": str(folder_path),
                "description": "Maak de ontbrekende modulemap aan als deze nog niet bestaat."
            })

            repair_plan["safe_auto_repairs"].append({
                "action": "MAAK_INIT_PY_INDIEN_ONTBREEKT",
                "path": str(folder_path / "__init__.py"),
                "description": "Maak een lege __init__.py aan als deze ontbreekt."
            })

            repair_plan["manual_repairs"].append({
                "action": "MAIN_PY_CONTROLEREN",
                "path": str(folder_path / "main.py"),
                "reason": (
                    "main.py kan niet inhoudelijk veilig worden gegenereerd "
                    "zonder te weten welke class erin hoort."
                )
            })

        return repair_plan

    def plan_import_error_repair(self, repair_plan):
        repair_plan["confidence"] = "middel"

        repair_plan["manual_repairs"].append({
            "action": "CONTROLEER_CLASSNAAM",
            "reason": "De classnaam in main.py komt waarschijnlijk niet overeen met de import.",
            "recommended_step": (
                "Open __init__.py en main.py en controleer of dezelfde "
                "classnaam wordt gebruikt."
            )
        })

        repair_plan["manual_repairs"].append({
            "action": "VOLLEDIGE_ENGINE_MAIN_PY_VERVANGEN",
            "reason": (
                "Bij ImportError is volledige bestandsvervanging veiliger "
                "dan automatisch gokken."
            )
        })

        return repair_plan

    def plan_unexpected_keyword_repair(self, repair_plan, error_message):
        keyword = self.extract_unexpected_keyword(error_message)

        repair_plan["confidence"] = "middel"

        repair_plan["manual_repairs"].append({
            "action": "FUNCTIEKOP_AANPASSEN",
            "keyword": keyword,
            "reason": "De functie accepteert het meegegeven argument nog niet.",
            "recommended_step": (
                "Open de genoemde engine-main.py en voeg het ontbrekende "
                "argument toe."
            )
        })

        repair_plan["blocked_repairs"].append({
            "action": "NIET_AUTOMATISCH_FUNCTIE_HERSCHRIJVEN",
            "reason": "Automatisch herschrijven van functiekoppen kan goede code beschadigen."
        })

        return repair_plan

    def execute_repair_plan(self, repair_plan, apply_safe_repairs):
        actions = []

        if not apply_safe_repairs:
            return {
                "status": "DRY_RUN_GEEN_REPARATIES_UITGEVOERD",
                "actions": actions
            }

        for action in repair_plan.get("safe_auto_repairs", []):
            action_type = action.get("action")

            if action_type == "MAAK_MODULEMAP_INDIEN_ONTBREEKT":
                actions.append(
                    self.safe_create_folder(action.get("path"))
                )

            elif action_type == "MAAK_INIT_PY_INDIEN_ONTBREEKT":
                actions.append(
                    self.safe_create_init_file(action.get("path"))
                )

            else:
                actions.append({
                    "action": action_type,
                    "status": "GEEN_SCHRIJFACTIE_NODIG",
                    "description": action.get("description", "")
                })

        return {
            "status": "SAFE_REPAIRS_UITGEVOERD",
            "actions": actions
        }

    def safe_create_folder(self, folder_path):
        folder_path = Path(folder_path)

        try:
            folder_path.mkdir(parents=True, exist_ok=True)

            return {
                "action": "MAAK_MODULEMAP_INDIEN_ONTBREEKT",
                "path": str(folder_path),
                "status": "OK",
                "exists": folder_path.exists()
            }

        except Exception as error:
            return {
                "action": "MAAK_MODULEMAP_INDIEN_ONTBREEKT",
                "path": str(folder_path),
                "status": "FOUT",
                "error": str(error)
            }

    def safe_create_init_file(self, file_path):
        file_path = Path(file_path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if not file_path.exists():
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("")

            return {
                "action": "MAAK_INIT_PY_INDIEN_ONTBREEKT",
                "path": str(file_path),
                "status": "OK",
                "exists": file_path.exists()
            }

        except Exception as error:
            return {
                "action": "MAAK_INIT_PY_INDIEN_ONTBREEKT",
                "path": str(file_path),
                "status": "FOUT",
                "error": str(error)
            }

    def extract_missing_module_name(self, error_message):
        text = str(error_message)

        if "No module named" in text:
            parts = text.split("No module named")

            if len(parts) > 1:
                return parts[1].strip().strip("'").strip('"')

        return "ONBEKEND"

    def extract_unexpected_keyword(self, error_message):
        text = str(error_message)
        marker = "unexpected keyword argument"

        if marker in text:
            parts = text.split(marker)

            if len(parts) > 1:
                return parts[1].strip().strip("'").strip('"')

        return "ONBEKEND"

    def create_repair_id(self, error_id):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        safe_error_id = "".join(
            character if character.isalnum() else "_"
            for character in str(error_id)
        )

        return f"baoees_repair_{stamp}_{safe_error_id}"

    def read_json_file(self, file_path):
        file_path = Path(file_path)

        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)

        except Exception:
            return {}

    def write_json_file(self, file_path, data):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def write_text_file(self, file_path, content):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_text_report(self, repair_result):
        repair_plan = repair_result.get("repair_plan", {})
        repair_actions_result = repair_result.get("repair_actions_result", {})

        return f"""BAOEES AUTO REPAIR RAPPORT
=========================

Repair ID:
{repair_result.get("repair_id", "ONBEKEND")}

Bronfout:
{repair_result.get("source_error_id", "ONBEKEND")}

Fouttype:
{repair_result.get("source_error_type", "ONBEKEND")}

Foutmelding:
{repair_result.get("source_error_message", "ONBEKEND")}

Confidence:
{repair_plan.get("confidence", "ONBEKEND")}

Status reparatieplan:
{repair_plan.get("status", "ONBEKEND")}

Status uitgevoerde acties:
{repair_actions_result.get("status", "ONBEKEND")}

Let op:
Deze engine voert alleen veilige automatische reparaties uit.
Grote codewijzigingen blijven handmatig akkoord nodig hebben.
"""

    def print_console_report(self, repair_result):
        print("")
        print("====================================================")
        print("BAOEES AUTO REPAIR ENGINE")
        print("====================================================")
        print(f"Status: {repair_result.get('status')}")
        print(f"Repair ID: {repair_result.get('repair_id')}")
        print(f"Bronfout: {repair_result.get('source_error_id')}")
        print(f"Fouttype: {repair_result.get('source_error_type')}")
        print("")
        print("Reparatierapport opgeslagen in:")
        print("outputs/auto_repairs")
        print("====================================================")
        print("")

    def get_repair_result(self):
        return self.repair_result

    def run(self):
        print("Project Auto Repair Engine actief")