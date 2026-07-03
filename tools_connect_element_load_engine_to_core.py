from pathlib import Path
import argparse
import py_compile
import subprocess
import sys


CORE_PATH = Path("baoees/core/main.py")
ELEMENT_PATH = Path("baoees/element_load_engine/main.py")
BACKUP_PATH = Path("backups/core_main_before_element_load_engine_connect.py")

IMPORT_LINE = "from baoees.element_load_engine.main import ElementLoadEngine\n"

ELEMENT_LOAD_BLOCK = '''
        try:
            element_load_engine = ElementLoadEngine()
            element_load_result = element_load_engine.create_element_load_analysis(
                project_result=project_result,
                structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                building_technical_result=building_technical_result if "building_technical_result" in locals() else {},
                geo_result=geo_result if "geo_result" in locals() else {},
                assumptions_result=aaie_result if "aaie_result" in locals() else {}
            )
        except Exception as error:
            element_load_result = {
                "engine": "ElementLoadEngine",
                "status": "ELEMENT_LOAD_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result("Element Load Engine resultaat:", element_load_result)

        try:
            self.add_to_digital_twin(
                {},
                "element_loads",
                element_load_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "element_loads",
                    element_load_result
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


def make_backup():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")

    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(
            CORE_PATH.read_text(encoding="utf-8"),
            encoding="utf-8"
        )

        print(f"Backup gemaakt: {BACKUP_PATH}")
    else:
        print(f"Backup bestond al: {BACKUP_PATH}")


def add_import(text):
    if IMPORT_LINE.strip() in text:
        print("Import bestaat al.")
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
    print("Import toegevoegd.")

    return "".join(lines)


def add_element_load_block(text):
    if "element_load_result" in text:
        print("Element Load Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    marker = '        self.print_result("Permit Engine resultaat:", permit_result)'

    if marker not in text:
        raise RuntimeError(
            "Koppelpunt niet gevonden: Permit Engine resultaat. "
            "Core-structuur wijkt af; handmatige inspectie nodig."
        )

    print("Element Load Engine-blok toegevoegd vóór Permit Engine.")
    return text.replace(marker, ELEMENT_LOAD_BLOCK + marker, 1)


def connect():
    make_backup()

    text = CORE_PATH.read_text(encoding="utf-8")
    text = add_import(text)
    text = add_element_load_block(text)
    CORE_PATH.write_text(text, encoding="utf-8")

    print("")
    print("ELEMENT_LOAD_ENGINE_GEKKOPPELD_AAN_CORE")


def test_python_files():
    py_compile.compile(str(CORE_PATH), doraise=True)
    py_compile.compile(str(ELEMENT_PATH), doraise=True)

    print("")
    print("PYTHON_COMPILE_OK")


def test_baoees():
    result = run_command("python run_baoees_v3.py", check=False)
    run_command("git restore outputs", check=False)

    combined_output = result.stdout + result.stderr

    if "=== PROJECTANALYSE GEREED ===" not in combined_output:
        print("")
        print("BAOEES_TEST_NIET_OK")
        raise SystemExit(1)

    print("")
    print("BAOEES_TEST_OK")

    if "Element Load Engine resultaat" in combined_output:
        print("ELEMENT_LOAD_ENGINE_OUTPUT_GEVONDEN")
    else:
        print("LET OP: PROJECTANALYSE GEREED, maar label Element Load Engine resultaat niet gevonden in console-output.")


def status():
    run_command("git status", check=False)


def connect_test():
    connect()
    test_python_files()
    test_baoees()
    status()


def cleanup_backup():
    if BACKUP_PATH.exists():
        BACKUP_PATH.unlink()
        print(f"Backup verwijderd: {BACKUP_PATH}")


def commit():
    test_python_files()
    test_baoees()
    run_command("git restore outputs", check=False)
    cleanup_backup()

    run_command("git add baoees/core/main.py")
    run_command("git add tools_connect_element_load_engine_to_core.py")
    run_command('git commit -m "feat: connect Element Load Engine to BAOEES Core"')
    run_command("git push")
    status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "connect-test",
            "test",
            "commit",
            "status"
        ]
    )

    args = parser.parse_args()

    if args.command == "connect-test":
        connect_test()
    elif args.command == "test":
        test_python_files()
        test_baoees()
        status()
    elif args.command == "commit":
        commit()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
