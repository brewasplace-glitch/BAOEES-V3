from pathlib import Path


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_add_to_digital_twin_call_fix.py")


def read_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def find_block_end(lines, start_index):
    open_parentheses = 0

    for index in range(start_index, len(lines)):
        line = lines[index]
        open_parentheses += line.count("(")
        open_parentheses -= line.count(")")

        if index > start_index and open_parentheses <= 0:
            return index

    return start_index


def replace_building_technical_digital_twin_call(content):
    lines = content.splitlines(keepends=True)
    new_lines = []
    index = 0
    replacements = 0

    while index < len(lines):
        line = lines[index]

        if "self.add_to_digital_twin(" in line:
            end_index = find_block_end(lines, index)
            block = "".join(lines[index:end_index + 1])

            if "building_technical" in block and "building_technical_result" in block:
                indent = line[:len(line) - len(line.lstrip())]

                replacement_block = (
                    f"{indent}try:\n"
                    f"{indent}    self.add_to_digital_twin(\n"
                    f"{indent}        {{}},\n"
                    f"{indent}        \"building_technical\",\n"
                    f"{indent}        building_technical_result\n"
                    f"{indent}    )\n"
                    f"{indent}except TypeError:\n"
                    f"{indent}    try:\n"
                    f"{indent}        self.add_to_digital_twin(\n"
                    f"{indent}            \"building_technical\",\n"
                    f"{indent}            building_technical_result\n"
                    f"{indent}        )\n"
                    f"{indent}    except TypeError:\n"
                    f"{indent}        pass\n"
                )

                new_lines.append(replacement_block)
                replacements += 1
                index = end_index + 1
                continue

        new_lines.append(line)
        index += 1

    return "".join(new_lines), replacements


def main():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {CORE_PATH}")

    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not BACKUP_PATH.exists():
        write_file(BACKUP_PATH, read_file(CORE_PATH))

    content = read_file(CORE_PATH)

    new_content, replacements = replace_building_technical_digital_twin_call(content)

    if replacements == 0:
        print("GEEN_BUILDING_TECHNICAL_ADD_TO_DIGITAL_TWIN_BLOK_GEVONDEN")
        print("Er is niets aangepast.")
        return

    write_file(CORE_PATH, new_content)

    print("ADD_TO_DIGITAL_TWIN_CALL_FIX_GEREED")
    print(f"Aantal vervangen blokken: {replacements}")
    print(f"Backup: {BACKUP_PATH}")
    print(f"Aangepast: {CORE_PATH}")


if __name__ == "__main__":
    main()