from pathlib import Path


CORE_PATH = Path("baoees/core/main.py")
BACKUP_PATH = Path("backups/core_main_before_structural_load_engine_connect.py")


IMPORT_LINE = "from baoees.structural_load_engine.main import StructuralLoadEngine\n"


STRUCTURAL_LOAD_BLOCK = '''
        try:
            structural_load_engine = StructuralLoadEngine()
            structural_load_result = structural_load_engine.create_structural_load_analysis(
                project_result=project_result,
                building_technical_result=building_technical_result,
                geo_result=geo_result if "geo_result" in locals() else {},
                structural_result=structural_result if "structural_result" in locals() else {},
                assumptions_result=aaie_result if "aaie_result" in locals() else {}
            )
        except Exception as error:
            structural_load_result = {
                "engine": "StructuralLoadEngine",
                "status": "STRUCTURAL_LOAD_ENGINE_ERROR",
                "error": str(error)
            }

        self.print_result("Structural Load Engine resultaat:", structural_load_result)

        try:
            self.add_to_digital_twin(
                {},
                "structural_loads",
                structural_load_result
            )
        except TypeError:
            try:
                self.add_to_digital_twin(
                    "structural_loads",
                    structural_load_result
                )
            except TypeError:
                pass

'''


def make_backup():
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(
            CORE_PATH.read_text(encoding="utf-8"),
            encoding="utf-8"
        )


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


def add_structural_load_block(text):
    if "structural_load_result" in text:
        print("Structural Load Engine lijkt al gekoppeld. Blok wordt niet opnieuw toegevoegd.")
        return text

    marker = '        self.print_result("Permit Engine resultaat:", permit_result)'

    if marker not in text:
        raise RuntimeError(
            "Koppelpunt niet gevonden: Permit Engine resultaat. "
            "Core-structuur wijkt af; handmatige inspectie nodig."
        )

    return text.replace(marker, STRUCTURAL_LOAD_BLOCK + marker, 1)


def main():
    if not CORE_PATH.exists():
        raise FileNotFoundError(f"Niet gevonden: {CORE_PATH}")

    make_backup()

    text = CORE_PATH.read_text(encoding="utf-8")
    text = add_import(text)
    text = add_structural_load_block(text)

    CORE_PATH.write_text(text, encoding="utf-8")

    print("STRUCTURAL_LOAD_ENGINE_GEKKOPPELD_AAN_CORE")
    print(f"Aangepast: {CORE_PATH}")
    print(f"Backup: {BACKUP_PATH}")


if __name__ == "__main__":
    main()