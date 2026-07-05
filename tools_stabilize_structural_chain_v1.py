from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_structural_qaqc_engine_connect.py")
STATUS_REPORT_PATH = Path("outputs/structural_chain_stabilization_report.txt")

QAQC_IMPORT_LINE = "from baoees.structural_qaqc_engine.main import StructuralQAQCEngine\n"
QAQC_LABEL = "Structural CAD Export Engine resultaat:"

ENGINE_MODULES = [
    ("Building Technical Engine", "baoees.building_technical_engine.main", "BuildingTechnicalEngine"),
    ("Structural Load Engine", "baoees.structural_load_engine.main", "StructuralLoadEngine"),
    ("Element Load Engine", "baoees.element_load_engine.main", "ElementLoadEngine"),
    ("Foundation Load Transfer Engine", "baoees.foundation_load_transfer_engine.main", "FoundationLoadTransferEngine"),
    ("Foundation Design Engine", "baoees.foundation_design_engine.main", "FoundationDesignEngine"),
    ("Foundation Verification Engine", "baoees.foundation_verification_engine.main", "FoundationVerificationEngine"),
    ("Structural Element Sizing Engine", "baoees.structural_element_sizing_engine.main", "StructuralElementSizingEngine"),
    ("Structural Reinforcement Engine", "baoees.structural_reinforcement_engine.main", "StructuralReinforcementEngine"),
    ("Structural Calculation Report Engine", "baoees.structural_calculation_report_engine.main", "StructuralCalculationReportEngine"),
    ("Structural Drawing Package Engine", "baoees.structural_drawing_package_engine.main", "StructuralDrawingPackageEngine"),
    ("Structural CAD Export Engine", "baoees.structural_cad_export_engine.main", "StructuralCADExportEngine"),
    ("Structural QAQC Engine", "baoees.structural_qaqc_engine.main", "StructuralQAQCEngine"),
]

CORE_LABELS = [
    "Building Technical Engine resultaat:",
    "Structural Load Engine resultaat:",
    "Element Load Engine resultaat:",
    "Foundation Load Transfer Engine resultaat:",
    "Foundation Design Engine resultaat:",
    "Foundation Verification Engine resultaat:",
    "Structural Element Sizing Engine resultaat:",
    "Structural Reinforcement Engine resultaat:",
    "Structural Calculation Report Engine resultaat:",
    "Structural Drawing Package Engine resultaat:",
    "Structural CAD Export Engine resultaat:",
    "Structural QAQC Engine resultaat:",
]

QAQC_BLOCK = '''
        try:
            structural_qaqc_engine = StructuralQAQCEngine()
            structural_qaqc_result = structural_qaqc_engine.create_structural_qaqc_review(
                project_result=project_result,
                building_technical_result=building_technical_result if "building_technical_result" in locals() else {},
                structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                element_load_result=element_load_result if "element_load_result" in locals() else {},
                foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                foundation_design_result=foundation_design_result if "foundation_design_result" in locals() else {},
                foundation_verification_result=foundation_verification_result if "foundation_verification_result" in locals() else {},
                structural_element_sizing_result=structural_element_sizing_result if "structural_element_sizing_result" in locals() else {},
                structural_reinforcement_result=structural_reinforcement_result if "structural_reinforcement_result" in locals() else {},
                structural_calculation_report_result=structural_calculation_report_result if "structural_calculation_report_result" in locals() else {},
                structural_drawing_package_result=structural_drawing_package_result if "structural_drawing_package_result" in locals() else {},
                structural_cad_export_result=structural_cad_export_result if "structural_cad_export_result" in locals() else {}
            )
        except Exception as error:
            structural_qaqc_result = {
                "engine": "StructuralQAQCEngine",
                "status": "STRUCTURAL_QAQC_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result(
            "Structural QAQC Engine resultaat:",
            structural_qaqc_result
        )

        try:
            self.add_to_digital_twin(
                {},
                "structural_qaqc_review",
                structural_qaqc_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "structural_qaqc_review",
                    structural_qaqc_result
                )
            except TypeError:
                pass

'''


def run_command(command, check=True):
    print("")
    print(f">> {command}")

    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if check and result.returncode != 0:
        raise SystemExit(result.returncode)

    return result


def read_core():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")

    return CORE_PATH.read_text(encoding="utf-8")


def write_core(text):
    CORE_PATH.write_text(text, encoding="utf-8")


def make_backup():
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_PATH.write_text(read_core(), encoding="utf-8")
    print(f"Backup gemaakt: {BACKUP_PATH}")


def rollback():
    if BACKUP_PATH.exists():
        CORE_PATH.write_text(
            BACKUP_PATH.read_text(encoding="utf-8"),
            encoding="utf-8"
        )
        print(f"Rollback uitgevoerd vanuit: {BACKUP_PATH}")
    else:
        print(f"Geen backup gevonden: {BACKUP_PATH}")


def cleanup_backup():
    if BACKUP_PATH.exists():
        BACKUP_PATH.unlink()
        print(f"Backup verwijderd: {BACKUP_PATH}")


def add_import(text):
    if QAQC_IMPORT_LINE.strip() in text:
        return text

    lines = text.splitlines(keepends=True)
    last_import_index = None

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_index = index

    if last_import_index is None:
        raise RuntimeError("Geen importsectie gevonden in baoees/core/main.py.")

    lines.insert(last_import_index + 1, QAQC_IMPORT_LINE)

    return "".join(lines)


def find_statement_start(lines, label_index):
    for index in range(label_index, max(label_index - 12, -1), -1):
        if "self.print_result" in lines[index]:
            return index

    raise RuntimeError("Start van self.print_result niet gevonden boven labelregel.")


def find_statement_end(lines, start_index):
    paren_balance = 0
    seen_open = False

    for index in range(start_index, len(lines)):
        line = lines[index]

        for char in line:
            if char == "(":
                paren_balance += 1
                seen_open = True
            elif char == ")":
                paren_balance -= 1

        if seen_open and paren_balance <= 0:
            return index

    raise RuntimeError("Einde van self.print_result niet gevonden.")


def find_insert_index(lines):
    label_index = None

    for index, line in enumerate(lines):
        if QAQC_LABEL in line:
            label_index = index
            break

    if label_index is None:
        raise RuntimeError(f"Koppelpunt niet gevonden: {QAQC_LABEL}")

    start_index = find_statement_start(lines, label_index)
    end_index = find_statement_end(lines, start_index)

    return end_index + 1


def add_qaqc_block(text):
    if "structural_qaqc_result" in text:
        print("Structural QAQC Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    lines = text.splitlines(keepends=True)
    insert_index = find_insert_index(lines)
    lines.insert(insert_index, QAQC_BLOCK)

    return "".join(lines)


def compile_core():
    py_compile.compile(str(CORE_PATH), doraise=True)
    print("CORE_PYTHON_COMPILE_OK")


def test_baoees():
    result = run_command("python run_baoees_v3.py", check=False)
    run_command("git restore outputs", check=False)

    combined_output = result.stdout + result.stderr

    if "=== PROJECTANALYSE GEREED ===" not in combined_output:
        print("")
        print("BAOEES_TEST_NIET_OK")
        raise RuntimeError("BAOEES-run eindigde niet met PROJECTANALYSE GEREED.")

    print("")
    print("BAOEES_TEST_OK")


def import_engine(module_path, class_name):
    module = importlib.import_module(module_path)
    engine_class = getattr(module, class_name)
    return engine_class


def test_imports():
    print("")
    print("ENGINE_IMPORT_TESTS")

    results = []

    for display_name, module_path, class_name in ENGINE_MODULES:
        try:
            engine_class = import_engine(module_path, class_name)
            status = "OK"
            message = str(engine_class)
        except Exception as error:
            status = "FOUT"
            message = str(error)

        results.append(
            {
                "engine": display_name,
                "module": module_path,
                "class": class_name,
                "status": status,
                "message": message
            }
        )

        print(f"- {display_name}: {status}")

        if status != "OK":
            print(f"  {message}")

    return results


def inspect_core():
    text = read_core()
    lines = text.splitlines()

    print("")
    print("CORE_KOPPELINGEN")

    label_results = []

    for label in CORE_LABELS:
        found_lines = []

        for index, line in enumerate(lines, start=1):
            if label in line:
                found_lines.append(index)

        status = "GEVONDEN" if found_lines else "ONTBREEKT"

        label_results.append(
            {
                "label": label,
                "status": status,
                "lines": found_lines
            }
        )

        if found_lines:
            print(f"- {label} {status} op regel(s): {found_lines}")
        else:
            print(f"- {label} {status}")

    return label_results


def inspect_qaqc_insert_point():
    lines = read_core().splitlines()

    label_index = None

    for index, line in enumerate(lines):
        if QAQC_LABEL in line:
            label_index = index
            break

    if label_index is None:
        print("")
        print(f"QAQC-koppelpunt niet gevonden: {QAQC_LABEL}")
        return None

    start_index = find_statement_start(lines, label_index)
    end_index = find_statement_end(lines, start_index)

    print("")
    print("QAQC_KOPPELPUNT")
    print(f"Labelregel: {label_index + 1}")
    print(f"Print-result startregel: {start_index + 1}")
    print(f"Print-result eindregel: {end_index + 1}")

    start = max(0, start_index - 4)
    end = min(len(lines), end_index + 5)

    print("")
    print("BLOK ROND QAQC-KOPPELPUNT:")

    for index in range(start, end):
        print(f"{index + 1:04d}: {lines[index]}")

    return {
        "label_line": label_index + 1,
        "start_line": start_index + 1,
        "end_line": end_index + 1
    }


def write_report(import_results, label_results):
    STATUS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("STRUCTURAL CHAIN STABILIZATION REPORT")
    lines.append("=" * 45)
    lines.append("")
    lines.append("ENGINE IMPORTS")

    for item in import_results:
        lines.append(f"- {item['engine']}: {item['status']}")
        if item["status"] != "OK":
            lines.append(f"  {item['message']}")

    lines.append("")
    lines.append("CORE LABELS")

    for item in label_results:
        lines.append(f"- {item['label']}: {item['status']} {item['lines']}")

    STATUS_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("")
    print(f"Rapport geschreven: {STATUS_REPORT_PATH}")


def audit():
    run_command("git restore outputs", check=False)
    compile_core()
    import_results = test_imports()
    label_results = inspect_core()
    inspect_qaqc_insert_point()
    write_report(import_results, label_results)


def connect_qaqc_test():
    make_backup()

    try:
        text = read_core()
        text = add_import(text)
        text = add_qaqc_block(text)
        write_core(text)

        print("STRUCTURAL_QAQC_ENGINE_GEKKOPPELD_AAN_CORE")

        compile_core()
        test_baoees()

    except Exception as error:
        print("")
        print("FOUT:")
        print(error)
        rollback()
        run_command("git restore outputs", check=False)
        raise SystemExit(1)


def commit():
    audit()
    connect_qaqc_test()

    run_command("git restore outputs", check=False)
    run_command("git add baoees/core/main.py")
    run_command("git add tools_stabilize_structural_chain_v1.py")
    run_command("git add outputs/structural_chain_stabilization_report.txt")
    run_command('git commit -m "feat: stabilize structural chain and connect QAQC engine"')
    run_command("git push")
    cleanup_backup()
    run_command("git status", check=False)


def clean_temp():
    temp_files = [
        BACKUP_PATH,
        Path("backups/core_main_before_structural_qaqc_engine_connect_v1.py"),
        Path("tools_connect_structural_qaqc_engine_to_core.py"),
    ]

    for path in temp_files:
        if path.exists():
            path.unlink()
            print(f"Verwijderd: {path}")

    run_command("git restore outputs", check=False)


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "status",
            "clean-temp",
            "audit",
            "connect-qaqc-test",
            "test-baoees",
            "commit",
            "rollback"
        ]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "clean-temp":
        clean_temp()
    elif args.command == "audit":
        audit()
    elif args.command == "connect-qaqc-test":
        connect_qaqc_test()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "commit":
        commit()
    elif args.command == "rollback":
        rollback()


if __name__ == "__main__":
    main()
