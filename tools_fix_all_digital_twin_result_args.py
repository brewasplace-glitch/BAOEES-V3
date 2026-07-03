import re
from pathlib import Path


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_all_digital_twin_arg_fix.py")


def read_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def main():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {CORE_PATH}")

    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not BACKUP_PATH.exists():
        write_file(BACKUP_PATH, read_file(CORE_PATH))

    content = read_file(CORE_PATH)

    pattern = r"(\s*)digital_twin_result\s*=\s*digital_twin_result\s*,"
    replacement = r"\1digital_twin_result={},"

    new_content, count = re.subn(
        pattern=pattern,
        repl=replacement,
        string=content
    )

    if count == 0:
        print("GEEN_DIGITAL_TWIN_RESULT_ARGUMENT_GEVONDEN")
        print("Er is niets aangepast.")
        return

    write_file(CORE_PATH, new_content)

    print("DIGITAL_TWIN_RESULT_ARGUMENT_FIX_GEREED")
    print(f"Aantal vervangen regels: {count}")
    print(f"Backup: {BACKUP_PATH}")
    print(f"Aangepast: {CORE_PATH}")


if __name__ == "__main__":
    main()