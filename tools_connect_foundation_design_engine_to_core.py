from pathlib import Path
import argparse
import py_compile
import subprocess


CORE_PATH = Path("baoees/core/main.py")
ENGINE_PATH = Path("baoees/foundation_design_engine/main.py")
BACKUP_PATH = Path("backups/core_main_before_foundation_design_engine_connect.py")

IMPORT_LINE = "from baoees.foundation_design_engine.main import FoundationDesignEngine\n"

FOUNDATION_DESIGN_BLOCK = '''
        try:
            foundation_design_engine = FoundationDesignEngine()

            if hasattr(foundation_design_engine, "create_foundation_design"):
                foundation_design_result = foundation_design_engine.create_foundation_design(
                    project_result=project_result,
                    foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            elif hasattr(foundation_design_engine, "create_foundation_design_analysis"):
                foundation_design_result = foundation_design_engine.create_foundation_design_analysis(
                    project_result=project_result,
                    foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            elif hasattr(foundation_design_engine, "run"):
                foundation_design_result = foundation_design_engine.run(
                    project_result=project_result,
                    foundation_load_transfer_result=foundation_load_transfer_result if "foundation_load_transfer_result" in locals() else {},
                    geo_result=geo_result if "geo_result" in locals() else {},
                    assumptions_result=aaie_result if "aaie_result" in locals() else {}
                )
            else:
                foundation_design_result = {
                    "engine": "FoundationDesignEngine",
                    "status": "FOUNDATION_DESIGN_ENGINE_METHOD_NOT_FOUND"
                }
        except Exception as error:
            foundation_design_result = {
                "engine": "FoundationDesignEngine",
                "status": "FOUNDATION_DESIGN_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result("Foundation Design Engine resultaat:", foundation_design_result)

        try:
            self.add_to_digital_twin(
                {},
                "foundation_design",
                foundation_design_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "foundation_design",
                    foundation_design_result
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

    if CORE_PATH.exists() and not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(
            CORE_PATH.read_text(encoding="utf-8"),
            encoding="utf-8"
        )
        print(f"Backup gemaakt: {BACKUP_PATH}")


def cleanup_temp_files():
    if BACKUP_PATH.exists():
        BACKUP_PATH.unlink()
        print(f"Backup verwijderd: {BACKUP_PATH}")

    run_command("git restore outputs", check=False)


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


def find_insert_position(text):
    markers = [
        '        self.print_result("Foundation Load Transfer Engine resultaat:", foundation_load_transfer_result)',
        "        self.print_result('Foundation Load Transfer Engine resultaat:', foundation_load_transfer_result)",
        "Foundation Load Transfer Engine resultaat:",
        "foundation_load_transfer_result"
    ]

    for marker in markers:
        position = text.find(marker)
        if position >= 0:
            line_end = text.find("\n", position)
            if line_end >= 0:
                return line_end + 1

    raise RuntimeError(
        "Koppelpunt niet gevonden. Zoektermen: Foundation Load Transfer Engine resultaat / foundation_load_transfer_result."
    )


def connect_core():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")

    if not ENGINE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {ENGINE_PATH}")

    make_backup()

    text = CORE_PATH.read_text(encoding="utf-8")
    text = add_import(text)

    if "foundation_design_result" in text:
        print("Foundation Design Engine lijkt al gekoppeld. Geen extra blok toegevoegd.")
    else:
        insert_position = find_insert_position(text)
        text = text[:insert_position] + FOUNDATION_DESIGN_BLOCK + text[insert_position:]

    CORE_PATH.write_text(text, encoding="utf-8")

    print("")
    print("FOUNDATION_DESIGN_ENGINE_GEKKOPPELD_AAN_CORE")
    print(f"Aangepast: {CORE_PATH}")


def compile_tests():
    py_compile.compile(str(CORE_PATH), doraise=True)
    py_compile.compile(str(ENGINE_PATH), doraise=True)
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
    connect_core()
    compile_tests()
    test_baoees()
    run_command("git status", check=False)


def commit():
    connect_test()
    cleanup_temp_files()

    run_command("git add baoees/core/main.py")
    run_command("git add tools_connect_foundation_design_engine_to_core.py")
    run_command('git commit -m "feat: connect Foundation Design Engine to BAOEES Core"')
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
            "commit"
        ]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "connect-test":
        connect_test()
    elif args.command == "commit":
        commit()


if __name__ == "__main__":
    main()
