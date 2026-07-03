from pathlib import Path


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_digital_twin_result_fix.py")


def read_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def main():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {CORE_PATH}")

    if not BACKUP_PATH.exists():
        BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_file(BACKUP_PATH, read_file(CORE_PATH))

    content = read_file(CORE_PATH)

    old_text = "            digital_twin_result=digital_twin_result,\n"
    new_text = "            digital_twin_result={},\n"

    if old_text not in content:
        print("REGEL_NIET_GEVONDEN_OF_AL_AANGEPAST")
        print("Controleer handmatig in baoees/core/main.py")
        return

    content = content.replace(old_text, new_text, 1)

    write_file(CORE_PATH, content)

    print("BUILDING_TECHNICAL_DIGITAL_TWIN_ARG_FIX_GEREED")
    print("Aangepast:")
    print("digital_twin_result=digital_twin_result,")
    print("naar:")
    print("digital_twin_result={},")


if __name__ == "__main__":
    main()