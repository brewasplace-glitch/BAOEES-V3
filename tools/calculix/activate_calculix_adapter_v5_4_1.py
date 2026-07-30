from pathlib import Path
import re
import sys

def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: activate_calculix_adapter_v5_4_1.py <engines.py>")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8-sig")
    base = "from .base import Detection, EngineAdapter, EngineSpec"
    adapter_import = (
        "from .calculix_adapter_v5_4_1 import CalculiXWindowsAdapter"
    )
    if adapter_import not in text:
        if base in text:
            text = text.replace(base, base + "\n" + adapter_import)
        else:
            text = adapter_import + "\n" + text

    patterns = (
        (r'("calculix"\s*:\s*)CalculiXAdapter\s*\(\s*\)', r'\1CalculiXWindowsAdapter'),
        (r'("calculix"\s*:\s*)CalculiXAdapter\b', r'\1CalculiXWindowsAdapter'),
        (r'("calculix"\s*:\s*)CalculiXWindowsAdapter\s*\(\s*\)', r'\1CalculiXWindowsAdapter'),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    if not re.search(
        r'"calculix"\s*:\s*CalculiXWindowsAdapter(?!\s*\()',
        text,
    ):
        raise RuntimeError("CalculiX registry class reference not found")
    if "CalculiXWindowsAdapter()" in text:
        raise RuntimeError("CalculiX registry contains an adapter instance")

    path.write_text(text, encoding="utf-8", newline="\n")
    print("CALCULIX REGISTRY CLASS REFERENCE: VERIFIED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
