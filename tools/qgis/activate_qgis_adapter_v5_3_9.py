from pathlib import Path
import re
import sys

def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: activate_qgis_adapter_v5_3_9.py <engines.py>"
        )

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8-sig")

    base_import = "from .base import Detection, EngineAdapter, EngineSpec"
    adapter_import = "from .qgis_adapter_v5_3_11 import QGISWindowsAdapter"

    if adapter_import not in text:
        if base_import in text:
            text = text.replace(
                base_import,
                base_import + "\n" + adapter_import,
            )
        else:
            text = adapter_import + "\n" + text

    patterns = [
        (r'("qgis"\s*:\s*)QGISWindowsAdapter\s*\(\s*\)', r'\1QGISWindowsAdapter'),
        (r'("qgis"\s*:\s*)QGISAdapter\s*\(\s*\)', r'\1QGISWindowsAdapter'),
        (r'("qgis"\s*:\s*)QGISAdapter\b', r'\1QGISWindowsAdapter'),
        (r'(?m)^(\s*)QGISWindowsAdapter\s*\(\s*\)\s*,?\s*$', r'\1QGISWindowsAdapter,'),
        (r'(?m)^(\s*)QGISAdapter\s*\(\s*\)\s*,?\s*$', r'\1QGISWindowsAdapter,'),
        (r'(?m)^(\s*)QGISAdapter\s*,?\s*$', r'\1QGISWindowsAdapter,'),
    ]

    total = 0
    for pattern, replacement in patterns:
        text, count = re.subn(pattern, replacement, text)
        total += count

    if "QGISWindowsAdapter()" in text:
        raise RuntimeError(
            "Invalid QGISWindowsAdapter instance remains in engines.py"
        )

    if '"qgis": QGISWindowsAdapter' not in text:
        # Support alternate spacing while still requiring a class reference.
        if not re.search(
            r'"qgis"\s*:\s*QGISWindowsAdapter(?!\s*\()',
            text,
        ):
            raise RuntimeError(
                "QGIS registry class reference was not activated"
            )

    if text.count("QGISWindowsAdapter") < 2:
        raise RuntimeError(
            "QGISWindowsAdapter import exists but registry class reference is missing"
        )

    path.write_text(text, encoding="utf-8", newline="\n")

    print(f"QGIS registry replacements: {total}")
    print("QGIS registry mode: CLASS_REFERENCE")
    print("QGIS adapter constructor call deferred to create_adapter()")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
