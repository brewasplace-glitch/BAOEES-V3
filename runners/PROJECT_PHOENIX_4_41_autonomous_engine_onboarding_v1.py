from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def sample_candidate():
    return {
        "schema":"PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id":"future.readonly.demo",
        "display_name":"Phase 6 Read-only Demo",
        "mutation_capable":False,
        "gateway_required":False,
        "allowed_actions":["research.inspect"],
        "allowed_domains":["research"],
        "action_profiles":[
            {
                "action":"research.inspect",
                "risk":"LOW",
                "domain":"research",
                "mutating":False,
                "plan_dispatchable":True
            }
        ],
        "adapters":[
            {
                "adapter_id":"future.readonly.demo.adapter",
                "actions":["research.inspect"],
                "kind":"callable_scaffold",
                "mutation_capable":False,
                "gateway_required":False,
                "plan_dispatchable":True,
                "priority":100
            }
        ],
        "metadata":{"source":"phase6_self_test"}
    }


def main():
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 autonomous engine onboarding v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--runtime-root",type=Path)
    ap.add_argument("--candidate-file",type=Path)
    ap.add_argument("--discover",action="store_true")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))
    from phoenix.autonomy import EngineOnboardingService

    if args.runtime_root:
        runtime=args.runtime_root
    elif args.self_test:
        runtime=Path(tempfile.mkdtemp(prefix="phoenix_phase6_probe_"))
    else:
        local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
        runtime=local/"PROJECT-PHOENIX"/"autonomy"

    service=EngineOnboardingService(repo,runtime)

    output={}
    if args.discover or args.self_test:
        output["discovery"]=service.discover(persist=True)

    candidate=None
    if args.candidate_file:
        candidate=json.loads(args.candidate_file.read_text(encoding="utf-8-sig"))
    elif args.self_test:
        candidate=sample_candidate()

    if candidate is not None:
        output["proposal"]=service.build_proposal(candidate,persist=True)

    if args.self_test:
        proposal=output["proposal"]
        if proposal["admission"]["status"]!="PASS":
            raise RuntimeError("Phase 6 admission probe failed")
        if proposal["activation"]["automatic_activation"] is not False:
            raise RuntimeError("Phase 6 unexpectedly auto-activated candidate")
        if proposal["activation"]["status"]!="SCAFFOLD_IMPLEMENTATION_REQUIRED":
            raise RuntimeError(
                "Expected scaffold implementation requirement, got "
                +proposal["activation"]["status"]
            )
        if proposal["admission"]["capability_discovery_code_loaded"] is not False:
            raise RuntimeError("Discovery loaded candidate code")
        if not proposal["generated_scaffolds"]:
            raise RuntimeError("Adapter scaffold was not generated")
        scaffold=runtime/"engine_onboarding"/proposal["generated_scaffolds"][0]["relative_path"]
        if not scaffold.is_file():
            raise RuntimeError("Generated adapter scaffold file missing")
        output["self_test"]="PASS"

    print(json.dumps(output,indent=2,ensure_ascii=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
