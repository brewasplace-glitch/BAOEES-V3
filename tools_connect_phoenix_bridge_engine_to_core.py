from pathlib import Path
import argparse
import py_compile
import subprocess


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_phoenix_bridge_engine_connect.py")

IMPORT_LINE = "from baoees.phoenix_bridge_engine.main import PhoenixBridgeEngine\n"

PREFERRED_LABELS = [
    "Structural Project Output Package Engine resultaat:",
    "Structural QAQC Engine resultaat:",
    "Structural CAD Export Engine resultaat:",
]

PHOENIX_BRIDGE_BLOCK = '''
        try:
            phoenix_bridge_engine = PhoenixBridgeEngine()
            phoenix_bridge_result = phoenix_bridge_engine.create_phoenix_bridge_package(
                project_result=project_result if "project_result" in locals() else {},
                structural_project_output_package_result=structural_project_output_package_result if "structural_project_output_package_result" in locals() else {},
                structural_qaqc_result=structural_qaqc_result if "structural_qaqc_result" in locals() else {},
                digital_twin_result=digital_twin_result if "digital_twin_result" in locals() else {}
            )
        except Exception as error:
            phoenix_bridge_result = {
                "engine": "PhoenixBridgeEngine",
                "status": "PHOENIX_BRIDGE_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result(
            "Phoenix Bridge Engine resultaat:",
            phoenix_bridge_result
        )

        try:
            self.add_to_digital_twin(
                {},
                "phoenix_bridge",
                phoenix_bridge_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "phoenix_bridge",
                    phoenix_bridge_result
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
    for index in range(label_index, max(label_index - 16, -1), -1):
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


def find_label(lines):
    for label in PREFERRED_LABELS:
        for index, line in enumerate(lines):
            if label in line:
                return label, index

    return None, None


def find_insert_index(lines):
    label, label_index = find_label(lines)

    if label_index is None:
        labels_text = ", ".join(PREFERRED_LABELS)
        raise RuntimeError(f"Geen geschikt koppelpunt gevonden. Gezocht naar: {labels_text}")

    start_index = find_statement_start(lines, label_index)
    end_index = find_statement_end(lines, start_index)

    return label, end_index + 1


def add_phoenix_bridge_block(text):
    if "phoenix_bridge_result" in text:
        print("Phoenix Bridge Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    lines = text.splitlines(keepends=True)
    label, insert_index = find_insert_index(lines)

    print(f"Koppelpunt gebruikt: {label}")
    lines.insert(insert_index, PHOENIX_BRIDGE_BLOCK)

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
    print("Zoeken naar Phoenix Bridge koppelpunt...")

    label, label_index = find_label(lines)

    if label_index is None:
        print("Geen geschikt koppelpunt gevonden.")
        print("Gezochte labels:")

        for item in PREFERRED_LABELS:
            print(f"- {item}")

        return

    start_index = find_statement_start(lines, label_index)
    end_index = find_statement_end(lines, start_index)

    print(f"Koppelpunt gebruikt: {label}")
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
        text = add_phoenix_bridge_block(text)
        write_core(text)

        print("PHOENIX_BRIDGE_ENGINE_GEKKOPPELD_AAN_CORE")

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
    run_command("git add tools_connect_phoenix_bridge_engine_to_core.py")
    run_command('git commit -m "feat: connect Phoenix Bridge Engine to BAOEES Core"')
    run_command("git push")
    cleanup_backup()
    run_command("git status", check=False)


def clean_temp():
    if BACKUP_PATH.exists():
        BACKUP_PATH.unlink()
        print(f"Verwijderd: {BACKUP_PATH}")

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
