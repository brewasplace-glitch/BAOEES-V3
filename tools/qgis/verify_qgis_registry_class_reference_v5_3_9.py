from pathlib import Path
import argparse
import re

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engines", required=True)
    args = parser.parse_args()

    text = Path(args.engines).read_text(encoding="utf-8-sig")

    if "QGISWindowsAdapter()" in text:
        raise RuntimeError(
            "Registry contains an adapter instance instead of a class reference"
        )

    match = re.search(
        r'"qgis"\s*:\s*QGISWindowsAdapter(?!\s*\()',
        text,
    )
    if not match:
        raise RuntimeError(
            "Registry does not contain the required QGISWindowsAdapter class reference"
        )

    print("QGIS REGISTRY CLASS REFERENCE: VERIFIED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
