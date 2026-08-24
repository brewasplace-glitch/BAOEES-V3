#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.engines.adapters.libreoffice_office_adapter_v1_0 import (
    LibreOfficeAdapterError,
    LibreOfficeOfficeAdapter,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    capability = sub.add_parser("capability")

    convert = sub.add_parser("convert")
    convert.add_argument("--input", required=True)
    convert.add_argument("--target", required=True)
    convert.add_argument("--output-dir", required=True)

    open_cmd = sub.add_parser("open")
    open_cmd.add_argument("--input", required=True)

    args = parser.parse_args()
    adapter = LibreOfficeOfficeAdapter()

    try:
        if args.command == "capability":
            result = adapter.capability()
        elif args.command == "convert":
            result = adapter.convert(
                args.input,
                args.target,
                args.output_dir,
            )
        else:
            result = adapter.open_document(args.input)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (LibreOfficeAdapterError, OSError, ValueError) as exc:
        print(f"LIBREOFFICE_ADAPTER_ERROR={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
