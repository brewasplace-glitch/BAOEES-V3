from pathlib import Path


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_building_technical_engine_v1.py")


def read_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def ensure_import(content):
    import_line = "from baoees.building_technical_engine.main import BuildingTechnicalEngine\n"

    if import_line in content:
        return content, "IMPORT_ALREADY_PRESENT"

    marker = "from baoees.core.main"

    lines = content.splitlines(keepends=True)

    insert_index = 0

    for index, line in enumerate(lines):
        if line.startswith("from baoees.") or line.startswith("import "):
            insert_index = index + 1

    lines.insert(insert_index, import_line)

    return "".join(lines), "IMPORT_ADDED"


def ensure_init_engine(content):
    target = "self.building_technical_engine = BuildingTechnicalEngine()"

    if target in content:
        return content, "INIT_ALREADY_PRESENT"

    possible_markers = [
        "self.project_git_evidence",
        "self.project_checksum",
        "self.project_audit_trail",
        "self.project_html_dashboard_export",
        "self.project_index_startpage",
        "self.runtime",
        "self.workflow"
    ]

    lines = content.splitlines(keepends=True)

    insert_index = None
    indent = "        "

    for index, line in enumerate(lines):
        for marker in possible_markers:
            if marker in line and "=" in line:
                insert_index = index + 1
                indent = line[:len(line) - len(line.lstrip())]
                break

        if insert_index is not None:
            break

    if insert_index is None:
        raise RuntimeError(
            "Kon geen veilige plek vinden in __init__ om BuildingTechnicalEngine te initialiseren."
        )

    lines.insert(
        insert_index,
        f"{indent}self.building_technical_engine = BuildingTechnicalEngine()\n"
    )

    return "".join(lines), "INIT_ADDED"


def ensure_building_technical_run(content):
    marker = "building_technical_result = self.building_technical_engine.create_building_technical_analysis"

    if marker in content:
        return content, "RUN_ALREADY_PRESENT"

    insertion_block = """
        building_technical_result = self.building_technical_engine.create_building_technical_analysis(
            project_result=project_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            digital_twin_result=digital_twin_result,
            assumptions_result=aaie_result
        )

        self.print_result(
            title="Building Technical Engine resultaat:",
            result=building_technical_result
        )

        self.add_to_digital_twin(
            digital_twin_result=digital_twin_result,
            key="building_technical",
            value=building_technical_result
        )

"""

    preferred_markers = [
        "permit_result =",
        "structural_result =",
        "geo_result ="
    ]

    lines = content.splitlines(keepends=True)

    insert_index = None

    for marker_text in preferred_markers:
        for index, line in enumerate(lines):
            if marker_text in line:
                insert_index = find_end_of_statement(lines, index)
                break

        if insert_index is not None:
            break

    if insert_index is None:
        raise RuntimeError(
            "Kon geen veilige plek vinden om de bouwtechnische analyse in start_projectanalyse te plaatsen."
        )

    lines.insert(insert_index, insertion_block)

    return "".join(lines), "RUN_ADDED"


def find_end_of_statement(lines, start_index):
    open_parentheses = 0
    seen_statement = False

    for index in range(start_index, len(lines)):
        line = lines[index]
        open_parentheses += line.count("(")
        open_parentheses -= line.count(")")

        if line.strip():
            seen_statement = True

        if seen_statement and open_parentheses <= 0:
            return index + 1

    return start_index + 1


def main():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {CORE_PATH}")

    if not BACKUP_PATH.exists():
        BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_file(BACKUP_PATH, read_file(CORE_PATH))

    content = read_file(CORE_PATH)

    report = []

    content, status = ensure_import(content)
    report.append(status)

    content, status = ensure_init_engine(content)
    report.append(status)

    content, status = ensure_building_technical_run(content)
    report.append(status)

    write_file(CORE_PATH, content)

    print("BUILDING_TECHNICAL_CORE_CONNECTOR_GEREED")

    for item in report:
        print(item)

    print(f"Backup: {BACKUP_PATH}")
    print(f"Aangepast: {CORE_PATH}")


if __name__ == "__main__":
    main()