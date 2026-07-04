from pathlib import Path
import argparse
import subprocess


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_structural_element_sizing_engine_connect.py")

IMPORT_LINE = "from baoees.structural_element_sizing_engine.main import StructuralElementSizingEngine\n"

BLOCK_MARKER = "structural_element_sizing_result"

STRUCTURAL_ELEMENT_SIZING_BLOCK = '''
        try:
            structural_element_sizing_engine = StructuralElementSizingEngine()

            if hasattr(
                structural_element_sizing_engine,
                "create_structural_element_sizing_analysis"
            ):
                structural_element_sizing_result = (
                    structural_element_sizing_engine
                    .create_structural_element_sizing_analysis(
                        project_result=project_result,
                        structural_load_result=structural_load_result
                        if "structural_load_result" in locals() else {},
                        element_load_result=element_load_result
                        if "element_load_result" in locals() else {},
                        foundation_load_transfer_result=foundation_load_transfer_result
                        if "foundation_load_transfer_result" in locals() else {},
                        foundation_design_result=foundation_design_result
                        if "foundation_design_result" in locals() else {},
                        foundation_verification_result=foundation_verification_result
                        if "foundation_verification_result" in locals() else {},
                        building_technical_result=building_technical_result
                        if "building_technical_result" in locals() else {},
                        geo_result=geo_result if "geo_result" in locals() else {},
                        assumptions_result=aaie_result
                        if "aaie_result" in locals() else {}
                    )
                )
            elif hasattr(
                structural_element_sizing_engine,
                "create_element_sizing_analysis"
            ):
                structural_element_sizing_result = (
                    structural_element_sizing_engine.create_element_sizing_analysis(
                        project_result=project_result,
                        structural_load_result=structural_load_result
                        if "structural_load_result" in locals() else {},
                        element_load_result=element_load_result
                        if "element_load_result" in locals() else {},
                        foundation_design_result=foundation_design_result
                        if "foundation_design_result" in locals() else {},
                        foundation_verification_result=foundation_verification_result
                        if "foundation_verification_result" in locals() else {},
                        building_technical_result=building_technical_result
                        if "building_technical_result" in locals() else {}
                    )
                )
            else:
                structural_element_sizing_result = structural_element_sizing_engine.run(
                    project_result=project_result,
                    structural_load_result=structural_load_result
                    if "structural_load_result" in locals() else {},
                    element_load_result=element_load_result
                    if "element_load_result" in locals() else {},
                    foundation_design_result=foundation_design_result
                    if "foundation_design_result" in locals() else {},
                    foundation_verification_result=foundation_verification_result
                    if "foundation_verification_result" in locals() else {}
                )

        except Exception as error:
            structural_element_sizing_result = {
                "engine": "StructuralElementSizingEngine",
                "status": "STRUCTURAL_ELEMENT_SIZING_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result(
            "Structural Element Sizing Engine resultaat:",
            structural_element_sizing_result
        )

        try:
            self.add_to_digital_twin(
                {},
                "structural_element_sizing",
                structural_element_sizing_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "structural_element_sizing",
                    structural_element_sizing_result
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
        BACKUP_PATH.write_text(
            CORE_PATH.read_text(encoding="utf-8"),
            encoding="utf-8"
        )

    print(f"Backup: {BACKUP_PATH}")


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


def insert_block_before_marker(text, marker):
    if marker not in text:
        return None

    return text.replace(marker, STRUCTURAL_ELEMENT_SIZING_BLOCK + marker, 1)


def add_structural_element_sizing_block(text):
    if BLOCK_MARKER in text:
        print("Structural Element Sizing Engine lijkt al gekoppeld.")
        return text

    markers = [
        '        self.print_result("Permit Engine resultaat:", permit_result)',
        '        self.digital_twin.create_project_twin(',
        '        self.add_to_digital_twin(\n            "project_selector"',
    ]

    for marker in markers:
        new_text = insert_block_before_marker(text, marker)
        if new_text is not None:
            return new_text

    raise RuntimeError(
        "Geen veilig koppelpunt gevonden. "
        "Controleer baoees/core/main.py handmatig."
    )


def connect():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")

    make_backup()

    text = CORE_PATH.read_text(encoding="utf-8")
    text = add_import(text)
    text = add_structural_element_sizing_block(text)

    CORE_PATH.write_text(text, encoding="utf-8")

    print("")
    print("STRUCTURAL_ELEMENT_SIZING_ENGINE_GEKKOPPELD_AAN_CORE")


def compile_core():
    run_command("python -m py_compile baoees\\core\\main.py")
    run_command(
        "python -m py_compile baoees\\structural_element_sizing_engine\\main.py"
    )

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
    compile_core()
    test_baoees()


def cleanup_untracked():
    duplicate_download = Path("tools_connect_structural_element_sizing_engine_to_core (1).py")

    if duplicate_download.exists():
        duplicate_download.unlink()
        print(f"Verwijderd: {duplicate_download}")

    if BACKUP_PATH.exists():
        BACKUP_PATH.unlink()
        print(f"Verwijderd: {BACKUP_PATH}")

    run_command("git restore outputs", check=False)


def commit():
    connect_test()
    cleanup_untracked()

    run_command("git add baoees/core/main.py")
    run_command("git add tools_connect_structural_element_sizing_engine_to_core.py")
    run_command(
        'git commit -m "feat: connect Structural Element Sizing Engine to BAOEES Core"'
    )
    run_command("git push")
    run_command("git status", check=False)


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "status",
            "connect-test",
            "commit",
            "compile",
            "test-baoees",
            "cleanup"
        ]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "connect-test":
        connect_test()
    elif args.command == "commit":
        commit()
    elif args.command == "compile":
        compile_core()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "cleanup":
        cleanup_untracked()
        status()


if __name__ == "__main__":
    main()
