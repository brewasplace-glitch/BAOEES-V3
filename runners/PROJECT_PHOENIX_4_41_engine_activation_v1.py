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
        "engine_id":"future.activation.demo",
        "display_name":"Phase 7 Activation Demo",
        "mutation_capable":False,
        "gateway_required":False,
        "allowed_actions":["research.inspect"],
        "allowed_domains":["research"],
        "action_profiles":[{
            "action":"research.inspect","risk":"LOW","domain":"research",
            "mutating":False,"plan_dispatchable":True
        }],
        "adapters":[{
            "adapter_id":"future.activation.demo.adapter",
            "actions":["research.inspect"],"kind":"callable_scaffold",
            "mutation_capable":False,"gateway_required":False,
            "plan_dispatchable":True,"priority":100
        }],
        "metadata":{"source":"phase7_self_test"}
    }


def implementation_source(class_name:str,adapter_id:str,engine_id:str):
    return (
        "from __future__ import annotations\n"
        "from phoenix.autonomy.executor_adapters import AdapterExecutionResult\n\n"
        f"class {class_name}:\n"
        f"    adapter_id = {adapter_id!r}\n"
        f"    engine_id = {engine_id!r}\n"
        "    actions = (\"research.inspect\",)\n"
        "    mutation_capable = False\n"
        "    gateway_required = False\n\n"
        "    def __init__(self, host):\n"
        "        self.host = host\n\n"
        "    def execute(self, ctx):\n"
        "        return AdapterExecutionResult(\"COMPLETE\", result={\"engine_id\": self.engine_id, \"action\": ctx.step.action})\n"
    )


def parse_impl(values):
    result={}
    for item in values or []:
        key,sep,value=item.partition("=")
        if not sep or not key or not value:
            raise ValueError("--implementation requires adapter_id=path")
        result[key]=Path(value)
    return result


def main():
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 governed engine activation v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--runtime-root",type=Path)
    ap.add_argument("--prepare",action="store_true")
    ap.add_argument("--proposal",type=Path)
    ap.add_argument("--implementation",action="append",default=[])
    ap.add_argument("--verify-bundle",type=Path)
    ap.add_argument("--apply-bundle",type=Path)
    ap.add_argument("--backup-receipt",type=Path)
    ap.add_argument("--approved-sha",action="append",default=[])
    ap.add_argument("--explicit-approval",action="store_true")
    ap.add_argument("--mark-activated")
    ap.add_argument("--commit")
    ap.add_argument("--mark-recovery")
    ap.add_argument("--smoke-import")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))
    from phoenix.autonomy import EngineActivationService, EngineOnboardingService

    if args.runtime_root:
        runtime=args.runtime_root
    elif args.self_test:
        runtime=Path(tempfile.mkdtemp(prefix="phoenix_phase7_probe_"))
    else:
        local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
        runtime=local/"PROJECT-PHOENIX"/"autonomy"

    service=EngineActivationService(repo,runtime)

    if args.self_test:
        onboarding=EngineOnboardingService(repo,runtime,gateway=service.gateway)
        proposal=onboarding.build_proposal(sample_candidate(),persist=True)
        proposal_path=Path(proposal["runtime_path"])
        descriptor=proposal["executor_registry_patch"][0]
        class_name=descriptor["implementation"].partition(":")[2]
        impl_path=runtime/"phase7_self_test_adapter.py"
        impl_path.write_text(
            implementation_source(class_name,descriptor["adapter_id"],proposal["engine_id"]),
            encoding="utf-8"
        )
        tx=service.build_transaction(
            proposal_path,{descriptor["adapter_id"]:impl_path},persist=True
        )
        if tx["status"]!="READY_FOR_GOVERNED_INSTALL":
            raise RuntimeError(f"unexpected transaction status {tx['status']}")
        verified=service.verify_bundle(Path(tx["bundle_dir"]))
        out={
            "schema":"PHOENIX_ENGINE_ACTIVATION_SELF_TEST_V1",
            "status":"PASS",
            "transaction_id":tx["transaction_id"],
            "transaction_status":tx["status"],
            "bundle_verified":verified["bundle_manifest"]["transaction_id"]==tx["transaction_id"],
            "candidate_code_executed_during_validation":False,
            "automatic_activation":False,
            "planned_paths":tx["planned_paths"],
            "implementation_sha256":tx["implementation_sha256"],
        }
        print(json.dumps(out,indent=2,ensure_ascii=True))
        return 0

    if args.prepare:
        if not args.proposal:
            raise SystemExit("--prepare requires --proposal")
        tx=service.build_transaction(args.proposal,parse_impl(args.implementation),persist=True)
        print(json.dumps(tx,indent=2,ensure_ascii=True))
        return 0

    if args.verify_bundle:
        print(json.dumps(service.verify_bundle(args.verify_bundle),indent=2,ensure_ascii=True))
        return 0

    if args.apply_bundle:
        if not args.backup_receipt:
            raise SystemExit("--apply-bundle requires --backup-receipt")
        result=service.apply_bundle(
            args.apply_bundle,args.backup_receipt,set(args.approved_sha),
            explicit_approval=args.explicit_approval
        )
        print(json.dumps(result,indent=2,ensure_ascii=True))
        return 0

    if args.mark_activated:
        if not args.commit:
            raise SystemExit("--mark-activated requires --commit")
        tx=service.update_transaction_status(args.mark_activated,"ACTIVATED",{"activated_commit":args.commit})
        print(json.dumps(tx,indent=2,ensure_ascii=True))
        return 0

    if args.mark_recovery:
        tx=service.update_transaction_status(args.mark_recovery,"RECOVERY_REQUIRED",{})
        print(json.dumps(tx,indent=2,ensure_ascii=True))
        return 0

    if args.smoke_import:
        result=service.smoke_import_activated_adapter(args.smoke_import)
        print(json.dumps(result,indent=2,ensure_ascii=True))
        return 0

    raise SystemExit("select --prepare, --verify-bundle, --apply-bundle, --mark-activated, --mark-recovery, --smoke-import or --self-test")


if __name__=="__main__":
    raise SystemExit(main())
