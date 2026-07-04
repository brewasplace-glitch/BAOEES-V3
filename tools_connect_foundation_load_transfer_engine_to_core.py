from pathlib import Path
import argparse
import py_compile
import subprocess


CORE_PATH = Path("baoees/core/main.py")
FOUNDATION_MAIN = Path("baoees/foundation_load_transfer_engine/main.py")
BACKUP_PATH = Path("backups/core_main_before_foundation_load_transfer_engine_connect.py")

IMPORT_LINE = "from baoees.foundation_load_transfer_engine.main import FoundationLoadTransferEngine\n"

FOUNDATION_BLOCK = '''

        try:
            foundation_load_transfer_engine = FoundationLoadTransferEngine()

            if hasattr(foundation_load_transfer_engine, "create_foundation_load_transfer_analysis"):
                foundation_load_transfer_result = foundation_load_transfer_engine.create_foundation_load_transfer_analysis(
                    project_result=project_result if "project_result" in locals() else {},
                    structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                    element_load_result=element_load_result if "element_load_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            elif hasattr(foundation_load_transfer_engine, "create_foundation_load_analysis"):
                foundation_load_transfer_result = foundation_load_transfer_engine.create_foundation_load_analysis(
                    project_result=project_result if "project_result" in locals() else {},
                    structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                    element_load_result=element_load_result if "element_load_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            elif hasattr(foundation_load_transfer_engine, "run"):
                foundation_load_transfer_result = foundation_load_transfer_engine.run(
                    project_result=project_result if "project_result" in locals() else {},
                    structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                    element_load_result=element_load_result if "element_load_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            else:
                foundation_load_transfer_result = {
                    "engine": "FoundationLoadTransferEngine",
                    "status": "FOUNDATION_LOAD_TRANSFER_ENGINE_METHOD_NOT_FOUND"
                }
        except Exception as error:
            foundation_load_transfer_result = {
                "engine": "FoundationLoadTransferEngine",
                "status": "FOUNDATION_LOAD_TRANSFER_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result("Foundation Load Transfer Engine resultaat:", foundation_load_transfer_result)

        try:
            self.add_to_digital_twin(
                {},
                "foundation_load_transfer",
                foundation_load_transfer_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "foundation_load_transfer",
                    foundation_load_transfer_result
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
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup gemaakt: {BACKUP_PATH}")


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


def add_foundation_block(text):
    if "foundation_load_transfer_result" in text:
        print("Foundation Load Transfer Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    marker_options = [
        '        self.print_result("Element Load Engine resultaat:", element_load_result)',
        '        self.print_result("Structural Load Engine resultaat:", structural_load_result)',
        '        self.print_result("Permit Engine resultaat:", permit_result)'
    ]

    for marker in marker_options:
        if marker in text:
            return text.replace(marker, marker + FOUNDATION_BLOCK, 1)

    raise RuntimeError(
        "Geen geschikt koppelpunt gevonden. Controleer of Element Load Engine of Structural Load Engine in core/main.py staat."
    )


def connect():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")

    if not FOUNDATION_MAIN.exists():
        raise FileNotFoundError(f"Niet gevonden: {FOUNDATION_MAIN}")

    make_backup()

    text = CORE_PATH.read_text(encoding="utf-8")
    text = add_import(text)
    text = add_foundation_block(text)
    CORE_PATH.write_text(text, encoding="utf-8")

    print("")
    print("FOUNDATION_LOAD_TRANSFER_ENGINE_GEKKOPPELD_AAN_CORE")
    print(f"Aangepast: {CORE_PATH}")


def compile_check():
    py_compile.compile(str(CORE_PATH), doraise=True)
    py_compile.compile(str(FOUNDATION_MAIN), doraise=True)
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


def connect_test():
    connect()
    compile_check()
    test_baoees()
    status()


def clean_backups():
    if BACKUP_PATH.exists():
        BACKUP_PATH.unlink()
        print(f"Backup verwijderd: {BACKUP_PATH}")


def commit():
    compile_check()
    test_baoees()
    run_command("git restore outputs", check=False)
    clean_backups()
    run_command("git add baoees/core/main.py")
    run_command("git add tools_connect_foundation_load_transfer_engine_to_core.py")
    run_command('git commit -m "feat: connect Foundation Load Transfer Engine to BAOEES Core"')
    run_command("git push")
    status()


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["status", "connect", "connect-test", "compile", "test-baoees", "commit"]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "connect":
        connect()
    elif args.command == "connect-test":
        connect_test()
    elif args.command == "compile":
        compile_check()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "commit":
        commit()


if __name__ == "__main__":
    main()
