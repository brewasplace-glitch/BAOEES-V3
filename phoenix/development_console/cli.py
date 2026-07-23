from __future__ import annotations
import argparse
from pathlib import Path
from .console import PhoenixDevelopmentConsole
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--repo-root',default=str(Path.cwd())); p.add_argument('--json-output',default=''); a=p.parse_args(argv)
    c=PhoenixDevelopmentConsole(a.repo_root); r=c.inspect(); print(c.render(r))
    if a.json_output:c.write_json(r,a.json_output)
    return 0 if r.working_tree in {'CLEAN','DIRTY'} else 1
if __name__=='__main__': raise SystemExit(main())
