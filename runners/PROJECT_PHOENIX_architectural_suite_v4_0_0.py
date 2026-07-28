from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from pathlib import Path
import argparse
from phoenix.architecture.integrated_suite_v4_0_0 import run
p=argparse.ArgumentParser();p.add_argument("--model",required=True);p.add_argument("--output",required=True);a=p.parse_args()
m=run(Path(a.model),Path(a.output))
print("PROJECT PHOENIX ARCHITECTURAL SUITE v4.0.0 COMPLETED")
print("PROJECT:",m["project_id"]);print("RELEASE STATUS:",m["release_status"]);print("ARTIFACTS:",len(m["artifacts"]))
