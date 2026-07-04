from pathlib import Path
import argparse
import py_compile
import subprocess


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_structural_calculation_report_engine_connect.py")

IMPORT_LINE = "from baoees.structural_calculation_report_engine.main import StructuralCalculationReportEngine\n"
LABEL = "Structural Reinforcement Engine resultaat:"


REPORT_BLOCK = '''
        try:
            structural_calculation_report_engine = StructuralCalculationReportEngine()
            structural_calculation_report_result = structural_calculation_report_engine.create_structural_calculation_report(
                project_result=project_result,
                building_technical_result=building_technical_result if "building_technical_result" in locals() else {},
                structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                element_load_result=element_load_result if "element_load_result" in locals() else {},
                foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                foundation_design_result=foundation_design_result if "foundation_design_result" in locals() else {},
                foundation_verification_result=foundation_verification_result if "foundation_verification_result" in locals() else {},
                structural_element_sizing_result=structural_element_sizing_result if "structural_element_sizing_result" in locals() else {},
                structural_reinforcement_result=structural_reinforcement_result if "structural_reinforcement_result" in locals() else {}
            )
        except Exception as error:
            structural_calculation_report_result = {
                "engine": "StructuralCalculationReportEngine",
                "status": "STRUCTURAL_CALCULATION_REPORT_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result(
            "Structural Calculation Report Engine resultaat:",
            structural_calculation_report_result
        )

        try:
            self.add_to_digital_twin(
                {},
                "structural_calculation_report",
                structural_calculation_report_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "structural_calculation_report",
                    structural_calculation_report_result
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
    if IMPORT_LINE.strip() in text:
        return text

    lines = text.splitlines(keepends=True)
    last_import_index = None

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_index = index

    if last_import_index is None:
        raise RuntimeError("Geen importsectie gevonden in baoees/core/main.py.")

    lines.insert(last_import_index + 1, IMPORT_LINE)

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
        if LABEL in line:
            label_index = index
            break

    if label_index is None:
        raise RuntimeError(f"Koppelpunt niet gevonden: {LABEL}")

    start_index = find_statement_start(lines, label_index)
    end_index = find_statement_end(lines, start_index)

    return end_index + 1


def add_report_block(text):
    if "structural_calculation_report_result" in text:
        print("Structural Calculation Report Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    lines = text.splitlines(keepends=True)
    insert_index = find_insert_index(lines)
    lines.insert(insert_index, REPORT_BLOCK)

    return "".join(lines)


def compile_tests():
    py_compile.compile(str(CORE_PATH), doraise=True)
    print("PYTHON_COMPILE_OK")


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


def inspect():
    lines = read_core().splitlines()

    print(f"Bestand: {CORE_PATH}")
    print(f"Aantal regels: {len(lines)}")

    label_index = None

    for index, line in enumerate(lines):
        if LABEL in line:
            label_index = index
            break

    if label_index is None:
        print(f"Koppelpunt niet gevonden: {LABEL}")
        return

    start_index = find_statement_start(lines, label_index)
    end_index = find_statement_end(lines, start_index)

    print(f"Koppelpunt labelregel: {label_index + 1}")
    print(f"Print-result startregel: {start_index + 1}")
    print(f"Print-result eindregel: {end_index + 1}")

    start = max(0, start_index - 5)
    end = min(len(lines), end_index + 6)

    print("")
    print("BLOK ROND KOPPELPUNT:")

    for index in range(start, end):
        print(f"{index + 1:04d}: {lines[index]}")


def connect_test():
    make_backup()

    try:
        text = read_core()
        text = add_import(text)
        text = add_report_block(text)
        write_core(text)

        print("STRUCTURAL_CALCULATION_REPORT_ENGINE_GEKKOPPELD_AAN_CORE")

        compile_tests()
        test_baoees()

    except Exception as error:
        print("")
        print("FOUT:")
        print(error)
        rollback()
        run_command("git restore outputs", check=False)
        raise SystemExit(1)


def commit():
    connect_test()

    run_command("git restore outputs", check=False)
    run_command("git add baoees/core/main.py")
    run_command("git add tools_connect_structural_calculation_report_engine_to_core.py")
    run_command('git commit -m "feat: connect Structural Calculation Report Engine to BAOEES Core"')
    run_command("git push")
    cleanup_backup()
    run_command("git status", check=False)


def clean_temp():
    for path in [
        Path("tools_connect_structural_reinforcement_engine_to_core_v2.py"),
        Path("tools_connect_structural_reinforcement_engine_to_core_v3.py"),
        Path("tools_connect_structural_reinforcement_engine_to_core_v4.py"),
        Path("backups/core_main_before_structural_reinforcement_engine_connect_v2.py"),
        Path("backups/core_main_before_structural_reinforcement_engine_connect_v3.py"),
        Path("backups/core_main_before_structural_reinforcement_engine_connect_v4.py"),
        BACKUP_PATH
    ]:
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
            "inspect",
            "connect-test",
            "commit",
            "rollback"
        ]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "clean-temp":
        clean_temp()
    elif args.command == "inspect":
        inspect()
    elif args.command == "connect-test":
        connect_test()
    elif args.command == "commit":
        commit()
    elif args.command == "rollback":
        rollback()


if __name__ == "__main__":
    main()
