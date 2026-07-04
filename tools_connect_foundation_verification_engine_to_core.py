from pathlib import Path
import argparse
import subprocess
import sys

CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_foundation_verification_engine_connect.py")

IMPORT_LINE = "from baoees.foundation_verification_engine.main import FoundationVerificationEngine\n"

PERMIT_MARKER = '        self.print_result("Permit Engine resultaat:", permit_result)'

FOUNDATION_VERIFICATION_BLOCK = r'''
        try:
            foundation_verification_engine = FoundationVerificationEngine()

            if hasattr(foundation_verification_engine, "create_foundation_verification_analysis"):
                foundation_verification_result = foundation_verification_engine.create_foundation_verification_analysis(
                    project_result=project_result,
                    foundation_design_result=foundation_design_result if "foundation_design_result" in locals() else {},
                    foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                    element_load_result=element_load_result if "element_load_result" in locals() else {},
                    structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            else:
                foundation_verification_result = foundation_verification_engine.run(
                    project_result=project_result,
                    foundation_design_result=foundation_design_result if "foundation_design_result" in locals() else {},
                    foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                    element_load_result=element_load_result if "element_load_result" in locals() else {},
                    structural_load_result=structural_load_result if "structural_load_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
        except Exception as error:
            foundation_verification_result = {
                "engine": "FoundationVerificationEngine",
                "status": "FOUNDATION_VERIFICATION_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result("Foundation Verification Engine resultaat:", foundation_verification_result)

        try:
            self.add_to_digital_twin(
                {},
                "foundation_verification",
                foundation_verification_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "foundation_verification",
                    foundation_verification_result
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


def ensure_core_exists():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")


def make_backup():
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


def add_foundation_verification_block(text):
    if "foundation_verification_result" in text:
        print("Foundation Verification Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    if PERMIT_MARKER not in text:
        raise RuntimeError(
            "Koppelpunt niet gevonden: Permit Engine resultaat. "
            "Core-structuur wijkt af; handmatige inspectie nodig."
        )

    print("Foundation Verification Engine-blok toegevoegd voor Permit Engine.")
    return text.replace(PERMIT_MARKER, FOUNDATION_VERIFICATION_BLOCK + PERMIT_MARKER, 1)


def connect():
    ensure_core_exists()
    make_backup()

    text = CORE_PATH.read_text(encoding="utf-8")
    text = add_import(text)
    text = add_foundation_verification_block(text)
    CORE_PATH.write_text(text, encoding="utf-8")

    print("")
    print("FOUNDATION_VERIFICATION_ENGINE_GEKKOPPELD_AAN_CORE")
    print(f"Aangepast: {CORE_PATH}")
    print(f"Backup: {BACKUP_PATH}")


def compile_check():
    run_command("python -m py_compile baoees/core/main.py")
    run_command("python -m py_compile baoees/foundation_verification_engine/main.py")
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


def connect_test():
    connect()
    compile_check()
    test_baoees()
    status()


def commit():
    connect_test()
    run_command("git restore outputs", check=False)
    run_command("git add baoees/core/main.py")
    run_command("git add tools_connect_foundation_verification_engine_to_core.py")
    run_command('git commit -m "feat: connect Foundation Verification Engine to BAOEES Core"')
    run_command("git push")
    status()


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "status",
            "connect",
            "compile-check",
            "test-baoees",
            "connect-test",
            "commit"
        ]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "connect":
        connect()
    elif args.command == "compile-check":
        compile_check()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "connect-test":
        connect_test()
    elif args.command == "commit":
        commit()


if __name__ == "__main__":
    main()
