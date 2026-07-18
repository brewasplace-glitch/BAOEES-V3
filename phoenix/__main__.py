# PHOENIX_UPDATER_V1_1_WRAPPER
from __future__ import annotations

import runpy
import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        from phoenix.updater.__main__ import main as updater_main

        updater_main(["update", *sys.argv[2:]])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "update-list":
        from phoenix.updater.__main__ import main as updater_main

        updater_main(["list", *sys.argv[2:]])
        return

    runpy.run_module("phoenix._legacy_main", run_name="__main__")


if __name__ == "__main__":
    main()
